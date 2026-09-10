"""Assembles a `decision.GameState` from screen captures using a calibrated
TableProfile: grabs each region, runs card recognition / OCR on it, and
falls back to `None`/unknown when a region can't be confidently read (a
misread card is worse than a visible gap the user can correct manually).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..cards import Card
from .card_reader import CardReader
from .ocr import read_number
from .profile import TableProfile
from .screen import grab_region


@dataclass
class RawObservation:
    hero_cards: List[Optional[Card]]
    board_cards: List[Optional[Card]]
    pot_bb: Optional[float]
    hero_stack_bb: Optional[float]
    to_call_bb: Optional[float]


class TableReader:
    def __init__(self, profile: TableProfile, layout: str, big_blind: float = 1.0):
        self.profile = profile
        self.card_reader = CardReader(layout)
        self.big_blind = big_blind

    def _read_card_region(self, region) -> Optional[Card]:
        if region is None:
            return None
        image = grab_region(region)
        return self.card_reader.read_card(image)

    def _read_number_region(self, region) -> Optional[float]:
        if region is None:
            return None
        image = grab_region(region)
        value = read_number(image)
        if value is None:
            return None
        return value / self.big_blind

    def read(self) -> RawObservation:
        hero_cards = [self._read_card_region(r) for r in self.profile.hero_card_regions]
        board_cards = [self._read_card_region(r) for r in self.profile.board_card_regions]
        pot_bb = self._read_number_region(self.profile.pot_text_region)
        stack_bb = self._read_number_region(self.profile.hero_stack_region)
        to_call_bb = self._read_number_region(self.profile.to_call_region)
        return RawObservation(
            hero_cards=hero_cards,
            board_cards=board_cards,
            pot_bb=pot_bb,
            hero_stack_bb=stack_bb,
            to_call_bb=to_call_bb,
        )

    @staticmethod
    def is_complete_enough(obs: RawObservation) -> bool:
        """We can compute a recommendation once both hero cards are known
        (board cards may still be partially unread pre-flop)."""
        return all(c is not None for c in obs.hero_cards) and len(obs.hero_cards) == 2
