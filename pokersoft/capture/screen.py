"""Thin wrapper around `mss` for grabbing screen regions as numpy arrays."""

from __future__ import annotations

from typing import Tuple

import numpy as np

try:
    import mss
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The 'mss' package is required for screen capture. Install with: pip install mss"
    ) from exc

Region = Tuple[int, int, int, int]  # left, top, width, height


def grab_region(region: Region) -> np.ndarray:
    left, top, width, height = region
    with mss.mss() as sct:
        shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
        arr = np.array(shot)  # BGRA
        return arr[:, :, :3][:, :, ::-1]  # -> RGB


def grab_full_screen(monitor_index: int = 1) -> np.ndarray:
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[monitor_index])
        arr = np.array(shot)
        return arr[:, :, :3][:, :, ::-1]
