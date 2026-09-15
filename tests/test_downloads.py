from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.downloads import DownloadError, _safe_extract_7z


class SevenZipBackendTests(unittest.TestCase):
    def test_native_7z_is_used(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "test.7z"
            archive.write_bytes(b"fake")
            dest = root / "out"
            listing = SimpleNamespace(returncode=0, stdout="Path = folder/file.elf\n", stderr="")
            extracted = SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch("src.downloads._native_7z_command", return_value="/bin/7z"), patch(
                "src.downloads.subprocess.run", side_effect=[listing, extracted]
            ) as run:
                _safe_extract_7z(archive, dest)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args_list[0].args[0][1], "l")
            self.assertEqual(run.call_args_list[1].args[0][1], "x")

    def test_native_7z_listing_blocks_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "test.7z"
            archive.write_bytes(b"fake")
            dest = root / "out"
            listing = SimpleNamespace(returncode=0, stdout="Path = ../evil.elf\n", stderr="")
            with patch("src.downloads._native_7z_command", return_value="/bin/7z"), patch(
                "src.downloads.subprocess.run", return_value=listing
            ) as run:
                with self.assertRaisesRegex(DownloadError, "Unsafe 7z entry"):
                    _safe_extract_7z(archive, dest)
            self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
