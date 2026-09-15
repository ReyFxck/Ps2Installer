from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.dependencies import DependencyError, ensure_py7zr, find_native_7z


class DependencyTests(unittest.TestCase):
    @patch("src.dependencies.module_available", return_value=True)
    @patch("src.dependencies.subprocess.run")
    def test_existing_py7zr_does_not_run_pip(self, run, _available):
        installed = ensure_py7zr(Path("requirements.txt"))
        self.assertFalse(installed)
        run.assert_not_called()

    @patch("src.dependencies.running_on_android", return_value=False)
    @patch("src.dependencies.module_available", side_effect=[False, True])
    @patch("src.dependencies.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
    def test_missing_py7zr_is_installed_with_current_python(self, run, _available, _android):
        installed = ensure_py7zr(Path("requirements.txt"))
        self.assertTrue(installed)
        command = run.call_args.args[0]
        self.assertEqual(command[0], sys.executable)
        self.assertIn("py7zr>=1.1,<2", command)

    @patch("src.dependencies.running_on_android", return_value=False)
    @patch("src.dependencies.module_available", return_value=False)
    @patch("src.dependencies.subprocess.run", return_value=SimpleNamespace(returncode=1))
    def test_pip_failure_is_reported_without_stderr_attribute(self, _run, _available, _android):
        with self.assertRaises(DependencyError):
            ensure_py7zr(Path("requirements.txt"))

    @patch("src.dependencies.running_on_android", return_value=True)
    @patch("src.dependencies.module_available", return_value=False)
    def test_android_never_attempts_pip(self, _available, _android):
        with self.assertRaisesRegex(DependencyError, "pkg install 7zip"):
            ensure_py7zr(Path("requirements.txt"))

    @patch("src.dependencies.shutil.which")
    def test_native_7z_detection(self, which):
        which.side_effect = lambda name: "/termux/bin/7z" if name == "7z" else None
        self.assertEqual(find_native_7z(), "/termux/bin/7z")


if __name__ == "__main__":
    unittest.main()
