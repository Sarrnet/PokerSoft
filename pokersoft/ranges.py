"""Starting-hand range notation and baseline preflop charts.

Supports the common PokerStove/Flopzilla-style notation:
    "AA"            - pocket aces
    "AKs"           - suited ace-king
    "AKo"           - offsuit ace-king
    "AK"            - both suited and offsuit ace-king
    "77+"           - all pocket pairs 77 and higher
    "ATs+"          - suited combos from ATs up to AKs (top card fixed as A)
    "ATo+"          - same, offsuit
    "AT+"           - both, suited and offsuit
    "AJo:0.5"       - a weight (mixed frequency) can be appended after ':'

Combos are individual 2-card hands represented as a frozenset of
(rank, suit) tuples via `Combo`. A Range is a mapping combo -> weight (0..1).
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, FrozenSet, Iterable, List, Tuple

from .cards import RANK_VALUE, SUITS, Card

Combo = FrozenSet[Card]
Range = Dict[Combo, float]


def _rank_of(ch: str) -> int:
    ch = ch.upper()
    if ch not in RANK_VALUE:
        raise ValueError(f"invalid rank char: {ch!r}")
    return RANK_VALUE[ch]


def all_combos_for_hand(r1: int, r2: int, suited: bool | None) -> List[Combo]:
    """suited=True -> only suited combos, False -> only offsuit, None -> pair (r1==r2)."""
    combos: List[Combo] = []
    if r1 == r2:
        for s1, s2 in combinations(SUITS, 2):
            combos.append(frozenset({Card(r1, s1), Card(r2, s2)}))
        return combos
    if suited:
        for s in SUITS:
            combos.append(frozenset({Card(r1, s), Card(r2, s)}))
    else:
        for s1 in SUITS:
            for s2 in SUITS:
                if s1 != s2:
                    combos.append(frozenset({Card(r1, s1), Card(r2, s2)}))
    return combos


def _add(range_out: Range, combos: Iterable[Combo], weight: float) -> None:
    for c in combos:
        # keep the max weight if a combo is specified twice
        range_out[c] = max(range_out.get(c, 0.0), weight)


def _parse_token(token: str) -> Tuple[str, float]:
    if ":" in token:
        hand_part, weight_part = token.split(":", 1)
        return hand_part.strip(), float(weight_part)
    return token.strip(), 1.0


def parse_range(range_str: str) -> Range:
    """Parse a comma-separated range string into a Combo -> weight mapping."""
    out: Range = {}
    if not range_str or not range_str.strip():
        return out
    for raw_token in range_str.split(","):
        raw_token = raw_token.strip()
        if not raw_token:
            continue
        hand_part, weight = _parse_token(raw_token)
        plus = hand_part.endswith("+")
        if plus:
            hand_part = hand_part[:-1]

        if len(hand_part) == 2:
            r1, r2 = _rank_of(hand_part[0]), _rank_of(hand_part[1])
            if r1 == r2:
                # pocket pair, e.g. "77" or "77+"
                lo, hi = (r1, 14) if plus else (r1, r1)
                for r in range(lo, hi + 1):
                    _add(out, all_combos_for_hand(r, r, None), weight)
            else:
                hi_r, lo_r = max(r1, r2), min(r1, r2)
                if plus:
                    for r in range(lo_r, hi_r):
                        _add(out, all_combos_for_hand(hi_r, r, True), weight)
                        _add(out, all_combos_for_hand(hi_r, r, False), weight)
                else:
                    _add(out, all_combos_for_hand(hi_r, lo_r, True), weight)
                    _add(out, all_combos_for_hand(hi_r, lo_r, False), weight)
        elif len(hand_part) == 3:
            r1, r2, suit_flag = (
                _rank_of(hand_part[0]),
                _rank_of(hand_part[1]),
                hand_part[2].lower(),
            )
            if suit_flag not in ("s", "o"):
                raise ValueError(f"invalid suited/offsuit flag in {raw_token!r}")
            suited = suit_flag == "s"
            hi_r, lo_r = max(r1, r2), min(r1, r2)
            if plus:
                for r in range(lo_r, hi_r):
                    _add(out, all_combos_for_hand(hi_r, r, suited), weight)
            else:
                _add(out, all_combos_for_hand(hi_r, lo_r, suited), weight)
        else:
            raise ValueError(f"cannot parse range token: {raw_token!r}")
    return out


def combos_excluding(range_: Range, dead_cards: Iterable[Card]) -> Range:
    dead = set(dead_cards)
    return {combo: w for combo, w in range_.items() if not (combo & dead)}


def canonical_hand_label(r1: int, r2: int, suited: bool) -> str:
    from .cards import VALUE_RANK

    hi, lo = max(r1, r2), min(r1, r2)
    if hi == lo:
        return f"{VALUE_RANK[hi]}{VALUE_RANK[lo]}"
    return f"{VALUE_RANK[hi]}{VALUE_RANK[lo]}{'s' if suited else 'o'}"


def all_169_hands() -> List[str]:
    """Canonical list of the 169 distinct starting hands (e.g. 'AA', 'AKs', 'AKo')."""
    labels = []
    ranks_desc = sorted(RANK_VALUE.values(), reverse=True)
    for i, r1 in enumerate(ranks_desc):
        for r2 in ranks_desc[i:]:
            if r1 == r2:
                labels.append(canonical_hand_label(r1, r2, False))
            else:
                labels.append(canonical_hand_label(r1, r2, True))
                labels.append(canonical_hand_label(r1, r2, False))
    return labels


# ---------------------------------------------------------------------------
# Baseline preflop open-raise (RFI) ranges, 6-max.
#
# These are hand-built approximations of widely published solver-derived
# charts, not the output of an actual solve. They exist so the assistant is
# useful out of the box; treat them as an editable starting point (e.g. for
# your specific home-game stakes/dynamics) rather than ground truth.
# ---------------------------------------------------------------------------

RFI_RANGES_6MAX: Dict[str, str] = {
    "UTG": "77+, ATo+, A9s+, KJo+, KTs+, QJo, QTs+, JTs, T9s",
    "HJ": "66+, A9o+, A8s+, KTo+, K9s+, QTo+, Q9s+, J9s+, T9s, 98s",
    "CO": "55+, A7o+, A5s+, K9o+, K7s+, Q9o+, Q8s+, J8s+, T8s+, 98s, 87s",
    "BTN": (
        "22+, A2o+, A2s+, K2o+, K2s+, Q4o+, Q2s+, J6o+, J4s+, "
        "T6o+, T4s+, 96s+, 86s+, 75s+, 64s+, 54s"
    ),
    "SB": (
        "33+, A5o+, A2s+, K8o+, K5s+, Q9o+, Q7s+, J9o+, J7s+, "
        "T8o+, T7s+, 97s+, 86s+, 76s, 65s"
    ),
}

# Simplified value-3bet ranges vs a single raise, by 3-bettor position.
# (the rest of a "would continue" range should generally flat/call instead)
THREEBET_VALUE_RANGES_6MAX: Dict[str, str] = {
    "UTG": "TT+, AQs+, AKo",
    "HJ": "TT+, AQs+, AKo",
    "CO": "99+, AJs+, AQo+, KQs",
    "BTN": "88+, ATs+, AJo+, KJs+, KQo",
    "SB": "99+, AJs+, AQo+, KQs",
    "BB": "TT+, AQs+, AKo",
}

POSITIONS_6MAX = ("UTG", "HJ", "CO", "BTN", "SB", "BB")
