"""Interactive region calibration tool.

Run as: `python -m pokersoft.app calibrate --layout my_table`

Takes a full-screen screenshot of your poker client (make sure a hand is on
screen, ideally with cards dealt, so you can see where things are), shows it
in a window, and asks you to click-and-drag a rectangle around each region
in turn (hero's two cards, the five board card slots, pot text, your stack,
the amount to call). The result is saved as a TableProfile JSON under
data/profiles/<layout>.json for reuse by `table_state.py`.

This has to be redone whenever the client's window size/zoom changes.
"""

from __future__ import annotations

import tkinter as tk
from typing import List, Optional

from PIL import Image, ImageTk

from .profile import Region, TableProfile
from .screen import grab_full_screen

STEPS = [
    ("hero_card_regions", "Карта героя #1"),
    ("hero_card_regions", "Карта героя #2"),
    ("board_card_regions", "Общая карта #1 (флоп)"),
    ("board_card_regions", "Общая карта #2 (флоп)"),
    ("board_card_regions", "Общая карта #3 (флоп)"),
    ("board_card_regions", "Общая карта #4 (тёрн)"),
    ("board_card_regions", "Общая карта #5 (ривер)"),
    ("pot_text_region", "Текст банка (пот)"),
    ("hero_stack_region", "Стек героя"),
    ("to_call_region", "Сумма 'колл'/текст кнопки колла"),
]


class _Calibrator:
    def __init__(self, root: tk.Tk, screenshot: Image.Image, layout_name: str):
        self.root = root
        self.layout_name = layout_name
        self.profile = TableProfile(name=layout_name)
        self.step_idx = 0
        self.start: Optional[tuple[int, int]] = None
        self.rect_id: Optional[int] = None

        self.scale = min(1.0, 1600 / screenshot.width)
        display_img = screenshot.resize(
            (int(screenshot.width * self.scale), int(screenshot.height * self.scale))
        )
        self.tk_image = ImageTk.PhotoImage(display_img)

        self.canvas = tk.Canvas(root, width=display_img.width, height=display_img.height)
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        self.label = tk.Label(root, text="", font=("Arial", 14))
        self.label.pack()

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        root.bind("<Escape>", lambda e: root.destroy())

        self._update_label()

    def _update_label(self) -> None:
        if self.step_idx >= len(STEPS):
            self.label.config(text="Готово! Закрываю окно...")
            self.profile.save()
            self.root.after(800, self.root.destroy)
            return
        _, prompt = STEPS[self.step_idx]
        self.label.config(text=f"Выделите: {prompt}  ({self.step_idx + 1}/{len(STEPS)})")

    def _on_press(self, event) -> None:
        self.start = (event.x, event.y)
        self.rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="red", width=2
        )

    def _on_drag(self, event) -> None:
        if self.rect_id is None or self.start is None:
            return
        x0, y0 = self.start
        self.canvas.coords(self.rect_id, x0, y0, event.x, event.y)

    def _on_release(self, event) -> None:
        if self.start is None:
            return
        x0, y0 = self.start
        x1, y1 = event.x, event.y
        left, top = min(x0, x1), min(y0, y1)
        width, height = abs(x1 - x0), abs(y1 - y0)
        # undo display scaling to get real screen coordinates
        region: Region = (
            int(left / self.scale),
            int(top / self.scale),
            int(width / self.scale),
            int(height / self.scale),
        )
        field_name, _ = STEPS[self.step_idx]
        current = getattr(self.profile, field_name)
        if isinstance(current, list):
            current.append(region)
        else:
            setattr(self.profile, field_name, region)
        self.step_idx += 1
        self.start = None
        self._update_label()


def run_calibration(layout_name: str) -> str:
    screenshot_arr = grab_full_screen()
    screenshot = Image.fromarray(screenshot_arr)

    root = tk.Tk()
    root.title(f"Калибровка стола: {layout_name}")
    _Calibrator(root, screenshot, layout_name)
    root.mainloop()
    return layout_name
