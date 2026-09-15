from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path


class DependencyError(RuntimeError):
    """Raised when a required runtime dependency cannot be installed."""


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def ensure_py7zr(requirements_path: Path) -> bool:
    """Ensure py7zr is importable.

    Returns True when an installation was performed and False when it was
    already available.
    """

    if module_available("py7zr"):
        return False

    if not requirements_path.is_file():
        raise DependencyError(f"requirements file not found: {requirements_path}")

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "-r",
        str(requirements_path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except OSError as exc:
        raise DependencyError(f"could not start pip: {exc}") from exc

    if completed.returncode != 0:
        output = (completed.stdout or "").strip()
        tail = "\n".join(output.splitlines()[-8:]) if output else "pip returned an error"
        raise DependencyError(tail)

    importlib.invalidate_caches()
    if not module_available("py7zr"):
        raise DependencyError("pip finished successfully, but py7zr is still not importable")

    return True
