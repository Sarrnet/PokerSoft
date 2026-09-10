"""A table profile describes where on screen to look for each piece of
information for one specific poker client / table layout / window size.

You build one of these once per layout with `calibrate.py`, then reuse it.
Screen-reading is inherently layout-specific: there is no way to reliably
read an arbitrary poker client's table without first telling the tool
where the cards, pot and stack text actually are.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

Region = Tuple[int, int, int, int]  # left, top, width, height

PROFILES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "profiles"


@dataclass
class TableProfile:
    name: str
    hero_card_regions: List[Region] = field(default_factory=list)  # usually 2
    board_card_regions: List[Region] = field(default_factory=list)  # usually 5
    pot_text_region: Region | None = None
    hero_stack_region: Region | None = None
    to_call_region: Region | None = None
    opponent_stack_regions: List[Region] = field(default_factory=list)
    opponent_name_regions: List[Region] = field(default_factory=list)
    num_players: int = 6

    def save(self) -> Path:
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        path = PROFILES_DIR / f"{self.name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
        return path

    @staticmethod
    def load(name: str) -> "TableProfile":
        path = PROFILES_DIR / f"{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TableProfile(**data)

    @staticmethod
    def list_profiles() -> List[str]:
        if not PROFILES_DIR.exists():
            return []
        return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))
