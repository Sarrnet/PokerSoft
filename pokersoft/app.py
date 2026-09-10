"""Command-line entry point.

Modes:
    manual      Interactive terminal input -> instant recommendation.
                Works immediately, no calibration or screen capture needed.
    calibrate   One-time region calibration for a specific table layout.
    run         Real-time loop: screen capture -> recognition -> overlay.

Run with: python -m pokersoft.app <mode> [options]
"""

from __future__ import annotations

import argparse
import sys
import time

from .cards import parse_cards
from .decision import Action, GameState, Street, analyze
from .opponent_model import OpponentBook


def _prompt(msg: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{msg}{suffix}: ").strip()
    return value or (default or "")


def run_manual() -> None:
    print("PokerSoft — ручной режим. Ctrl+C для выхода.\n")
    book = OpponentBook()
    while True:
        try:
            hero_txt = _prompt("Ваши карты (напр. 'Ah Kd')")
            hero_cards = parse_cards(hero_txt)
            if len(hero_cards) != 2:
                print("Нужно ровно 2 карты героя.\n")
                continue

            board_txt = _prompt("Общие карты (пусто, если префлоп)", default="")
            board_cards = parse_cards(board_txt) if board_txt else []
            street = {0: Street.PREFLOP, 3: Street.FLOP, 4: Street.TURN, 5: Street.RIVER}.get(
                len(board_cards)
            )
            if street is None:
                print("Общих карт должно быть 0, 3, 4 или 5.\n")
                continue

            position = _prompt("Позиция героя (UTG/HJ/CO/BTN/SB/BB)", default="BTN").upper()
            stack_bb = float(_prompt("Стек героя в bb", default="100"))
            pot_bb = float(_prompt("Банк (пот) в bb", default="1.5"))
            to_call_bb = float(_prompt("Сколько нужно доколлировать (bb)", default="0"))
            num_opp = int(_prompt("Число активных соперников в раздаче", default="1"))
            facing_raises = 0
            if street == Street.PREFLOP:
                facing_raises = int(_prompt("Сколько рейзов до героя (0/1/2+)", default="0"))

            opp_name = _prompt("Имя соперника для эксплойт-статистики (Enter — пропустить)", default="")
            opp_stats = book.get(opp_name) if opp_name else None

            state = GameState(
                hero_cards=hero_cards,
                board=board_cards,
                street=street,
                position=position,
                stack_bb=stack_bb,
                pot_bb=pot_bb,
                to_call_bb=to_call_bb,
                num_active_opponents=num_opp,
                facing_preflop_raises=facing_raises,
                opponent_stats=opp_stats,
            )
            analysis = analyze(state)

            print("\n--- Рекомендация ---")
            if analysis.equity_result is not None:
                print(f"Эквити: {analysis.equity_result}")
            g = analysis.gto
            print(f"МАТЕМАТИКА (GTO-базис): {g.action.value.upper()}"
                  + (f" {g.sizing_bb:.1f}bb" if g.sizing_bb else ""))
            print(f"  почему: {g.rationale}")
            e = analysis.exploit
            print(f"ПРО-СТИЛЬ (эксплойт): {e.action.value.upper()}"
                  + (f" {e.sizing_bb:.1f}bb" if e.sizing_bb else ""))
            print(f"  почему: {e.rationale}")
            print()
        except (KeyboardInterrupt, EOFError):
            print("\nВыход.")
            return
        except Exception as exc:
            print(f"Ошибка ввода: {exc}\n")


def run_calibrate(layout: str) -> None:
    from .capture.calibrate import run_calibration

    run_calibration(layout)
    print(f"Профиль сохранён: data/profiles/{layout}.json")


def run_realtime(layout: str, big_blind: float, poll_seconds: float) -> None:
    from .capture.profile import TableProfile
    from .capture.table_state import TableReader
    from .ui.overlay import Overlay

    profile = TableProfile.load(layout)
    reader = TableReader(profile, layout, big_blind=big_blind)

    def poll():
        obs = reader.read()
        if not TableReader.is_complete_enough(obs):
            return None
        board = [c for c in obs.board_cards if c is not None]
        street = {0: Street.PREFLOP, 3: Street.FLOP, 4: Street.TURN, 5: Street.RIVER}.get(
            len(board)
        )
        if street is None:
            return None
        state = GameState(
            hero_cards=obs.hero_cards,
            board=board,
            street=street,
            pot_bb=obs.pot_bb or 1.0,
            to_call_bb=obs.to_call_bb or 0.0,
            stack_bb=obs.hero_stack_bb or 100.0,
        )
        return analyze(state)

    overlay = Overlay(poll)
    overlay.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pokersoft")
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("manual", help="interactive terminal mode, no screen capture")

    p_cal = sub.add_parser("calibrate", help="calibrate screen regions for a table layout")
    p_cal.add_argument("--layout", required=True)

    p_run = sub.add_parser("run", help="real-time screen-capture overlay")
    p_run.add_argument("--layout", required=True)
    p_run.add_argument("--big-blind", type=float, default=1.0)
    p_run.add_argument("--poll-seconds", type=float, default=0.4)

    args = parser.parse_args(argv)

    if args.mode == "manual":
        run_manual()
    elif args.mode == "calibrate":
        run_calibrate(args.layout)
    elif args.mode == "run":
        run_realtime(args.layout, args.big_blind, args.poll_seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
