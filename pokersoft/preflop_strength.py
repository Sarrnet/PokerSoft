"""Preflop hand-strength percentile table.

Rather than hand-typing a "hand strength" ranking, we actually compute each
of the 169 canonical starting hands' raw equity vs. a random hand (heads-up,
all-in, uniformly random board) via Monte Carlo, then rank them. This table
backs push/fold shove decisions and sanity-checks the RFI charts. Results
are cached to a JSON file since the full sweep takes a couple of seconds.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List

from .cards import Card, remaining_deck
from .evaluator import evaluate_best
from .ranges import all_169_hands

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "preflop_strength.json"


def _one_combo_for_label(label: str) -> List[Card]:
    from .cards import RANK_VALUE

    if len(label) == 2:
        r = RANK_VALUE[label[0]]
        return [Card(r, "s"), Card(r, "h")]
    r1, r2, flag = RANK_VALUE[label[0]], RANK_VALUE[label[1]], label[2]
    if flag == "s":
        return [Card(r1, "s"), Card(r2, "s")]
    return [Card(r1, "s"), Card(r2, "h")]


def _equity_vs_random(hero: List[Card], trials: int, rng: random.Random) -> float:
    wins = ties = 0
    for _ in range(trials):
        deck = remaining_deck(hero)
        opp = rng.sample(deck, 2)
        deck2 = remaining_deck(hero + opp)
        board = rng.sample(deck2, 5)
        hero_score = evaluate_best(hero + board)
        opp_score = evaluate_best(opp + board)
        if hero_score > opp_score:
            wins += 1
        elif hero_score == opp_score:
            ties += 1
    return (wins + ties / 2) / trials


def compute_strength_table(trials_per_hand: int = 400, seed: int = 0) -> Dict[str, float]:
    rng = random.Random(seed)
    table: Dict[str, float] = {}
    for label in all_169_hands():
        hero = _one_combo_for_label(label)
        table[label] = _equity_vs_random(hero, trials_per_hand, rng)
    return table


def load_or_compute_strength_table(force: bool = False) -> Dict[str, float]:
    if not force and CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    table = compute_strength_table()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=2, sort_keys=True)
    return table


def percentile_rank(table: Dict[str, float], label: str) -> float:
    """Return 0..1, where 0 = the single best hand (AA), 1 = the worst hand."""
    ordered = sorted(table.keys(), key=lambda k: table[k], reverse=True)
    idx = ordered.index(label)
    return idx / (len(ordered) - 1)
