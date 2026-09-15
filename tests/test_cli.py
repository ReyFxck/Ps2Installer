from __future__ import annotations

import unittest

from src.app import _local_app_from_path, _sanitize_downloads, package_status, parse_app_selection, parse_multi_selection


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

    def test_manual_sources_do_not_make_package_incomplete(self) -> None:
        manifest = {
            "ps2bbl": {"destination": "BOOT/BOOT.ELF"},
            "installed_apps": {"osdmenu": {}},
        }
        plan = {
            "homebrews": [
                {"id": "ps2bbl", "name": "PS2BBL"},
                {"id": "osdmenu", "name": "OSDMenu"},
                {"id": "popstarter", "name": "POPStarter", "source_type": "manual"},
            ]
        }
        ready, missing = package_status(manifest, plan)
        self.assertTrue(ready)
        self.assertEqual(missing, [])


class MultiSelectionTests(unittest.TestCase):
    def test_comma_selection_without_spaces(self) -> None:
        selected, jump = parse_multi_selection("1,2", 5, [0, 2])
        self.assertEqual(selected, [0, 1])
        self.assertFalse(jump)

    def test_comma_selection_with_spaces(self) -> None:
        selected, jump = parse_multi_selection("1, 2", 5, [0, 2])
        self.assertEqual(selected, [0, 1])
        self.assertFalse(jump)

    def test_p_alone_uses_defaults_and_jumps(self) -> None:
        selected, jump = parse_multi_selection("P", 5, [0, 2])
        self.assertEqual(selected, [0, 2])
        self.assertTrue(jump)

    def test_numbers_plus_p_keep_explicit_selection(self) -> None:
        selected, jump = parse_multi_selection("1, 3, P", 5, [1])
        self.assertEqual(selected, [0, 2])
        self.assertTrue(jump)

    def test_a_selects_all(self) -> None:
        selected, jump = parse_multi_selection("A", 4, [])
        self.assertEqual(selected, [0, 1, 2, 3])
        self.assertFalse(jump)

    def test_invalid_index_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_multi_selection("1,99", 3, [])


class ExtendedSelectionTests(unittest.TestCase):
    def test_l_requests_local_import_without_losing_defaults(self) -> None:
        selected, jump, local = parse_app_selection("L", 4, [0, 2])
        self.assertEqual(selected, [0, 2])
        self.assertFalse(jump)
        self.assertTrue(local)

    def test_numbers_local_and_p_can_be_combined(self) -> None:
        selected, jump, local = parse_app_selection("1, 3, L, P", 5, [])
        self.assertEqual(selected, [0, 2])
        self.assertTrue(jump)
        self.assertTrue(local)

    def test_local_elf_entry_targets_both_menus(self) -> None:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "MYAPP.ELF"
            path.write_bytes(b"elf")
            text = {"local_invalid": "bad {path}", "local_name": "Name"}
            app = _local_app_from_path(path, text, ask_name=False)
            self.assertEqual(app["source_type"], "local")
            self.assertTrue(app["menu_targets"]["opl"])
            self.assertTrue(app["menu_targets"]["osdmenu"])


class TemporaryDownloadPlanTests(unittest.TestCase):
    def test_sanitize_downloads_drops_ephemeral_paths(self) -> None:
        plan = {
            "downloads": {
                "opl": {
                    "asset_path": "/tmp/x.7z",
                    "extracted_path": "/tmp/x",
                    "elf_candidates": ["/tmp/x/OPNPS2LD.ELF"],
                    "extracted": True,
                    "warning": None,
                }
            }
        }
        _sanitize_downloads(plan)
        self.assertEqual(
            plan["downloads"]["opl"],
            {"downloaded": True, "extracted": True, "warning": None, "error": None},
        )
        self.assertTrue(plan["downloads_temporary"])


if __name__ == "__main__":
    unittest.main()
