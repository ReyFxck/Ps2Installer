from __future__ import annotations

import os
import sys


BANNER = r"""
 ____  ____  ____  ___           _        _ _
|  _ \/ ___||___ \|_ _|_ __  ___| |_ __ _| | | ___ _ __
| |_) \___ \  __) || || '_ \/ __| __/ _` | | |/ _ \ '__|
|  __/ ___) |/ __/ | || | | \__ \ || (_| | | |  __/ |
|_|   |____/|_____|___|_| |_|___/\__\__,_|_|_|\___|_|
""".strip("\n")


class ConsoleUI:
    """Small dependency-free terminal UI helper."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

    def __init__(self, *, color: bool | None = None, clear: bool = True) -> None:
        auto_color = (
            sys.stdout.isatty()
            and os.environ.get("TERM", "") != "dumb"
            and "NO_COLOR" not in os.environ
        )
        self.color = auto_color if color is None else color
        self.clear_enabled = clear

    def paint(self, text: str, *codes: str) -> str:
        if not self.color or not codes:
            return text
        return f"{''.join(codes)}{text}{self.RESET}"

    def clear(self) -> None:
        if not self.clear_enabled or not sys.stdout.isatty():
            return
        if os.name == "nt":
            os.system("cls")
        else:
            print("\033[2J\033[H", end="")

    def banner(self) -> None:
        print(self.paint(BANNER, self.BOLD, self.CYAN))
        print(self.paint("PlayStation 2 Homebrew Package Builder", self.DIM))

    def section(self, title: str, description: str | None = None) -> None:
        print()
        print(self.paint(f"== {title} ==", self.BOLD, self.CYAN))
        if description:
            print(self.paint(description, self.DIM))

    def info(self, message: str) -> None:
        print(f"{self.paint('[i]', self.CYAN)} {message}")

    def success(self, message: str) -> None:
        print(f"{self.paint('[OK]', self.GREEN, self.BOLD)} {message}")

    def warning(self, message: str) -> None:
        print(f"{self.paint('[!]', self.YELLOW, self.BOLD)} {message}")

    def error(self, message: str) -> None:
        print(f"{self.paint('[X]', self.RED, self.BOLD)} {message}")

    def option(self, index: int, label: str, *, default: bool = False) -> None:
        marker = self.paint(f"[{index}]", self.CYAN, self.BOLD)
        suffix = self.paint("  <- default", self.GREEN) if default else ""
        print(f"  {marker} {label}{suffix}")

    def release(self, label: str, version: str, status: str) -> None:
        if status == "stable":
            status_text = self.paint(status, self.GREEN)
        elif status == "development":
            status_text = self.paint(status, self.MAGENTA)
        else:
            status_text = self.paint(status, self.YELLOW)
        print(f"  - {self.paint(label, self.BOLD)}: {version} ({status_text})")

    def path(self, value: str) -> str:
        return self.paint(value, self.BLUE)
