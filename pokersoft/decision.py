"""Decision engine: turns a game state into two recommendations.

- `gto`: a GTO-*leaning* baseline (pot odds / MDF / preflop charts / hand
  percentile). It is a heuristic approximation of solver output, not an
  actual real-time solve - genuinely solving postflop spots needs a
  precomputed strategy or serious offline compute, neither of which fits a
  live overlay. Treat it as "the mathematically-grounded default line".
- `exploit`: starts from the GTO baseline and adjusts it using observed
  opponent tendencies (see opponent_model.py) the way a thinking-player
  would deviate from a balanced default against a specific, read opponent.
  Only applied once enough hands have been observed (see MIN_SAMPLE).

Both are returned together so the user can see the math-optimal anchor and
the "pro adjustment" side by side, with the reasoning spelled out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from .cards import Card
from .equity import EquityResult, hand_equity
from .opponent_model import OpponentStats
from .preflop_strength import load_or_compute_strength_table, percentile_rank
from .ranges import (
    RFI_RANGES_6MAX,
    THREEBET_VALUE_RANGES_6MAX,
    canonical_hand_label,
    parse_range,
)

_STRENGTH_TABLE = None


def _strength_table():
    global _STRENGTH_TABLE
    if _STRENGTH_TABLE is None:
        _STRENGTH_TABLE = load_or_compute_strength_table()
    return _STRENGTH_TABLE


class Street(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class Action(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    SHOVE = "shove"


@dataclass
class GameState:
    hero_cards: Sequence[Card]
    board: Sequence[Card] = field(default_factory=list)
    street: Street = Street.PREFLOP
    position: str = "BTN"  # UTG/HJ/CO/BTN/SB/BB
    stack_bb: float = 100.0
    pot_bb: float = 1.5
    to_call_bb: float = 0.0
    num_active_opponents: int = 1
    facing_preflop_raises: int = 0  # 0 = unopened/first in, 1 = facing a raise, 2 = facing a 3bet, ...
    opponent_range_hint: Optional[str] = None  # override the default assumed range
    opponent_stats: Optional[OpponentStats] = None


@dataclass
class Recommendation:
    action: Action
    sizing_bb: Optional[float]
    equity: Optional[float]
    required_equity: Optional[float]
    rationale: str


@dataclass
class Analysis:
    equity_result: Optional[EquityResult]
    gto: Recommendation
    exploit: Recommendation


def pot_odds(pot_bb: float, to_call_bb: float) -> float:
    if to_call_bb <= 0:
        return 0.0
    return to_call_bb / (pot_bb + to_call_bb)


def minimum_defense_frequency(pot_bb: float, bet_bb: float) -> float:
    if pot_bb + bet_bb <= 0:
        return 1.0
    return pot_bb / (pot_bb + bet_bb)


def _default_opponent_range_str(state: GameState) -> str:
    if state.opponent_range_hint:
        return state.opponent_range_hint
    if state.street == Street.PREFLOP:
        return RFI_RANGES_6MAX.get(state.position, "22+, A2+, K2+, Q2s+, J6s+, T6s+")
    # postflop default: a generic "will get to showdown with" range
    return "22+, A2+, K2+, Q4+, J7+, T7+, 97s+, 86s+, 75s+, 65s"


def _hand_label(hero_cards: Sequence[Card]) -> str:
    c1, c2 = hero_cards
    suited = c1.suit == c2.suit
    return canonical_hand_label(c1.rank, c2.rank, suited)


def _preflop_gto(state: GameState) -> Recommendation:
    table = _strength_table()
    label = _hand_label(state.hero_cards)
    pct = percentile_rank(table, label)  # 0 = best hand, 1 = worst

    # Short-stack push/fold overrides standard opening strategy.
    if state.stack_bb <= 20 and state.facing_preflop_raises == 0:
        # widen shove threshold as stack shrinks and position gets later
        position_bonus = {"UTG": 0.0, "HJ": 0.03, "CO": 0.06, "BTN": 0.12, "SB": 0.09, "BB": 0.0}
        depth_factor = max(0.0, (20 - state.stack_bb) / 20)  # 0 at 20bb, 1 at 0bb
        threshold = 0.10 + depth_factor * 0.30 + position_bonus.get(state.position, 0.0)
        if pct <= threshold:
            return Recommendation(
                Action.SHOVE, state.stack_bb, None, None,
                f"Стек {state.stack_bb:.0f}бб — пуш/фолд зона. {label} входит в топ "
                f"{threshold:.0%} рук для {state.position}, шовим весь стек.",
            )
        return Recommendation(
            Action.FOLD, None, None, None,
            f"Стек {state.stack_bb:.0f}бб, {label} не входит в диапазон шова "
            f"(топ {threshold:.0%}) для {state.position}.",
        )

    if state.facing_preflop_raises == 0:
        range_str = RFI_RANGES_6MAX.get(state.position, "")
        in_range = frozenset(state.hero_cards) in parse_range(range_str)
        if in_range:
            size = 2.2 if state.position in ("CO", "BTN") else 2.5
            return Recommendation(
                Action.RAISE, size, None, None,
                f"{label} входит в диапазон открытия ({state.position}, 6-max). "
                f"Стандартный рейз-опен.",
            )
        return Recommendation(
            Action.FOLD, None, None, None,
            f"{label} не входит в диапазон открытия ({state.position}).",
        )

    if state.facing_preflop_raises == 1:
        value_range_str = THREEBET_VALUE_RANGES_6MAX.get(state.position, "TT+, AQs+, AKo")
        in_value = frozenset(state.hero_cards) in parse_range(value_range_str)
        if in_value:
            return Recommendation(
                Action.RAISE, state.pot_bb + 3 * state.to_call_bb, None, None,
                f"{label} — часть value-3-бет диапазона. 3-бет для изолейта/значения.",
            )
        # flat/call band: everything within ~35th percentile that isn't a 3bet-value hand
        if pct <= 0.35:
            return Recommendation(
                Action.CALL, state.to_call_bb, None, None,
                f"{label} недостаточно силён для 3-бета, но крепок для колла "
                f"против одиночного рейза ({state.position}).",
            )
        return Recommendation(
            Action.FOLD, None, None, None,
            f"{label} слишком слаб, чтобы продолжать против рейза из {state.position}.",
        )

    # facing a 3bet or more
    continue_threshold = 0.06
    if pct <= continue_threshold:
        return Recommendation(
            Action.CALL, state.to_call_bb, None, None,
            f"{label} в топ {continue_threshold:.0%} рук — можно коллировать/4-бетить 3-бет.",
        )
    return Recommendation(
        Action.FOLD, None, None, None,
        f"{label} не входит в диапазон продолжения против 3-бета "
        f"(топ {continue_threshold:.0%}).",
    )


def _postflop_gto(state: GameState, equity_result: EquityResult) -> Recommendation:
    equity = equity_result.equity
    req = pot_odds(state.pot_bb, state.to_call_bb)

    if state.to_call_bb <= 0:
        if equity >= 0.65:
            size = round(0.66 * state.pot_bb, 2)
            return Recommendation(
                Action.BET, size, equity, None,
                f"Эквити {equity:.0%} — сильная рука, ставим на значение "
                f"(~66% пота).",
            )
        if equity <= 0.30 and state.num_active_opponents <= 1:
            size = round(0.66 * state.pot_bb, 2)
            return Recommendation(
                Action.BET, size, equity, None,
                f"Эквити только {equity:.0%}, но одиночный соперник — "
                f"место для полублефа/блефа (~66% пота), баланс value/bluff по теории.",
            )
        return Recommendation(
            Action.CHECK, None, equity, None,
            f"Эквити {equity:.0%} — недостаточно ни для ставки на значение, "
            f"ни для явного блефа. Чек.",
        )

    mdf = minimum_defense_frequency(state.pot_bb, state.to_call_bb)
    margin = 0.03
    if equity >= req + 0.15:
        size = round(min(state.stack_bb, (state.pot_bb + 2 * state.to_call_bb) * 0.75), 2)
        return Recommendation(
            Action.RAISE, size, equity, req,
            f"Эквити {equity:.0%} значительно выше требуемых {req:.0%} "
            f"(pot odds) — рейзим на значение.",
        )
    if equity >= req - margin:
        return Recommendation(
            Action.CALL, state.to_call_bb, equity, req,
            f"Эквити {equity:.0%} против требуемых {req:.0%} по pot odds — "
            f"колл математически корректен (MDF {mdf:.0%}).",
        )
    return Recommendation(
        Action.FOLD, None, equity, req,
        f"Эквити {equity:.0%} ниже требуемых {req:.0%} по pot odds — фолд.",
    )


def _apply_exploit_adjustment(
    state: GameState, gto: Recommendation, equity_result: Optional[EquityResult]
) -> Recommendation:
    stats = state.opponent_stats
    if stats is None or not stats.is_reliable():
        return Recommendation(
            gto.action, gto.sizing_bb, gto.equity, gto.required_equity,
            gto.rationale + " [Недостаточно раздач по сопернику — эксплойт совпадает с GTO.]",
        )

    action, sizing, rationale_extra = gto.action, gto.sizing_bb, ""

    # Postflop, facing a bet decision baked into gto.action already; here we
    # nudge based on reads. Preflop nudges are handled separately below.
    if state.street != Street.PREFLOP:
        if state.to_call_bb <= 0:
            if stats.fold_to_cbet() >= 0.60 and gto.action == Action.CHECK:
                action = Action.BET
                sizing = round(0.5 * state.pot_bb, 2)
                rationale_extra = (
                    f" Против этого соперника fold-to-cbet {stats.fold_to_cbet():.0%} "
                    f"(> 60%) — ставим шире, чем GTO-чек, эксплуатируя частые фолды."
                )
            elif stats.fold_to_cbet() <= 0.30 and gto.action == Action.BET and (equity_result and equity_result.equity < 0.55):
                action = Action.CHECK
                sizing = None
                rationale_extra = (
                    f" Соперник почти не бросает карты на кбет (fold-to-cbet "
                    f"{stats.fold_to_cbet():.0%}) — тонкий/полу-блефовый бет невыгоден, "
                    f"чек и переоценка на следующей улице."
                )
        else:
            if stats.aggression_factor() < 0.5 and gto.action in (Action.CALL,) and equity_result and equity_result.equity >= 0.55:
                action = Action.RAISE
                sizing = round(state.pot_bb * 0.75, 2)
                rationale_extra = (
                    " Соперник пассивен (низкий AF) — при сильной руке рейзим "
                    "чаще, чем предполагает баланс GTO, так как он редко "
                    "переоценивает наши руки блефом в ответ."
                )
    else:
        # preflop exploit nudges
        if state.facing_preflop_raises == 0 and stats.vpip() < 0.16 and gto.action == Action.RAISE:
            rationale_extra = (
                f" Соперник(и) очень тайтовые (VPIP {stats.vpip():.0%}) — "
                f"стандартный рейз-опен и так корректен, можно даже чуть шире."
            )
        if state.facing_preflop_raises >= 1 and stats.fold_to_3bet() >= 0.70 and gto.action == Action.FOLD:
            action = Action.RAISE
            sizing = state.pot_bb + 3 * state.to_call_bb
            rationale_extra = (
                f" Соперник пасует на 3-бет {stats.fold_to_3bet():.0%} — GTO-фолд "
                f"здесь можно заменить на блеф-3-бет за счёт частых сбросов."
            )
        if state.facing_preflop_raises >= 1 and stats.vpip() >= 0.42 and stats.aggression_factor() < 0.7 and gto.action == Action.FOLD:
            rationale_extra = (
                " Соперник лузовый и пассивный (calling station) — не нужно "
                "пытаться его выбить блефом, GTO-фолд с мусорной рукой остаётся верным."
            )

    if not rationale_extra:
        rationale_extra = " [Есть статистика по сопернику, но она не меняет рекомендацию GTO в этой ситуации.]"

    return Recommendation(action, sizing, gto.equity, gto.required_equity, gto.rationale + rationale_extra)


def analyze(state: GameState) -> Analysis:
    if state.street == Street.PREFLOP:
        gto = _preflop_gto(state)
        equity_result = None
    else:
        opp_range_str = _default_opponent_range_str(state)
        opp_range = parse_range(opp_range_str)
        equity_result = hand_equity(
            list(state.hero_cards),
            list(state.board),
            opponent_ranges=[opp_range] * max(1, state.num_active_opponents),
        )
        gto = _postflop_gto(state, equity_result)

    exploit = _apply_exploit_adjustment(state, gto, equity_result)
    return Analysis(equity_result=equity_result, gto=gto, exploit=exploit)
