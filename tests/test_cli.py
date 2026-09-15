from __future__ import annotations

import unittest

from src.app import package_status


class CliPackageStatusTests(unittest.TestCase):
    def test_ready_package(self) -> None:
        manifest = {
            "ps2bbl": {"destination": "BOOT/BOOT.ELF"},
            "installed_apps": {"osdmenu": {}, "opl": {}},
        }
        plan = {
            "homebrews": [
                {"id": "ps2bbl", "name": "PS2BBL"},
                {"id": "osdmenu", "name": "OSDMenu"},
                {"id": "opl", "name": "Open PS2 Loader"},
            ]
        }
        ready, missing = package_status(manifest, plan)
        self.assertTrue(ready)
        self.assertEqual(missing, [])

    def test_incomplete_package_lists_human_names(self) -> None:
        manifest = {"ps2bbl": None, "installed_apps": {"osdmenu": {}}}
        plan = {
            "homebrews": [
                {"id": "ps2bbl", "name": "PS2BBL"},
                {"id": "osdmenu", "name": "OSDMenu"},
                {"id": "opl", "name": "Open PS2 Loader"},
            ]
        }
        ready, missing = package_status(manifest, plan)
        self.assertFalse(ready)
        self.assertEqual(missing, ["PS2BBL/BOOT.ELF", "Open PS2 Loader"])


if __name__ == "__main__":
    unittest.main()
