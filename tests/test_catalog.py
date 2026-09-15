from __future__ import annotations

import json
import unittest
from pathlib import Path


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(__file__).resolve().parents[1] / "catalog" / "homebrews.json"
        cls.catalog = json.loads(path.read_text(encoding="utf-8"))
        cls.apps = cls.catalog["homebrews"]

    def test_catalog_has_unique_ids_and_required_core(self) -> None:
        ids = [app["id"] for app in self.apps]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("ps2bbl", ids)
        self.assertIn("osdmenu", ids)
        self.assertGreaterEqual(len(ids), 50)

    def test_requested_projects_are_present(self) -> None:
        ids = {app["id"] for app in self.apps}
        for app_id in {
            "dkwdrv", "popstarter", "ember", "project-titan", "retroarch",
            "retrolauncher", "snesticleaurora", "pgen",
        }:
            self.assertIn(app_id, ids)

    def test_direct_entries_have_download_metadata(self) -> None:
        for app in self.apps:
            if app.get("source_type") != "direct":
                continue
            self.assertTrue(app.get("channels"))
            for cfg in app["channels"].values():
                self.assertTrue(cfg.get("url"))
                self.assertTrue(cfg.get("asset_name"))


if __name__ == "__main__":
    unittest.main()
