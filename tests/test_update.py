from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.update import apply_package_update, scan_existing_apps


class ExistingInstallationTests(unittest.TestCase):
    def test_scan_existing_apps_reads_title_cfg(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            storage = Path(temp)
            app = storage / "APPS" / "MyApp"
            app.mkdir(parents=True)
            (app / "BOOT.ELF").write_bytes(b"elf")
            (app / "title.cfg").write_text("title=My App\nboot=BOOT.ELF\n", encoding="utf-8")
            found = scan_existing_apps(storage)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["name"], "My App")
            self.assertEqual(found[0]["relative_path"], "APPS/MyApp/BOOT.ELF")
            self.assertTrue(found[0]["menu_targets"]["opl"])

    def test_update_backs_up_then_removes_and_installs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "package"
            mc_source = package / "1_MEMORY_CARD"
            storage_source = package / "2_USB"
            (mc_source / "BOOT").mkdir(parents=True)
            (mc_source / "SYS-CONF").mkdir(parents=True)
            (mc_source / "BOOT" / "BOOT.ELF").write_bytes(b"new-boot")
            (mc_source / "SYS-CONF" / "PS2BBL.INI").write_text("new-ini")
            (mc_source / "SYS-CONF" / "OSDMENU.CNF").write_text("new-cnf")
            new_app = storage_source / "APPS" / "NewApp"
            new_app.mkdir(parents=True)
            (new_app / "NEW.ELF").write_bytes(b"new")

            mc_target = root / "mc"
            storage_target = root / "storage"
            (mc_target / "BOOT").mkdir(parents=True)
            (mc_target / "BOOT" / "BOOT.ELF").write_bytes(b"old-boot")
            old_app = storage_target / "APPS" / "OldApp"
            old_app.mkdir(parents=True)
            (old_app / "OLD.ELF").write_bytes(b"old")

            result = apply_package_update(package, mc_target, storage_target, ["OldApp"], root / "backups")
            self.assertEqual((mc_target / "BOOT" / "BOOT.ELF").read_bytes(), b"new-boot")
            self.assertFalse(old_app.exists())
            self.assertTrue((storage_target / "APPS" / "NewApp" / "NEW.ELF").is_file())
            backup = Path(result["backup_root"])
            self.assertEqual((backup / "memory_card" / "BOOT" / "BOOT.ELF").read_bytes(), b"old-boot")
            self.assertTrue((backup / "storage" / "APPS" / "OldApp" / "OLD.ELF").is_file())

    def test_reselecting_removed_folder_installs_new_version_after_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "package"
            (package / "1_MEMORY_CARD" / "BOOT").mkdir(parents=True)
            (package / "1_MEMORY_CARD" / "BOOT" / "BOOT.ELF").write_bytes(b"boot")
            source = package / "2_USB" / "APPS" / "Same"
            source.mkdir(parents=True)
            (source / "APP.ELF").write_bytes(b"new")
            mc = root / "mc"
            storage = root / "storage"
            old = storage / "APPS" / "Same"
            old.mkdir(parents=True)
            (old / "APP.ELF").write_bytes(b"old")
            apply_package_update(package, mc, storage, ["Same"], root / "backups")
            self.assertEqual((storage / "APPS" / "Same" / "APP.ELF").read_bytes(), b"new")

    def test_copy_configs_false_preserves_existing_menu_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "package"
            mc_source = package / "1_MEMORY_CARD"
            (mc_source / "BOOT").mkdir(parents=True)
            (mc_source / "SYS-CONF").mkdir(parents=True)
            (mc_source / "BOOT" / "BOOT.ELF").write_bytes(b"boot")
            (mc_source / "SYS-CONF" / "PS2BBL.INI").write_text("new")
            (package / "2_USB" / "APPS").mkdir(parents=True)
            mc = root / "mc"
            (mc / "SYS-CONF").mkdir(parents=True)
            (mc / "SYS-CONF" / "PS2BBL.INI").write_text("keep")
            storage = root / "storage"
            apply_package_update(package, mc, storage, backup_parent=root / "backups", copy_configs=False)
            self.assertEqual((mc / "SYS-CONF" / "PS2BBL.INI").read_text(), "keep")

    def test_copy_boot_false_preserves_existing_boot_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "package"
            (package / "1_MEMORY_CARD" / "BOOT").mkdir(parents=True)
            (package / "1_MEMORY_CARD" / "BOOT" / "BOOT.ELF").write_bytes(b"ps2bbl")
            (package / "2_USB" / "APPS").mkdir(parents=True)
            mc = root / "mc"
            (mc / "BOOT").mkdir(parents=True)
            (mc / "BOOT" / "BOOT.ELF").write_bytes(b"existing-launcher")
            storage = root / "storage"
            apply_package_update(
                package, mc, storage, backup_parent=root / "backups", copy_boot_elf=False
            )
            self.assertEqual((mc / "BOOT" / "BOOT.ELF").read_bytes(), b"existing-launcher")


if __name__ == "__main__":
    unittest.main()
