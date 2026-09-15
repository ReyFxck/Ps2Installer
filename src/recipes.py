from __future__ import annotations

from copy import deepcopy
from typing import Any


_DEFAULT_RECIPES: dict[str, dict[str, Any]] = {
    "single-elf": {
        "id": "single-elf",
        "mode": "single-elf",
        "description": "Install one ELF into its APPS folder.",
    },
    "elf-directory": {
        "id": "elf-directory",
        "mode": "elf-directory",
        "description": "Preserve the directory containing the primary ELF and its sidecar files.",
    },
    "archive-tree": {
        "id": "archive-tree",
        "mode": "archive-tree",
        "description": "Preserve the extracted archive tree.",
    },
    "collection": {
        "id": "collection",
        "mode": "collection",
        "description": "Preserve an extracted multi-ELF/core collection.",
    },
    "manual": {
        "id": "manual",
        "mode": "manual",
        "description": "Document the source and requirements without guessing a deployment layout.",
    },
}


_SPECIAL_RECIPES: dict[str, dict[str, Any]] = {
    "ps2bbl": {
        "id": "ps2bbl-core",
        "mode": "archive-tree",
        "notes": [
            "Select the build variant that matches the APPS storage driver.",
            "The generated BOOT.ELF is a bootloader payload; the chosen boot method may require an external entry point or KELF installer.",
        ],
    },
    "retroarch": {
        "id": "retroarch-bundle",
        "mode": "collection",
        "notes": [
            "Keep the complete RetroArch PS2 bundle together; individual cores may rely on shared files.",
        ],
    },
    "popstarter": {
        "id": "popstarter-manual",
        "mode": "manual",
        "notes": [
            "Sony POPS/BIOS components are not downloaded or bundled.",
            "Use only components you are legally entitled to use.",
        ],
    },
    "popsloader": {
        "id": "popsloader-manual",
        "mode": "manual",
        "notes": [
            "Storage-specific setup is required.",
            "Launching POPSLoader from OPL APPS has had compatibility issues in some OPL 1.2 beta builds; direct launcher entries are safer when affected.",
        ],
    },
    "ember": {
        "id": "ember-manual",
        "mode": "manual",
        "required_user_files": ["bios.bin"],
        "notes": [
            "A user-supplied legally dumped BIOS is required and is never downloaded by Ps2Installer.",
        ],
    },
    "project-titan": {
        "id": "project-titan-manual",
        "mode": "manual",
        "notes": [
            "Project Titan has its own boot/runtime/package deployment and is not treated as a normal APPS ELF.",
        ],
    },
    "retrolauncher": {
        "id": "retrolauncher-manual",
        "mode": "manual",
        "notes": [
            "Deploy the complete RETROLauncher environment instead of copying a single ELF.",
        ],
    },
    "neutrino": {
        "id": "neutrino-manual",
        "mode": "manual",
        "notes": [
            "Neutrino uses a module/config tree and should be deployed as a matched set.",
        ],
    },
    "nhddl": {
        "id": "nhddl-manual",
        "mode": "manual",
        "requires_apps": ["neutrino"],
        "notes": [
            "Use a Neutrino build/configuration compatible with the selected NHDDL release.",
        ],
    },
    "wopl": {
        "id": "wopl-manual",
        "mode": "manual",
        "notes": [
            "wOPL releases may contain multiple variants; Ps2Installer does not guess which variant is appropriate.",
        ],
    },
}


def recipe_for(app: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized deployment recipe for a catalog/plan entry."""
    app_id = str(app.get("id") or "")
    explicit = app.get("recipe")
    if isinstance(explicit, dict):
        recipe = deepcopy(explicit)
        recipe.setdefault("id", app_id or "custom")
        recipe.setdefault("mode", str((app.get("install") or {}).get("mode") or "single-elf"))
        return recipe

    if isinstance(explicit, str) and explicit in _DEFAULT_RECIPES:
        return deepcopy(_DEFAULT_RECIPES[explicit])

    if app_id in _SPECIAL_RECIPES:
        return deepcopy(_SPECIAL_RECIPES[app_id])

    mode = str((app.get("install") or {}).get("mode") or "single-elf")
    if str(app.get("source_type") or "github") == "manual":
        mode = "manual"
    return deepcopy(_DEFAULT_RECIPES.get(mode, {"id": mode, "mode": mode}))


def install_mode_for(app: dict[str, Any]) -> str:
    return str(recipe_for(app).get("mode") or "single-elf")


def recipe_notes(app: dict[str, Any]) -> list[str]:
    recipe = recipe_for(app)
    return [str(value) for value in recipe.get("notes", []) if str(value).strip()]


def write_recipe_guide(package_root, plan: dict[str, Any]) -> str:
    """Write a human-readable deployment recipe summary for selected apps."""
    from pathlib import Path

    root = Path(package_root)
    lines = ["Ps2Installer - Installation Recipes", ""]
    for app in plan.get("homebrews", []) or []:
        recipe = recipe_for(app)
        lines.append(str(app.get("name") or app.get("id") or "App"))
        lines.append(f"  recipe={recipe.get('id', '-')}")
        lines.append(f"  mode={recipe.get('mode', '-')}")
        required_files = recipe.get("required_user_files") or []
        if required_files:
            lines.append("  required-user-files=" + ", ".join(str(value) for value in required_files))
        for note in recipe.get("notes") or []:
            lines.append(f"  note={note}")
        lines.append("")
    path = root / "INSTALL_RECIPES.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
