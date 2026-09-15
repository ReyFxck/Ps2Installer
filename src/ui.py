from __future__ import annotations

import os
import sys

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[96m"
_BLUE = "\033[94m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_MAGENTA = "\033[95m"


def color_enabled() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def paint(text: str, *codes: str) -> str:
    if not color_enabled():
        return text
    return "".join(codes) + text + _RESET


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    # ANSI works in modern Windows Terminal, PowerShell, Termux and Unix terminals.
    print("\033[2J\033[H", end="")


def banner() -> None:
    art = r"""
 ____  ____  ____  ___           _        _ _
|  _ \/ ___||___ \|_ _|_ __  ___| |_ __ _| | | ___ _ __
| |_) \___ \  __) || || '_ \/ __| __/ _` | | |/ _ \ '__|
|  __/ ___) |/ __/ | || | | \__ \ || (_| | | |  __/ |
|_|   |____/|_____|___|_| |_|___/\__\__,_|_|_|\___|_|
""".strip("\n")
    print(paint(art, _CYAN, _BOLD))
    print(paint("        PS2 homebrew package builder", _MAGENTA, _BOLD))
    print()


def section(step: int, total: int, title: str) -> None:
    print()
    print(paint(f"[{step}/{total}] {title}", _BLUE, _BOLD))
    print(paint("─" * max(26, len(title) + 8), _DIM))


def info(message: str) -> None:
    print(f"{paint('•', _CYAN, _BOLD)} {message}")


def ok(message: str) -> None:
    print(f"{paint('✓', _GREEN, _BOLD)} {message}")


def warn(message: str) -> None:
    print(f"{paint('!', _YELLOW, _BOLD)} {paint(message, _YELLOW)}")


def error(message: str) -> None:
    print(f"{paint('✗', _RED, _BOLD)} {paint(message, _RED)}")


def success_box(title: str, lines: list[str]) -> None:
    width = max([len(title), *(len(line) for line in lines)] or [len(title)]) + 4
    top = "┌" + "─" * width + "┐"
    bottom = "└" + "─" * width + "┘"
    print()
    print(paint(top, _GREEN))
    print(paint("│ " + title.ljust(width - 2) + " │", _GREEN, _BOLD))
    for line in lines:
        print(paint("│ " + line.ljust(width - 2) + " │", _GREEN))
    print(paint(bottom, _GREEN))
