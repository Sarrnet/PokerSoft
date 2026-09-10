"""Lightweight per-opponent statistics used for exploitative adjustments.

Tracks the standard small set of "reads" a live pro would keep in their head
(VPIP, PFR, 3-bet%, fold-to-cbet, fold-to-3bet, went-to-showdown%) from a
stream of observed actions. Everything is a simple running count, and the
decision engine ignores a stat until enough hands have been observed to
trust it (see MIN_SAMPLE below) - a read from 3 hands is noise, not a read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

MIN_SAMPLE = 15  # hands observed before we let a stat influence a decision


@dataclass
class OpponentStats:
    name: str
    hands_observed: int = 0
    vpip_count: int = 0
    pfr_count: int = 0
    three_bet_opportunities: int = 0
    three_bet_count: int = 0
    faced_cbet_count: int = 0
    folded_to_cbet_count: int = 0
    faced_3bet_count: int = 0
    folded_to_3bet_count: int = 0
    went_to_showdown_count: int = 0
    aggressive_actions: int = 0  # bets + raises postflop
    passive_actions: int = 0  # calls postflop

    def record_hand_start(self) -> None:
        self.hands_observed += 1

    def record_voluntary_preflop_action(self) -> None:
        self.vpip_count += 1

    def record_preflop_raise(self) -> None:
        self.pfr_count += 1

    def record_3bet_opportunity(self, did_3bet: bool) -> None:
        self.three_bet_opportunities += 1
        if did_3bet:
            self.three_bet_count += 1

    def record_faced_cbet(self, folded: bool) -> None:
        self.faced_cbet_count += 1
        if folded:
            self.folded_to_cbet_count += 1

    def record_faced_3bet(self, folded: bool) -> None:
        self.faced_3bet_count += 1
        if folded:
            self.folded_to_3bet_count += 1

    def record_showdown(self) -> None:
        self.went_to_showdown_count += 1

    def record_postflop_action(self, aggressive: bool) -> None:
        if aggressive:
            self.aggressive_actions += 1
        else:
            self.passive_actions += 1

    def is_reliable(self) -> bool:
        return self.hands_observed >= MIN_SAMPLE

    def vpip(self) -> float:
        return self._safe_div(self.vpip_count, self.hands_observed)

    def pfr(self) -> float:
        return self._safe_div(self.pfr_count, self.hands_observed)

    def three_bet_pct(self) -> float:
        return self._safe_div(self.three_bet_count, self.three_bet_opportunities)

    def fold_to_cbet(self) -> float:
        return self._safe_div(self.folded_to_cbet_count, self.faced_cbet_count)

    def fold_to_3bet(self) -> float:
        return self._safe_div(self.folded_to_3bet_count, self.faced_3bet_count)

    def aggression_factor(self) -> float:
        return self._safe_div(self.aggressive_actions, self.passive_actions, default=1.0)

    @staticmethod
    def _safe_div(num: int, den: int, default: float = 0.0) -> float:
        return num / den if den else default


class OpponentBook:
    """A simple registry of OpponentStats keyed by player name/seat id."""

    def __init__(self) -> None:
        self._players: Dict[str, OpponentStats] = {}

    def get(self, name: str) -> OpponentStats:
        if name not in self._players:
            self._players[name] = OpponentStats(name=name)
        return self._players[name]

    def all(self) -> Dict[str, OpponentStats]:
        return dict(self._players)
