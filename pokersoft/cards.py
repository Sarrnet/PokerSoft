"""Card and deck primitives shared by the whole engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

RANKS = "23456789TJQKA"
SUITS = "shdc"
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}
VALUE_RANK = {v: r for r, v in RANK_VALUE.items()}


@dataclass(frozen=True, order=True)
class Card:
    rank: int  # 2..14 (14 = Ace)
    suit: str  # one of 's', 'h', 'd', 'c'

    def __post_init__(self) -> None:
        if self.rank not in VALUE_RANK:
            raise ValueError(f"invalid rank value: {self.rank}")
        if self.suit not in SUITS:
            raise ValueError(f"invalid suit: {self.suit!r}")

    def __str__(self) -> str:
        return f"{VALUE_RANK[self.rank]}{self.suit}"

    def __repr__(self) -> str:
        return f"Card({self!s})"

    @staticmethod
    def parse(text: str) -> "Card":
        text = text.strip()
        if len(text) != 2:
            raise ValueError(f"cannot parse card: {text!r}")
        rank_char, suit_char = text[0].upper(), text[1].lower()
        if rank_char not in RANK_VALUE:
            raise ValueError(f"invalid rank char: {rank_char!r}")
        if suit_char not in SUITS:
            raise ValueError(f"invalid suit char: {suit_char!r}")
        return Card(RANK_VALUE[rank_char], suit_char)


def parse_cards(text: str) -> List[Card]:
    """Parse a whitespace/comma separated string of cards, e.g. 'Ah Kd' or 'As,Kh,2c'."""
    text = text.replace(",", " ")
    tokens = [t for t in text.split() if t]
    return [Card.parse(t) for t in tokens]


def full_deck() -> List[Card]:
    return [Card(rank, suit) for rank in VALUE_RANK for suit in SUITS]


def remaining_deck(used: Iterable[Card]) -> List[Card]:
    used_set = set(used)
    return [c for c in full_deck() if c not in used_set]
