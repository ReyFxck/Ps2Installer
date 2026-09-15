from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.boot import boot_method_meta, write_boot_guide


class BootMethodTests(unittest.TestCase):
    def test_system_update_is_explicit_about_external_kelf(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = {"language": "pt-BR", "boot": {"id": "system-update"}}
            manifest = write_boot_guide(root, plan, {"variant": "PS2"})
            text = (root / "BOOT_METHOD.txt").read_text(encoding="utf-8")
            self.assertTrue(manifest["external_required"])
            self.assertIn("SYSTEM.XLF", text)
            self.assertIn("não cria um KELF válido", text)

    def test_dev1_payload_does_not_require_an_extra_installer(self) -> None:
        meta = boot_method_meta("dev1")
        self.assertFalse(meta["external_required"])
        self.assertTrue(meta["autoboot"])


if __name__ == "__main__":
    unittest.main()
