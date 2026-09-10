"""Monte Carlo equity calculation: hero hand/range vs opponent range(s)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .cards import Card, remaining_deck
from .evaluator import evaluate_best
from .ranges import Range, combos_excluding


@dataclass
class EquityResult:
    win: float
    tie: float
    lose: float
    trials: int

    @property
    def equity(self) -> float:
        return self.win + self.tie / 2 if self.tie else self.win

    def __str__(self) -> str:
        return f"win={self.win:.1%} tie={self.tie:.1%} lose={self.lose:.1%} (n={self.trials})"


def _sample_combo(range_: Range, rng: random.Random) -> Sequence[Card]:
    combos = list(range_.keys())
    weights = list(range_.values())
    (chosen,) = rng.choices(combos, weights=weights, k=1)
    return tuple(chosen)


def hand_equity(
    hero: Sequence[Card],
    board: Sequence[Card],
    opponent_ranges: Optional[List[Range]] = None,
    num_random_opponents: int = 1,
    trials: int = 4000,
    seed: Optional[int] = None,
) -> EquityResult:
    """Estimate hero's equity against one or more opponents.

    If `opponent_ranges` is given, each entry is a Range (Combo -> weight) an
    opponent's hole cards are sampled from each trial. Otherwise
    `num_random_opponents` opponents are dealt uniformly random hole cards.
    """
    rng = random.Random(seed)
    hero = list(hero)
    board = list(board)
    known = set(hero) | set(board)

    ranges: List[Optional[Range]]
    if opponent_ranges is not None:
        ranges = [combos_excluding(r, known) for r in opponent_ranges]
        for r in ranges:
            if not r:
                raise ValueError("an opponent range has no combos left after removing dead cards")
    else:
        ranges = [None] * num_random_opponents

    win = tie = lose = 0
    cards_needed_board = 5 - len(board)

    for _ in range(trials):
        used = set(known)
        opp_hands: List[Sequence[Card]] = []
        for r in ranges:
            if r is not None:
                # re-filter for cards used by opponents already sampled this trial
                r_avail = combos_excluding(r, used)
                combo = _sample_combo(r_avail, rng)
            else:
                deck = [c for c in remaining_deck(used)]
                combo = tuple(rng.sample(deck, 2))
            opp_hands.append(combo)
            used.update(combo)

        deck = remaining_deck(used)
        extra_board = rng.sample(deck, cards_needed_board) if cards_needed_board > 0 else []
        full_board = board + list(extra_board)

        hero_score = evaluate_best(hero + full_board)
        opp_scores = [evaluate_best(list(h) + full_board) for h in opp_hands]
        best_opp = max(opp_scores)

        if hero_score > best_opp:
            win += 1
        elif hero_score == best_opp:
            tie += 1
        else:
            lose += 1

    return EquityResult(win / trials, tie / trials, lose / trials, trials)
