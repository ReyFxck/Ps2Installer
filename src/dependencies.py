from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path


class DependencyError(RuntimeError):
    """Raised when an automatic dependency installation fails."""


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def ensure_py7zr(requirements_file: Path) -> bool:
    """Ensure py7zr is available.

    Returns:
        False: py7zr was already installed.
        True: py7zr was installed during this call.

    Raises:
        DependencyError: automatic installation failed.
    """
    if module_available("py7zr"):
        return False

    if not requirements_file.is_file():
        raise DependencyError(
            f"requirements file not found: {requirements_file}"
        )

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "-r",
        str(requirements_file),
    ]

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise DependencyError(
            f"could not start pip: {exc}"
        ) from exc

    if completed.returncode != 0:
        stderr = getattr(completed, "stderr", "") or ""
        stdout = getattr(completed, "stdout", "") or ""
        detail = (stderr or stdout).strip().splitlines()
        tail = detail[-1] if detail else "unknown pip error"

        raise DependencyError(
            f"pip exited with status {completed.returncode}: {tail}"
        )

    importlib.invalidate_caches()

    if not module_available("py7zr"):
        raise DependencyError(
            "pip finished successfully, but py7zr could not be imported"
        )

    return True
