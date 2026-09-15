from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.report import write_installation_report


class ReportTests(unittest.TestCase):
    def test_report_contains_status_paths_and_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = {
                "language": "pt-BR",
                "memory_card": {"name": "Standard"},
                "storage": {"name": "USB"},
                "boot": {"id": "dev1"},
            }
            manifest = {
                "ready": True,
                "installed_apps": {
                    "opl": {"display_name": "Open PS2 Loader v1.1.0", "relative_path": "APPS/OPL/OPNPS2LD.ELF"},
                },
                "warnings": [],
                "manual_sources": [],
                "boot": {"id": "dev1"},
            }
            path = write_installation_report(
                root,
                plan,
                manifest,
                [{"severity": "info", "message": "DEV1 test"}],
            )
            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("Package status: READY", text)
            self.assertIn("APPS/OPL/OPNPS2LD.ELF", text)
            self.assertIn("DEV1 test", text)


if __name__ == "__main__":
    unittest.main()
