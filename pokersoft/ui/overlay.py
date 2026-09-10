"""A small always-on-top overlay window showing the current recommendation.

Kept deliberately simple (plain tkinter, polling refresh) so it has no
heavy UI dependencies. Pin it in a corner of the screen away from the table.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from ..decision import Analysis

REFRESH_MS = 400


class Overlay:
    def __init__(self, poll_fn: Callable[[], Optional[Analysis]]):
        self.poll_fn = poll_fn
        self.root = tk.Tk()
        self.root.title("PokerSoft")
        self.root.attributes("-topmost", True)
        self.root.geometry("360x220+40+40")
        self.root.configure(bg="#111")

        self.status_label = tk.Label(
            self.root, text="Ожидание данных...", fg="#aaa", bg="#111",
            font=("Consolas", 10), justify="left", anchor="w",
        )
        self.status_label.pack(fill="x", padx=8, pady=(8, 2))

        self.gto_label = tk.Label(
            self.root, text="", fg="#4dd0e1", bg="#111",
            font=("Consolas", 12, "bold"), justify="left", anchor="w", wraplength=340,
        )
        self.gto_label.pack(fill="x", padx=8, pady=2)

        self.exploit_label = tk.Label(
            self.root, text="", fg="#ffd54f", bg="#111",
            font=("Consolas", 12, "bold"), justify="left", anchor="w", wraplength=340,
        )
        self.exploit_label.pack(fill="x", padx=8, pady=2)

        self.rationale_label = tk.Label(
            self.root, text="", fg="#ccc", bg="#111",
            font=("Consolas", 9), justify="left", anchor="w", wraplength=340,
        )
        self.rationale_label.pack(fill="x", padx=8, pady=(2, 8))

        self._tick()

    def _tick(self) -> None:
        try:
            analysis = self.poll_fn()
        except Exception as exc:  # keep the overlay alive even if a read fails
            self.status_label.config(text=f"Ошибка чтения стола: {exc}")
            analysis = None

        if analysis is not None:
            self.status_label.config(text="Данные обновлены")
            eq_txt = (
                f"эквити {analysis.equity_result.equity:.0%}"
                if analysis.equity_result is not None
                else ""
            )
            self.gto_label.config(
                text=f"МАТЕМАТИКА: {analysis.gto.action.value.upper()}"
                + (f" {analysis.gto.sizing_bb:.1f}bb" if analysis.gto.sizing_bb else "")
                + (f"  ({eq_txt})" if eq_txt else "")
            )
            self.exploit_label.config(
                text=f"ПРО-СТИЛЬ: {analysis.exploit.action.value.upper()}"
                + (f" {analysis.exploit.sizing_bb:.1f}bb" if analysis.exploit.sizing_bb else "")
            )
            self.rationale_label.config(text=analysis.exploit.rationale)

        self.root.after(REFRESH_MS, self._tick)

    def run(self) -> None:
        self.root.mainloop()
