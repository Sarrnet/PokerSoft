"""Card recognition via template matching.

Poker clients render cards as clean, static graphics (no photographic
noise), which makes template matching a good fit - much simpler and more
robust than training a classifier, as long as you have one reference image
per rank and per suit captured from *your* client at *your* table's zoom
level. Use `build_template_library` (or the calibration tool) to create
them once; after that, recognition is just correlation against 13+4 small
images.

Template layout expected on disk (see data/templates/<layout>/):
    ranks/2.png ... ranks/A.png
    suits/s.png suits/h.png suits/d.png suits/c.png
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np

try:
    import cv2
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "opencv-python is required for card recognition. Install with: pip install opencv-python"
    ) from exc

from ..cards import RANKS, SUITS, Card

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "templates"

MATCH_THRESHOLD = 0.75


def _load_templates(layout: str, subdir: str, keys: str) -> Dict[str, np.ndarray]:
    out = {}
    base = TEMPLATES_DIR / layout / subdir
    for key in keys:
        path = base / f"{key}.png"
        if path.exists():
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                out[key] = img
    return out


class CardReader:
    def __init__(self, layout: str):
        self.layout = layout
        self.rank_templates = _load_templates(layout, "ranks", RANKS)
        self.suit_templates = _load_templates(layout, "suits", SUITS)
        if not self.rank_templates or not self.suit_templates:
            raise FileNotFoundError(
                f"No card templates found for layout '{layout}' under "
                f"{TEMPLATES_DIR / layout}. Capture reference crops first "
                f"(see capture/calibrate.py)."
            )

    @staticmethod
    def _best_match(gray_crop: np.ndarray, templates: Dict[str, np.ndarray]) -> Optional[str]:
        best_key, best_score = None, -1.0
        for key, template in templates.items():
            if template.shape[0] > gray_crop.shape[0] or template.shape[1] > gray_crop.shape[1]:
                continue
            result = cv2.matchTemplate(gray_crop, template, cv2.TM_CCOEFF_NORMED)
            score = float(result.max())
            if score > best_score:
                best_key, best_score = key, score
        if best_score < MATCH_THRESHOLD:
            return None
        return best_key

    def read_card(self, card_image_rgb: np.ndarray) -> Optional[Card]:
        """`card_image_rgb` should be a crop tightly framing one card, where the
        rank glyph occupies the top-left region and the suit glyph sits just
        below/right of it (the common layout for most clients). Split it
        heuristically in half; if your client's card art differs, adjust the
        split in a subclass or crop rank/suit as separate regions instead.
        """
        gray = cv2.cvtColor(card_image_rgb, cv2.COLOR_RGB2GRAY)
        h = gray.shape[0]
        rank_region = gray[: int(h * 0.55), :]
        suit_region = gray[int(h * 0.45) :, :]

        rank_key = self._best_match(rank_region, self.rank_templates)
        suit_key = self._best_match(suit_region, self.suit_templates)
        if rank_key is None or suit_key is None:
            return None
        return Card(rank=Card.parse(f"{rank_key}{suit_key}").rank, suit=suit_key)
