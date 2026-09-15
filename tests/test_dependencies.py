from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.dependencies import DependencyError, ensure_py7zr


class DependencyTests(unittest.TestCase):
    def test_existing_py7zr_does_not_run_pip(self) -> None:
        with patch("src.dependencies.module_available", return_value=True), patch(
            "src.dependencies.subprocess.run"
        ) as run:
            installed = ensure_py7zr(Path("requirements.txt"))
        self.assertFalse(installed)
        run.assert_not_called()

    def test_missing_py7zr_is_installed_with_current_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            requirements = Path(tmp) / "requirements.txt"
            requirements.write_text("py7zr>=0.22,<1.0\n", encoding="utf-8")
            completed = SimpleNamespace(returncode=0, stdout="installed")
            with patch(
                "src.dependencies.module_available", side_effect=[False, True]
            ), patch("src.dependencies.subprocess.run", return_value=completed) as run:
                installed = ensure_py7zr(requirements)

        self.assertTrue(installed)
        command = run.call_args.args[0]
        self.assertIn("-m", command)
        self.assertIn("pip", command)
        self.assertIn("-r", command)
        self.assertIn(str(requirements), command)

    def test_pip_failure_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            requirements = Path(tmp) / "requirements.txt"
            requirements.write_text("py7zr\n", encoding="utf-8")
            completed = SimpleNamespace(returncode=1, stdout="pip failed badly")
            with patch("src.dependencies.module_available", return_value=False), patch(
                "src.dependencies.subprocess.run", return_value=completed
            ):
                with self.assertRaisesRegex(DependencyError, "pip failed badly"):
                    ensure_py7zr(requirements)


if __name__ == "__main__":
    unittest.main()
