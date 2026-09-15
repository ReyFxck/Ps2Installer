from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.package import build_package


def _base_plan(root: Path, storage: dict) -> dict:
    extracted = root / "downloads"
    ps2bbl_root = extracted / "ps2bbl" / "extracted" / "release"
    for variant in ("PS2", "PS2_HDD", "PS2_MMCE", "PS2_MX4SIO"):
        folder = ps2bbl_root / variant
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "COMPRESSED_PS2BBL.ELF").write_bytes(variant.encode())

    osd = extracted / "osdmenu" / "extracted" / "osdmenu.elf"
    osd.parent.mkdir(parents=True, exist_ok=True)
    osd.write_bytes(b"osd")
    wle = extracted / "wlaunchelf" / "extracted" / "BOOT.ELF"
    wle.parent.mkdir(parents=True, exist_ok=True)
    wle.write_bytes(b"wle")

    return {
        "language": "pt-BR",
        "memory_card": {"id": "standard", "name": "Standard"},
        "storage": storage,
        "homebrews": [
            {
                "id": "ps2bbl",
                "name": "PS2BBL",
                "folder": "PS2BBL",
                "elf_names": ["COMPRESSED_PS2BBL.ELF"],
                "menu_targets": {"osdmenu": False, "opl": False},
                "resolved": {"version": "dev-test", "channel": "development", "prerelease": True},
            },
            {
                "id": "osdmenu",
                "name": "OSDMenu",
                "folder": "OSDMenu",
                "elf_names": ["osdmenu.elf"],
                "menu_targets": {"osdmenu": False, "opl": True},
                "resolved": {"version": "v1.3.0", "channel": "stable", "prerelease": False},
            },
            {
                "id": "wlaunchelf",
                "name": "wLaunchELF",
                "folder": "wLaunchELF",
                "elf_names": ["BOOT.ELF"],
                "menu_targets": {"osdmenu": True, "opl": True},
                "resolved": {"version": "dev-2026-09-03", "channel": "development", "prerelease": True},
            },
        ],
        "downloads": {
            "ps2bbl": {"extracted_path": str(ps2bbl_root.parent)},
            "osdmenu": {"elf_candidates": [str(osd)]},
            "wlaunchelf": {"elf_candidates": [str(wle)]},
        },
    }


class PackageBuilderTests(unittest.TestCase):
    def test_usb_uses_separate_ps2bbl_and_osdmenu_prefixes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "usb", "name": "USB"})
            manifest = build_package(plan, root)
            mc = Path(manifest["package_root"]) / manifest["memory_card_folder"]
            ini = (mc / "SYS-CONF" / "PS2BBL.INI").read_text()
            cnf = (mc / "SYS-CONF" / "OSDMENU.CNF").read_text()
            self.assertIn("mass:/APPS/OSDMenu/osdmenu.elf", ini)
            self.assertIn("usb:/APPS/wLaunchELF/BOOT.ELF", cnf)
            self.assertIn("[Development]", cnf)
            self.assertNotIn("[Prerelease]", cnf)

    def test_hdd_apa_uses_selected_pfs_partition_and_hdd_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "hdd-apa", "name": "HDD APA", "apa_partition": "+OPL"})
            manifest = build_package(plan, root)
            self.assertEqual(manifest["ps2bbl"]["variant"], "PS2_HDD")
            mc = Path(manifest["package_root"]) / manifest["memory_card_folder"]
            ini = (mc / "SYS-CONF" / "PS2BBL.INI").read_text()
            cnf = (mc / "SYS-CONF" / "OSDMENU.CNF").read_text()
            self.assertIn("hdd0:+OPL:pfs:/APPS/OSDMenu/osdmenu.elf", ini)
            self.assertIn("hdd0:+OPL:pfs:/APPS/wLaunchELF/BOOT.ELF", cnf)

    def test_hdd_apa_non_default_partition_generates_opl_helper(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "hdd-apa", "name": "HDD APA", "apa_partition": "__common"})
            manifest = build_package(plan, root)
            helper = Path(manifest["package_root"]) / "3_HDD_APA_OPL_CONFIG" / "__common" / "OPL" / "conf_hdd.cfg"
            self.assertEqual(helper.read_text().strip(), "hdd_partition=__common")


    def test_user_can_disable_r1_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "usb", "name": "USB"})
            plan["boot"] = {"id": "existing", "r1_osdmenu": False}
            manifest = build_package(plan, root)
            mc = Path(manifest["package_root"]) / manifest["memory_card_folder"]
            ini = (mc / "SYS-CONF" / "PS2BBL.INI").read_text()
            self.assertNotIn("LK_R1_E1", ini)
            self.assertIn("disabled by the user", ini)

    def test_exfat_keeps_ps2bbl_but_does_not_invent_r1_ata_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "hdd-exfat", "name": "HDD exFAT"})
            manifest = build_package(plan, root)
            self.assertEqual(manifest["ps2bbl"]["variant"], "PS2")
            mc = Path(manifest["package_root"]) / manifest["memory_card_folder"]
            ini = (mc / "SYS-CONF" / "PS2BBL.INI").read_text()
            cnf = (mc / "SYS-CONF" / "OSDMENU.CNF").read_text()
            self.assertNotIn("LK_R1_E1", ini)
            self.assertIn("ata:/APPS/wLaunchELF/BOOT.ELF", cnf)
            self.assertTrue(manifest["warnings"])

    def test_manual_source_writes_manual_sources_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "usb", "name": "USB"})
            plan["homebrews"].append({
                "id": "popstarter",
                "name": "POPStarter",
                "source_type": "manual",
                "source_url": "https://example.invalid/popstarter",
                "manual_note": "Manual setup required.",
            })
            manifest = build_package(plan, root)
            manual = Path(manifest["package_root"]) / "MANUAL_SOURCES.txt"
            text = manual.read_text()
            self.assertIn("POPStarter", text)
            self.assertIn("https://example.invalid/popstarter", text)
            self.assertEqual(manifest["manual_sources"][0]["name"], "POPStarter")

    def test_archive_tree_preserves_sidecar_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "usb", "name": "USB"})
            extracted = root / "downloads" / "bundle" / "extracted" / "wrapper"
            extracted.mkdir(parents=True)
            (extracted / "bundle.elf").write_bytes(b"elf")
            (extracted / "settings.cfg").write_text("keep-me")
            plan["homebrews"].append({
                "id": "bundle",
                "name": "Bundle",
                "folder": "Bundle",
                "elf_names": ["bundle.elf"],
                "install": {"mode": "archive-tree"},
                "menu_targets": {"osdmenu": True, "opl": True},
                "resolved": {"version": "1.0", "channel": "stable", "prerelease": False},
            })
            plan["downloads"]["bundle"] = {
                "extracted_path": str(extracted.parent),
                "elf_candidates": [str(extracted / "bundle.elf")],
            }
            manifest = build_package(plan, root)
            storage = Path(manifest["package_root"]) / manifest["storage_folder"]
            self.assertEqual((storage / "APPS" / "Bundle" / "settings.cfg").read_text(), "keep-me")
            self.assertTrue((storage / "APPS" / "Bundle" / "bundle.elf").is_file())

    def test_package_writes_boot_recipe_and_installation_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "usb", "name": "USB"})
            plan["boot"] = {"id": "dev1"}
            manifest = build_package(plan, root)
            package = Path(manifest["package_root"])
            self.assertTrue((package / "BOOT_METHOD.txt").is_file())
            self.assertTrue((package / "INSTALL_RECIPES.txt").is_file())
            self.assertTrue((package / "INSTALLATION_REPORT.txt").is_file())
            self.assertEqual(manifest["boot"]["id"], "dev1")

    def test_update_rebuild_keeps_detected_existing_app_in_osdmenu(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "usb", "name": "USB"})
            plan["workflow"] = {"mode": "update", "rebuild_menus": True, "remove_folders": []}
            plan["existing_apps"] = [{
                "id": "existing:SMS",
                "name": "SMS",
                "folder": "SMS",
                "elf": "SMS.ELF",
                "relative_path": "APPS/SMS/SMS.ELF",
                "menu_targets": {"osdmenu": True, "opl": True},
            }]
            manifest = build_package(plan, root)
            mc = Path(manifest["package_root"]) / manifest["memory_card_folder"]
            cnf = (mc / "SYS-CONF" / "OSDMENU.CNF").read_text()
            self.assertIn("usb:/APPS/SMS/SMS.ELF", cnf)
            self.assertTrue(manifest["installed_apps"]["existing:SMS"]["existing"])

    def test_local_elf_is_packaged_and_gets_title_cfg(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = _base_plan(root, {"id": "usb", "name": "USB"})
            local = root / "MyLocal.ELF"
            local.write_bytes(b"local")
            plan["homebrews"].append({
                "id": "local-mylocal",
                "name": "My Local",
                "source_type": "local",
                "folder": "My-Local",
                "elf_names": ["MyLocal.ELF"],
                "menu_targets": {"osdmenu": True, "opl": True},
                "install": {"mode": "single-elf"},
                "recipe": {"id": "local-elf", "mode": "single-elf"},
            })
            plan["downloads"]["local-mylocal"] = {"elf_candidates": [str(local)], "extracted": True}
            manifest = build_package(plan, root)
            storage = Path(manifest["package_root"]) / manifest["storage_folder"]
            app_dir = storage / "APPS" / "My-Local"
            self.assertEqual((app_dir / "MyLocal.ELF").read_bytes(), b"local")
            self.assertIn("boot=MyLocal.ELF", (app_dir / "title.cfg").read_text())


if __name__ == "__main__":
    unittest.main()
