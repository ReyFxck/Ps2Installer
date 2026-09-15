#!/usr/bin/env python3
"""Interactive Ps2Installer prototype with live GitHub release resolution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.downloads import DownloadError, download_release
from src.releases import GitHubError, GitHubReleaseResolver, ResolvedRelease

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "catalog" / "homebrews.json"
OUTPUT_DIR = ROOT / "output"
PLAN_PATH = OUTPUT_DIR / "selection.json"
DOWNLOAD_ROOT = OUTPUT_DIR / "downloads"

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
        "title": "Ps2Installer - protótipo",
        "memory_card": "Qual Memory Card você usa?",
        "storage": "Onde o OSDMenu e os homebrews devem ficar?",
        "homebrew": "Seleção de homebrews",
        "install": "Instalar {name}?",
        "required": "{name}: obrigatório para este modo",
        "resolving": "Consultando versões atuais no GitHub...",
        "resolve_failed": "Não foi possível consultar {name}: {error}",
        "available": "Versões disponíveis:",
        "choose_channel": "Escolha o canal para {name}",
        "saved": "Plano salvo em: {path}",
        "summary": "Resumo",
        "card": "Memory Card",
        "selected_storage": "Armazenamento",
        "selected_apps": "Homebrews selecionados",
        "none": "nenhum opcional",
        "invalid": "Opção inválida. Tente novamente.",
        "download": "Baixar agora os arquivos selecionados?",
        "downloading": "Baixando {name} {version}...",
        "downloaded": "OK: {name} -> {path}",
        "download_failed": "Falha ao baixar {name}: {error}",
        "download_warning": "Aviso para {name}: {warning}",
        "unresolved": "{name} será mantido no plano sem versão resolvida.",
        "done": "Etapa concluída.",
    },
    "en": {
        "title": "Ps2Installer - prototype",
        "memory_card": "Which Memory Card do you use?",
        "storage": "Where should OSDMenu and homebrew be stored?",
        "homebrew": "Homebrew selection",
        "install": "Install {name}?",
        "required": "{name}: required for this mode",
        "resolving": "Checking current GitHub releases...",
        "resolve_failed": "Could not resolve {name}: {error}",
        "available": "Available versions:",
        "choose_channel": "Choose a channel for {name}",
        "saved": "Plan saved to: {path}",
        "summary": "Summary",
        "card": "Memory Card",
        "selected_storage": "Storage",
        "selected_apps": "Selected homebrew",
        "none": "no optional apps",
        "invalid": "Invalid option. Try again.",
        "download": "Download the selected files now?",
        "downloading": "Downloading {name} {version}...",
        "downloaded": "OK: {name} -> {path}",
        "download_failed": "Failed to download {name}: {error}",
        "download_warning": "Warning for {name}: {warning}",
        "unresolved": "{name} will remain in the plan without a resolved version.",
        "done": "Step completed.",
    },
    "es": {
        "title": "Ps2Installer - prototipo",
        "memory_card": "¿Qué Memory Card utilizas?",
        "storage": "¿Dónde deben guardarse OSDMenu y los homebrews?",
        "homebrew": "Selección de homebrews",
        "install": "¿Instalar {name}?",
        "required": "{name}: obligatorio para este modo",
        "resolving": "Consultando versiones actuales en GitHub...",
        "resolve_failed": "No se pudo consultar {name}: {error}",
        "available": "Versiones disponibles:",
        "choose_channel": "Elige un canal para {name}",
        "saved": "Plan guardado en: {path}",
        "summary": "Resumen",
        "card": "Memory Card",
        "selected_storage": "Almacenamiento",
        "selected_apps": "Homebrews seleccionados",
        "none": "ninguna aplicación opcional",
        "invalid": "Opción inválida. Inténtalo de nuevo.",
        "download": "¿Descargar ahora los archivos seleccionados?",
        "downloading": "Descargando {name} {version}...",
        "downloaded": "OK: {name} -> {path}",
        "download_failed": "Error al descargar {name}: {error}",
        "download_warning": "Aviso para {name}: {warning}",
        "unresolved": "{name} permanecerá en el plan sin versión resuelta.",
        "done": "Etapa completada.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a PS2 homebrew installation plan.")
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Resolve versions and write selection.json without downloading assets.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip GitHub release resolution and only create a local selection plan.",
    )
    return parser.parse_args()


def numbered_choice(
    title: str,
    options: list[tuple[str, str]],
    invalid_text: str,
    default_id: str | None = None,
) -> str:
    while True:
        print(f"\n{title}")
        for index, (option_id, label) in enumerate(options, start=1):
            default_mark = " *" if option_id == default_id else ""
            print(f"  [{index}] {label}{default_mark}")
        raw = input("> ").strip()
        if not raw and default_id is not None:
            return default_id
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


def choose_language() -> str:
    print("Ps2Installer")
    print("Choose language / Escolha o idioma / Elige el idioma")
    for index, (_, label) in enumerate(LANGUAGES, start=1):
        print(f"  [{index}] {label}")
    while True:
        raw = input("> ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(LANGUAGES):
            return LANGUAGES[int(raw) - 1][0]
        print("Invalid / Inválido")


def print_release_options(options: list[ResolvedRelease]) -> None:
    for option in options:
        status = "prerelease" if option.prerelease else "stable"
        print(f"  - {option.channel_label}: {option.version} ({status})")


def select_release_option(
    app: dict[str, Any],
    options: list[ResolvedRelease],
    text: dict[str, str],
) -> ResolvedRelease | None:
    if not options:
        return None
    if len(options) == 1:
        return options[0]

    recommended = app.get("recommended_channel")
    option_pairs = [
        (option.channel, f"{option.channel_label}: {option.version}")
        for option in options
    ]
    default_id = recommended if any(o.channel == recommended for o in options) else None
    selected_channel = numbered_choice(
        text["choose_channel"].format(name=app["name"]),
        option_pairs,
        text["invalid"],
        default_id=default_id,
    )
    return next(option for option in options if option.channel == selected_channel)


def app_plan_entry(app: dict[str, Any], resolved: ResolvedRelease | None) -> dict[str, Any]:
    return {
        "id": app["id"],
        "name": app["name"],
        "repository": app.get("repository"),
        "folder": app.get("folder"),
        "elf_names": app.get("elf_names", []),
        "menu_targets": app.get("menu_targets", {}),
        "resolved": resolved.to_dict() if resolved else None,
    }


def write_plan(plan: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PLAN_PATH.open("w", encoding="utf-8") as handle:
        json.dump(plan, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    args = parse_args()
    language = choose_language()
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
    resolver = None if args.offline else GitHubReleaseResolver()
    selected: list[tuple[dict[str, Any], ResolvedRelease | None]] = []

    print(f"\n=== {t['homebrew']} ===")
    if resolver:
        print(t["resolving"])

    for app in catalog["homebrews"]:
        options: list[ResolvedRelease] = []
        resolution_error: str | None = None
        if resolver:
            try:
                options = resolver.resolve_options(app)
            except GitHubError as exc:
                resolution_error = str(exc)

        print(f"\n{app['name']}")
        if options:
            print(t["available"])
            print_release_options(options)
        elif resolution_error:
            print(t["resolve_failed"].format(name=app["name"], error=resolution_error))

        if app.get("required", False):
            print(t["required"].format(name=app["name"]))
            chosen = select_release_option(app, options, t)
            if chosen is None:
                print(t["unresolved"].format(name=app["name"]))
            selected.append((app, chosen))
            continue

        if not yes_no(
            t["install"].format(name=app["name"]),
            default=app.get("default", False),
        ):
            continue

        chosen = select_release_option(app, options, t)
        if chosen is None:
            print(t["unresolved"].format(name=app["name"]))
        selected.append((app, chosen))

    card = get_by_id(MEMORY_CARDS, card_id)
    storage = get_by_id(STORAGES, storage_id)
    plan: dict[str, Any] = {
        "schema_version": 2,
        "language": language,
        "memory_card": card,
        "storage": storage,
        "homebrews": [app_plan_entry(app, resolved) for app, resolved in selected],
        "downloads": {},
    }
    write_plan(plan)

    optional_names = [
        f"{app['name']} {resolved.version if resolved else '(unresolved)'}"
        for app, resolved in selected
        if not app.get("required", False)
    ]

    print(f"\n=== {t['summary']} ===")
    print(f"{t['card']}: {card['name']}")
    print(f"{t['selected_storage']}: {storage['name']}")
    print(f"{t['selected_apps']}: {', '.join(optional_names) if optional_names else t['none']}")
    print(t["saved"].format(path=PLAN_PATH.relative_to(ROOT)))

    should_download = False
    if not args.no_download and not args.offline:
        resolved_count = sum(1 for _, resolved in selected if resolved is not None)
        if resolved_count:
            should_download = yes_no(t["download"], default=True)

    if should_download:
        for app, resolved in selected:
            if resolved is None:
                continue
            print(t["downloading"].format(name=app["name"], version=resolved.version))
            try:
                result = download_release(
                    resolved,
                    DOWNLOAD_ROOT,
                    elf_names=list(app.get("elf_names", [])),
                )
                plan["downloads"][app["id"]] = result
                print(t["downloaded"].format(name=app["name"], path=result["asset_path"]))
                if result.get("warning"):
                    print(
                        t["download_warning"].format(
                            name=app["name"], warning=result["warning"]
                        )
                    )
            except DownloadError as exc:
                plan["downloads"][app["id"]] = {"error": str(exc)}
                print(t["download_failed"].format(name=app["name"], error=exc))
            write_plan(plan)

    print(t["done"])


if __name__ == "__main__":
    main()
