from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.package import build_package


class PackageBuilderTests(unittest.TestCase):
    def _write_elf(self, path: Path, marker: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(marker)
        return path

    def test_mx4sio_package_uses_shared_apps_and_correct_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            downloads = root / "downloads"

            ps2bbl = self._write_elf(
                downloads
                / "ps2bbl"
                / "extracted"
                / "PS2BBL-build"
                / "PS2_MX4SIO"
                / "COMPRESSED_PS2BBL.ELF",
                b"ps2bbl-mx4sio",
            )
            osdmenu = self._write_elf(
                downloads / "osdmenu" / "extracted" / "osdmenu.elf",
                b"osdmenu",
            )
            opl = self._write_elf(
                downloads / "opl" / "extracted" / "OPNPS2LD.ELF",
                b"opl",
            )
            wle = self._write_elf(
                downloads / "wlaunchelf" / "extracted" / "BOOT.ELF",
                b"wle",
            )

            plan = {
                "language": "pt-BR",
                "memory_card": {"id": "memcard-pro2", "name": "MemCard PRO2"},
                "storage": {"id": "mx4sio", "name": "MX4SIO"},
                "homebrews": [
                    {
                        "id": "ps2bbl",
                        "name": "PS2BBL",
                        "folder": "PS2BBL",
                        "elf_names": ["COMPRESSED_PS2BBL.ELF"],
                        "menu_targets": {"osdmenu": False, "opl": False},
                        "resolved": {"version": "dev-2026-09-15", "channel": "development", "prerelease": True},
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
                        "id": "opl",
                        "name": "Open PS2 Loader",
                        "folder": "OPL",
                        "elf_names": ["OPNPS2LD.ELF"],
                        "menu_targets": {"osdmenu": True, "opl": False},
                        "resolved": {"version": "v1.2.0-Beta-2245-3e3f34e", "channel": "prerelease", "prerelease": True},
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
                    "ps2bbl": {"extracted_path": str(ps2bbl.parents[2]), "elf_candidates": [str(ps2bbl)]},
                    "osdmenu": {"extracted_path": str(osdmenu.parent), "elf_candidates": [str(osdmenu)]},
                    "opl": {"extracted_path": str(opl.parent), "elf_candidates": [str(opl)]},
                    "wlaunchelf": {"extracted_path": str(wle.parent), "elf_candidates": [str(wle)]},
                },
            }

            manifest = build_package(plan, root)
            package = Path(manifest["package_root"])
            mc = package / "1_MEMCARD_PRO2_VMC"
            storage = package / "2_MX4SIO"

            self.assertEqual((mc / "BOOT" / "BOOT.ELF").read_bytes(), b"ps2bbl-mx4sio")

            ps2bbl_ini = (mc / "SYS-CONF" / "PS2BBL.INI").read_text(encoding="utf-8")
            self.assertIn("LK_AUTO_E1 = $OSDSYS", ps2bbl_ini)
            self.assertIn(
                "LK_R1_E1 = massX:/APPS/OSDMenu/osdmenu.elf",
                ps2bbl_ini,
            )

            osdmenu_cnf = (mc / "SYS-CONF" / "OSDMENU.CNF").read_text(encoding="utf-8")
            self.assertIn("Open PS2 Loader v1.2.0-Beta-2245-3e3f34e", osdmenu_cnf)
            self.assertIn(
                "mx4sio:/APPS/OPL/OPNPS2LD.ELF",
                osdmenu_cnf,
            )
            self.assertIn("mx4sio:/APPS/wLaunchELF/BOOT.ELF", osdmenu_cnf)

            osd_title = (storage / "APPS" / "OSDMenu" / "title.cfg").read_text(encoding="utf-8")
            self.assertEqual(osd_title, "title=OSDMenu v1.3.0\nboot=osdmenu.elf\n")
            self.assertFalse((storage / "APPS" / "OPL" / "title.cfg").exists())
            self.assertTrue((storage / "APPS" / "wLaunchELF" / "title.cfg").exists())

    def test_exfat_hdd_is_explicit_about_ps2bbl_limitation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            osdmenu = self._write_elf(root / "osdmenu.elf", b"osdmenu")
            plan = {
                "language": "en",
                "memory_card": {"id": "standard", "name": "Standard"},
                "storage": {"id": "hdd-exfat", "name": "Internal HDD (exFAT)"},
                "homebrews": [
                    {
                        "id": "osdmenu",
                        "name": "OSDMenu",
                        "folder": "OSDMenu",
                        "elf_names": ["osdmenu.elf"],
                        "menu_targets": {"osdmenu": False, "opl": True},
                        "resolved": {"version": "v1.3.0", "channel": "stable", "prerelease": False},
                    }
                ],
                "downloads": {
                    "osdmenu": {"elf_candidates": [str(osdmenu)]}
                },
            }

            manifest = build_package(plan, root)
            self.assertIsNone(manifest["ps2bbl"])
            self.assertTrue(any("ata:" in warning for warning in manifest["warnings"]))
            ini = (
                Path(manifest["package_root"])
                / "1_MEMORY_CARD"
                / "SYS-CONF"
                / "PS2BBL.INI"
            ).read_text(encoding="utf-8")
            self.assertNotIn("LK_R1_E1", ini)


if __name__ == "__main__":
    unittest.main()
