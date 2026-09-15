from __future__ import annotations

import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


class DependencyError(RuntimeError):
    """Raised when an automatic dependency installation fails."""


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def find_native_7z() -> str | None:
    for name in ("7z", "7zz", "7za", "7zr"):
        command = shutil.which(name)
        if command:
            return command
    return None


def running_on_android() -> bool:
    return bool(
        os.environ.get("ANDROID_ROOT")
        or os.environ.get("ANDROID_DATA")
        or os.environ.get("TERMUX_VERSION")
        or sys.platform == "android"
        or hasattr(sys, "getandroidapilevel")
    )


def ensure_py7zr(requirements_file: Path | None = None) -> bool:
    """Ensure optional py7zr is available on desktop Python.

    Native 7-Zip is preferred by the installer whenever present. This helper is
    only the fallback for systems that do not provide a 7z executable.

    Returns False when py7zr already existed and True when it was installed.
    """
    if module_available("py7zr"):
        return False

    if running_on_android():
        raise DependencyError("Android/Termux should use the native 7zip package: pkg install 7zip")

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "py7zr>=1.1,<2",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise DependencyError(f"could not start pip: {exc}") from exc

    if completed.returncode != 0:
        stderr = getattr(completed, "stderr", "") or ""
        stdout = getattr(completed, "stdout", "") or ""
        detail = (stderr or stdout).strip().splitlines()
        tail = detail[-1] if detail else "unknown pip error"
        raise DependencyError(f"pip exited with status {completed.returncode}: {tail}")

    importlib.invalidate_caches()
    if not module_available("py7zr"):
        raise DependencyError("pip finished successfully, but py7zr could not be imported")
    return True
