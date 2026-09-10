"""OCR helpers for reading pot/stack/bet text off the table."""

from __future__ import annotations

import re
from typing import Optional

import numpy as np

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

_NUMBER_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def read_text(image: np.ndarray) -> str:
    if pytesseract is None:
        raise ImportError(
            "pytesseract is required for OCR. Install with: pip install pytesseract "
            "(and the tesseract-ocr system binary)."
        )
    return pytesseract.image_to_string(image, config="--psm 7")


def read_number(image: np.ndarray) -> Optional[float]:
    """Read a number like '$12.50', '1,250', 'Pot: 340' out of a small crop."""
    text = read_text(image)
    match = _NUMBER_RE.search(text.replace(" ", ""))
    if not match:
        return None
    cleaned = match.group(0).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None
