#!/usr/bin/env python3
"""Initial Ps2Installer setup planner.

This first milestone intentionally does not download or copy PS2 binaries yet.
It records the user's hardware/storage choices and selected homebrew so the
package generator can consume a stable plan in the next milestone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "catalog" / "homebrews.json"
OUTPUT_DIR = ROOT / "output"
PLAN_PATH = OUTPUT_DIR / "selection.json"

LANGUAGES = [
    ("pt-BR", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
]

MEMORY_CARDS = [
    {"id": "standard", "family": "mc", "name": "Standard PS2 Memory Card / MagicGate compatible"},
    {"id": "sd2psx", "family": "mmce", "name": "SD2PSX"},
    {"id": "memcard-pro2", "family": "mmce", "name": "MemCard PRO2"},
    {"id": "psxmemcard-gen2", "family": "mmce", "name": "PSxMemCard Gen2"},
    {"id": "other-mmce", "family": "mmce", "name": "Other MMCE-compatible Memory Card"},
]

STORAGES = [
    {"id": "mmce", "name": "MMCE storage"},
    {"id": "mx4sio", "name": "MX4SIO"},
    {"id": "usb", "name": "USB"},
    {"id": "hdd-exfat", "name": "Internal HDD (exFAT)"},
    {"id": "hdd-apa", "name": "Internal HDD (APA/PFS)"},
]

TEXT = {
    "pt-BR": {
        "title": "Ps2Installer - planejador inicial",
        "language": "Escolha o idioma",
        "memory_card": "Qual Memory Card você usa?",
        "storage": "Onde o OSDMenu e os homebrews devem ficar?",
        "homebrew": "Seleção de homebrews",
        "install": "Instalar {name}?",
        "required": "{name}: obrigatório para este modo",
        "saved": "Plano salvo em: {path}",
        "next": "Esta versão ainda não baixa/copia ELFs; ela registra o plano para a próxima etapa do instalador.",
        "summary": "Resumo",
        "card": "Memory Card",
        "selected_storage": "Armazenamento",
        "selected_apps": "Homebrews selecionados",
        "none": "nenhum opcional",
        "invalid": "Opção inválida. Tente novamente.",
    },
    "en": {
        "title": "Ps2Installer - initial setup planner",
        "language": "Choose language",
        "memory_card": "Which Memory Card do you use?",
        "storage": "Where should OSDMenu and homebrew be stored?",
        "homebrew": "Homebrew selection",
        "install": "Install {name}?",
        "required": "{name}: required for this mode",
        "saved": "Plan saved to: {path}",
        "next": "This version does not download/copy ELFs yet; it records the plan for the next installer milestone.",
        "summary": "Summary",
        "card": "Memory Card",
        "selected_storage": "Storage",
        "selected_apps": "Selected homebrew",
        "none": "no optional apps",
        "invalid": "Invalid option. Try again.",
    },
    "es": {
        "title": "Ps2Installer - planificador inicial",
        "language": "Elige el idioma",
        "memory_card": "¿Qué Memory Card utilizas?",
        "storage": "¿Dónde deben guardarse OSDMenu y los homebrews?",
        "homebrew": "Selección de homebrews",
        "install": "¿Instalar {name}?",
        "required": "{name}: obligatorio para este modo",
        "saved": "Plan guardado en: {path}",
        "next": "Esta versión todavía no descarga/copia ELFs; registra el plan para la siguiente etapa del instalador.",
        "summary": "Resumen",
        "card": "Memory Card",
        "selected_storage": "Almacenamiento",
        "selected_apps": "Homebrews seleccionados",
        "none": "ninguna aplicación opcional",
        "invalid": "Opción inválida. Inténtalo de nuevo.",
    },
}


def numbered_choice(title: str, options: list[tuple[str, str]], invalid_text: str) -> str:
    while True:
        print(f"\n{title}")
        for index, (_, label) in enumerate(options, start=1):
            print(f"  [{index}] {label}")
        raw = input("> ").strip()
        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < len(options):
                return options[index][0]
        print(invalid_text)


def yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"{prompt} {suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes", "s", "sim", "sí", "si"}:
            return True
        if raw in {"n", "no", "não", "nao"}:
            return False


def load_catalog() -> dict[str, Any]:
    with CATALOG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_by_id(items: list[dict[str, str]], item_id: str) -> dict[str, str]:
    return next(item for item in items if item["id"] == item_id)


def main() -> None:
    # Language prompt is intentionally readable before a locale is selected.
    print("Ps2Installer")
    print("Choose language / Escolha o idioma / Elige el idioma")
    for index, (_, label) in enumerate(LANGUAGES, start=1):
        print(f"  [{index}] {label}")

    while True:
        raw = input("> ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(LANGUAGES):
            language = LANGUAGES[int(raw) - 1][0]
            break
        print("Invalid / Inválido")

    t = TEXT[language]
    print(f"\n=== {t['title']} ===")

    card_id = numbered_choice(
        t["memory_card"],
        [(item["id"], item["name"]) for item in MEMORY_CARDS],
        t["invalid"],
    )
    storage_id = numbered_choice(
        t["storage"],
        [(item["id"], item["name"]) for item in STORAGES],
        t["invalid"],
    )

    catalog = load_catalog()
    selected: list[dict[str, Any]] = []

    print(f"\n=== {t['homebrew']} ===")
    for app in catalog["homebrews"]:
        if app.get("required", False):
            print(t["required"].format(name=app["name"]))
            selected.append(app)
            continue

        channel_hint = app.get("channel_policy", "auto-detect")
        print(f"\n{app['name']} ({channel_hint})")
        if yes_no(t["install"].format(name=app["name"]), default=app.get("default", False)):
            selected.append(app)

    card = get_by_id(MEMORY_CARDS, card_id)
    storage = get_by_id(STORAGES, storage_id)

    plan = {
        "schema_version": 1,
        "language": language,
        "memory_card": card,
        "storage": storage,
        "homebrews": [
            {
                "id": app["id"],
                "name": app["name"],
                "repository": app.get("repository"),
                "channel_policy": app.get("channel_policy", "auto-detect"),
            }
            for app in selected
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PLAN_PATH.open("w", encoding="utf-8") as handle:
        json.dump(plan, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    optional_names = [app["name"] for app in selected if not app.get("required", False)]

    print(f"\n=== {t['summary']} ===")
    print(f"{t['card']}: {card['name']}")
    print(f"{t['selected_storage']}: {storage['name']}")
    print(f"{t['selected_apps']}: {', '.join(optional_names) if optional_names else t['none']}")
    print(t["saved"].format(path=PLAN_PATH.relative_to(ROOT)))
    print(t["next"])


if __name__ == "__main__":
    main()
