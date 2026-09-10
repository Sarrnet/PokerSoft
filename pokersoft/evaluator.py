"""5-to-7 card Texas Hold'em hand evaluator.

Returns a comparable score (bigger is better): (category, tiebreak_tuple).
Category order: 8=straight flush, 7=quads, 6=full house, 5=flush,
4=straight, 3=trips, 2=two pair, 1=pair, 0=high card.

This is a plain, correctness-first implementation (checks all C(7,5)=21
five-card combinations). It is fast enough for interactive use (a few
thousand Monte Carlo trials per decision), not tuned to the level of a
perfect-hash evaluator.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import List, Sequence, Tuple

from .cards import Card

Score = Tuple[int, Tuple[int, ...]]

CATEGORY_NAMES = {
    8: "стрит-флеш",
    7: "каре",
    6: "фулл-хаус",
    5: "флеш",
    4: "стрит",
    3: "сет",
    2: "две пары",
    1: "пара",
    0: "старшая карта",
}


def _straight_high(distinct_ranks_desc: Sequence[int]) -> int | None:
    if len(distinct_ranks_desc) < 5:
        return None
    ranks = list(distinct_ranks_desc)
    if ranks[0] - ranks[4] == 4 and len(set(ranks[:5])) == 5:
        return ranks[0]
    if set(ranks[:5]) == {14, 5, 4, 3, 2} or (
        14 in ranks and {5, 4, 3, 2}.issubset(ranks)
    ):
        # wheel: A-2-3-4-5, straight high card is 5
        low_set = {2, 3, 4, 5}
        if low_set.issubset(ranks) and 14 in ranks:
            return 5
    return None


def evaluate_5(cards: Sequence[Card]) -> Score:
    if len(cards) != 5:
        raise ValueError("evaluate_5 requires exactly 5 cards")
    ranks = sorted((c.rank for c in cards), reverse=True)
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1

    distinct_ranks = sorted(set(ranks), reverse=True)
    straight_high = _straight_high(distinct_ranks) if len(distinct_ranks) == 5 else None

    if is_flush and straight_high:
        return (8, (straight_high,))

    counts = Counter(ranks)
    counts_sorted = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))
    pattern = tuple(c for _, c in counts_sorted)

    if pattern[0] == 4:
        quad_rank = counts_sorted[0][0]
        kicker = counts_sorted[1][0]
        return (7, (quad_rank, kicker))

    if pattern[0] == 3 and len(pattern) > 1 and pattern[1] == 2:
        return (6, (counts_sorted[0][0], counts_sorted[1][0]))

    if is_flush:
        return (5, tuple(ranks))

    if straight_high:
        return (4, (straight_high,))

    if pattern[0] == 3:
        trip = counts_sorted[0][0]
        kickers = sorted((r for r, _ in counts_sorted[1:]), reverse=True)
        return (3, (trip, *kickers))

    if pattern[0] == 2 and len(pattern) > 1 and pattern[1] == 2:
        pairs = sorted([counts_sorted[0][0], counts_sorted[1][0]], reverse=True)
        kicker = counts_sorted[2][0]
        return (2, (*pairs, kicker))

    if pattern[0] == 2:
        pair = counts_sorted[0][0]
        kickers = sorted((r for r, _ in counts_sorted[1:]), reverse=True)
        return (1, (pair, *kickers))

    return (0, tuple(ranks))


def evaluate_best(cards: Sequence[Card]) -> Score:
    """Best 5-card score out of 5..7 given cards."""
    if len(cards) < 5:
        raise ValueError("need at least 5 cards to evaluate a hand")
    if len(cards) == 5:
        return evaluate_5(cards)
    best: Score | None = None
    for combo in combinations(cards, 5):
        score = evaluate_5(combo)
        if best is None or score > best:
            best = score
    assert best is not None
    return best


def describe(score: Score) -> str:
    return CATEGORY_NAMES[score[0]]
