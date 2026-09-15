from __future__ import annotations

import unittest

from src.recipes import install_mode_for, recipe_for


class RecipeTests(unittest.TestCase):
    def test_retroarch_bundle_uses_collection_recipe(self) -> None:
        recipe = recipe_for({"id": "retroarch", "install": {"mode": "single-elf"}})
        self.assertEqual(recipe["id"], "retroarch-bundle")
        self.assertEqual(recipe["mode"], "collection")

    def test_ember_recipe_records_user_bios_requirement(self) -> None:
        recipe = recipe_for({"id": "ember", "source_type": "manual"})
        self.assertIn("bios.bin", recipe["required_user_files"])
        self.assertEqual(install_mode_for({"id": "ember", "source_type": "manual"}), "manual")

    def test_explicit_local_recipe_wins(self) -> None:
        app = {"id": "local-test", "recipe": {"id": "local-elf", "mode": "single-elf"}}
        self.assertEqual(recipe_for(app)["id"], "local-elf")


if __name__ == "__main__":
    unittest.main()
