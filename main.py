#!/usr/bin/env python3
"""Interactive Ps2Installer with live release resolution and package generation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from src.dependencies import DependencyError, ensure_py7zr
from src.downloads import DownloadError, download_release
from src.package import PackageError, build_package
from src.releases import GitHubError, GitHubReleaseResolver, ResolvedRelease
from src.ui import ConsoleUI

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "catalog" / "homebrews.json"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
DEFAULT_OUTPUT_DIR = ROOT / "output"

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
        "title": "Ps2Installer",
        "intro": "Este assistente prepara PS2BBL, OSDMenu e os homebrews escolhidos em pastas prontas para copiar. Nada é gravado diretamente no PS2: o resultado fica somente na pasta de saída escolhida.",
        "output_title": "Pasta de saída",
        "output_help": "Aqui ficarão o plano, os downloads temporários e o pacote final para o PS2.",
        "output_location": "Onde você quer salvar os downloads e o pacote final?",
        "output_project": "Junto do projeto (./output)",
        "output_custom": "Escolher outra pasta",
        "custom_output": "Digite o caminho da pasta de saída",
        "output_error": "Não foi possível usar essa pasta: {error}",
        "output_selected": "Saída selecionada: {path}",
        "hardware_title": "Memory Card e armazenamento",
        "hardware_help": "PS2BBL e configurações ficam no Memory Card/VMC. OSDMenu e os aplicativos maiores ficam no armazenamento escolhido abaixo.",
        "memory_card": "Qual Memory Card você usa?",
        "storage": "Onde o OSDMenu e os homebrews devem ficar?",
        "homebrew": "Seleção de homebrews",
        "homebrew_help": "Componentes obrigatórios são incluídos automaticamente. Para os opcionais, escolha Y/N e depois o canal quando houver Stable/Beta/Development.",
        "install": "Instalar {name}?",
        "required": "{name}: obrigatório para este modo",
        "resolving": "Consultando versões atuais no GitHub...",
        "resolve_failed": "Não foi possível consultar {name}: {error}",
        "available": "Versões disponíveis:",
        "choose_channel": "Escolha o canal para {name}",
        "saved": "Plano salvo em: {path}",
        "summary": "Revisão",
        "summary_help": "Confira as escolhas antes dos downloads. As versões abaixo são exatamente as que entrarão no pacote.",
        "card": "Memory Card",
        "selected_storage": "Armazenamento",
        "selected_apps": "Homebrews selecionados",
        "none": "nenhum opcional",
        "invalid": "Opção inválida. Tente novamente.",
        "download": "Baixar agora os arquivos selecionados?",
        "downloads_title": "Downloads",
        "downloads_help": "Os releases escolhidos serão baixados e extraídos. Dependências necessárias são verificadas automaticamente antes de começar.",
        "dependency_check": "Verificando suporte a arquivos .7z...",
        "dependency_install": "py7zr não foi encontrado. Instalando automaticamente pelo pip...",
        "dependency_ready": "py7zr pronto para extrair arquivos .7z.",
        "dependency_failed": "Não foi possível instalar py7zr automaticamente:\n{error}\nExecute manualmente: python -m pip install -r requirements.txt",
        "downloading": "Baixando {name} {version}...",
        "downloaded": "{name} baixado: {path}",
        "download_failed": "Falha ao baixar {name}: {error}",
        "download_warning": "{name}: {warning}",
        "unresolved": "{name} será mantido no plano sem versão resolvida.",
        "generate_package": "Gerar agora o pacote pronto para copiar aos dispositivos?",
        "package_title": "Pacote PS2",
        "package_help": "Organizando Memory Card/VMC, APPS, PS2BBL.INI, OSDMENU.CNF, title.cfg e instruções de cópia.",
        "package_done": "Pacote gerado em: {path}",
        "package_failed": "Falha ao gerar o pacote: {error}",
        "package_warning": "{warning}",
        "done_title": "Concluído",
        "done": "Leia os README-COPY-HERE.txt antes de copiar os arquivos para o PS2.",
    },
    "en": {
        "title": "Ps2Installer",
        "intro": "This wizard prepares PS2BBL, OSDMenu and the selected homebrew in folders ready to copy. Nothing is written directly to the PS2; everything stays inside the selected output folder.",
        "output_title": "Output folder",
        "output_help": "The installation plan, temporary downloads and final PS2 package will be stored here.",
        "output_location": "Where should downloads and the final package be saved?",
        "output_project": "Inside the project (./output)",
        "output_custom": "Choose another folder",
        "custom_output": "Enter the output folder path",
        "output_error": "Could not use that folder: {error}",
        "output_selected": "Selected output: {path}",
        "hardware_title": "Memory Card and storage",
        "hardware_help": "PS2BBL and configuration live on the Memory Card/VMC. OSDMenu and larger applications live on the storage selected below.",
        "memory_card": "Which Memory Card do you use?",
        "storage": "Where should OSDMenu and homebrew be stored?",
        "homebrew": "Homebrew selection",
        "homebrew_help": "Required components are included automatically. For optional apps choose Y/N, then select Stable/Beta/Development when more than one channel exists.",
        "install": "Install {name}?",
        "required": "{name}: required for this mode",
        "resolving": "Checking current GitHub releases...",
        "resolve_failed": "Could not resolve {name}: {error}",
        "available": "Available versions:",
        "choose_channel": "Choose a channel for {name}",
        "saved": "Plan saved to: {path}",
        "summary": "Review",
        "summary_help": "Review the choices before downloading. These are the exact versions that will be used in the package.",
        "card": "Memory Card",
        "selected_storage": "Storage",
        "selected_apps": "Selected homebrew",
        "none": "no optional apps",
        "invalid": "Invalid option. Try again.",
        "download": "Download the selected files now?",
        "downloads_title": "Downloads",
        "downloads_help": "Selected releases will be downloaded and extracted. Required Python dependencies are checked automatically before downloads begin.",
        "dependency_check": "Checking .7z support...",
        "dependency_install": "py7zr was not found. Installing it automatically with pip...",
        "dependency_ready": "py7zr is ready to extract .7z files.",
        "dependency_failed": "Could not install py7zr automatically:\n{error}\nRun manually: python -m pip install -r requirements.txt",
        "downloading": "Downloading {name} {version}...",
        "downloaded": "{name} downloaded: {path}",
        "download_failed": "Failed to download {name}: {error}",
        "download_warning": "{name}: {warning}",
        "unresolved": "{name} will remain in the plan without a resolved version.",
        "generate_package": "Generate the device-ready package now?",
        "package_title": "PS2 package",
        "package_help": "Organizing Memory Card/VMC, APPS, PS2BBL.INI, OSDMENU.CNF, title.cfg and copy instructions.",
        "package_done": "Package generated at: {path}",
        "package_failed": "Failed to generate package: {error}",
        "package_warning": "{warning}",
        "done_title": "Finished",
        "done": "Read the generated README-COPY-HERE.txt files before copying anything to the PS2.",
    },
    "es": {
        "title": "Ps2Installer",
        "intro": "Este asistente prepara PS2BBL, OSDMenu y los homebrews seleccionados en carpetas listas para copiar. Nada se escribe directamente en la PS2; todo queda dentro de la carpeta de salida elegida.",
        "output_title": "Carpeta de salida",
        "output_help": "Aquí se guardarán el plan, las descargas temporales y el paquete final para PS2.",
        "output_location": "¿Dónde deben guardarse las descargas y el paquete final?",
        "output_project": "Dentro del proyecto (./output)",
        "output_custom": "Elegir otra carpeta",
        "custom_output": "Introduce la ruta de la carpeta de salida",
        "output_error": "No se pudo usar esa carpeta: {error}",
        "output_selected": "Salida seleccionada: {path}",
        "hardware_title": "Memory Card y almacenamiento",
        "hardware_help": "PS2BBL y la configuración permanecen en la Memory Card/VMC. OSDMenu y las aplicaciones grandes quedan en el almacenamiento seleccionado abajo.",
        "memory_card": "¿Qué Memory Card utilizas?",
        "storage": "¿Dónde deben guardarse OSDMenu y los homebrews?",
        "homebrew": "Selección de homebrews",
        "homebrew_help": "Los componentes obligatorios se incluyen automáticamente. Para los opcionales elige Y/N y luego Stable/Beta/Development cuando haya varios canales.",
        "install": "¿Instalar {name}?",
        "required": "{name}: obligatorio para este modo",
        "resolving": "Consultando versiones actuales en GitHub...",
        "resolve_failed": "No se pudo consultar {name}: {error}",
        "available": "Versiones disponibles:",
        "choose_channel": "Elige un canal para {name}",
        "saved": "Plan guardado en: {path}",
        "summary": "Revisión",
        "summary_help": "Revisa las opciones antes de descargar. Estas son exactamente las versiones que se usarán en el paquete.",
        "card": "Memory Card",
        "selected_storage": "Almacenamiento",
        "selected_apps": "Homebrews seleccionados",
        "none": "ninguna aplicación opcional",
        "invalid": "Opción inválida. Inténtalo de nuevo.",
        "download": "¿Descargar ahora los archivos seleccionados?",
        "downloads_title": "Descargas",
        "downloads_help": "Los releases seleccionados se descargarán y extraerán. Las dependencias necesarias se verifican automáticamente antes de comenzar.",
        "dependency_check": "Comprobando soporte para archivos .7z...",
        "dependency_install": "No se encontró py7zr. Instalándolo automáticamente con pip...",
        "dependency_ready": "py7zr está listo para extraer archivos .7z.",
        "dependency_failed": "No se pudo instalar py7zr automáticamente:\n{error}\nEjecuta manualmente: python -m pip install -r requirements.txt",
        "downloading": "Descargando {name} {version}...",
        "downloaded": "{name} descargado: {path}",
        "download_failed": "Error al descargar {name}: {error}",
        "download_warning": "{name}: {warning}",
        "unresolved": "{name} permanecerá en el plan sin versión resuelta.",
        "generate_package": "¿Generar ahora el paquete listo para los dispositivos?",
        "package_title": "Paquete PS2",
        "package_help": "Organizando Memory Card/VMC, APPS, PS2BBL.INI, OSDMENU.CNF, title.cfg e instrucciones de copia.",
        "package_done": "Paquete generado en: {path}",
        "package_failed": "Error al generar el paquete: {error}",
        "package_warning": "{warning}",
        "done_title": "Completado",
        "done": "Lee los README-COPY-HERE.txt generados antes de copiar archivos a la PS2.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a PS2 homebrew installation package.")
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
    parser.add_argument(
        "--no-package",
        action="store_true",
        help="Do not generate the final Memory Card/storage package after downloads.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Use PATH as the output folder and skip the interactive output-folder question.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors.",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear the terminal between wizard stages.",
    )
    return parser.parse_args()


def numbered_choice(
    title: str,
    options: list[tuple[str, str]],
    invalid_text: str,
    ui: ConsoleUI,
    default_id: str | None = None,
) -> str:
    while True:
        print(f"\n{ui.paint(title, ui.BOLD)}")
        for index, (option_id, label) in enumerate(options, start=1):
            ui.option(index, label, default=option_id == default_id)
        raw = input(ui.paint("> ", ui.CYAN, ui.BOLD)).strip()
        if not raw and default_id is not None:
            return default_id
        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < len(options):
                return options[index][0]
        ui.warning(invalid_text)


def yes_no(prompt: str, ui: ConsoleUI, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(
            f"{prompt} {ui.paint(suffix, ui.CYAN, ui.BOLD)}: "
        ).strip().lower()
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


def choose_language(ui: ConsoleUI) -> str:
    ui.clear()
    ui.banner()
    print()
    print(ui.paint("Choose language / Escolha o idioma / Elige el idioma", ui.BOLD))
    for index, (_, label) in enumerate(LANGUAGES, start=1):
        ui.option(index, label)
    while True:
        raw = input(ui.paint("> ", ui.CYAN, ui.BOLD)).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(LANGUAGES):
            return LANGUAGES[int(raw) - 1][0]
        ui.warning("Invalid / Inválido")


def _prepare_output_path(raw_path: str | Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(str(raw_path).strip()))
    if not expanded:
        raise ValueError("empty path")
    path = Path(expanded)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path} is not a directory")
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".ps2installer-write-test"
    try:
        probe.write_text("ok\n", encoding="utf-8")
    finally:
        probe.unlink(missing_ok=True)
    return path


def choose_output_root(args: argparse.Namespace, text: dict[str, str], ui: ConsoleUI) -> Path:
    if args.output:
        try:
            return _prepare_output_path(args.output)
        except (OSError, ValueError) as exc:
            raise SystemExit(text["output_error"].format(error=exc)) from exc

    choice = numbered_choice(
        text["output_location"],
        [
            ("project", text["output_project"]),
            ("custom", text["output_custom"]),
        ],
        text["invalid"],
        ui,
        default_id="project",
    )
    if choice == "project":
        return _prepare_output_path(DEFAULT_OUTPUT_DIR)

    while True:
        raw = input(f"{text['custom_output']}: ").strip()
        try:
            return _prepare_output_path(raw)
        except (OSError, ValueError) as exc:
            ui.error(text["output_error"].format(error=exc))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def print_release_options(options: list[ResolvedRelease], ui: ConsoleUI) -> None:
    for option in options:
        if option.channel == "development":
            status = "development"
        else:
            status = "prerelease" if option.prerelease else "stable"
        ui.release(option.channel_label, option.version, status)


def select_release_option(
    app: dict[str, Any],
    options: list[ResolvedRelease],
    text: dict[str, str],
    ui: ConsoleUI,
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
        ui,
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


def write_plan(plan: dict[str, Any], plan_path: Path) -> None:
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    with plan_path.open("w", encoding="utf-8") as handle:
        json.dump(plan, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def needs_7z(selected: list[tuple[dict[str, Any], ResolvedRelease | None]]) -> bool:
    return any(
        resolved is not None and resolved.archive_type == "7z"
        for _, resolved in selected
    )


def prepare_7z_dependency(text: dict[str, str], ui: ConsoleUI) -> bool:
    ui.info(text["dependency_check"])
    try:
        installed = ensure_py7zr(REQUIREMENTS_PATH)
    except DependencyError as exc:
        ui.error(text["dependency_failed"].format(error=exc))
        return False

    if installed:
        ui.success(text["dependency_install"])
    ui.success(text["dependency_ready"])
    return True


def main() -> None:
    args = parse_args()
    ui = ConsoleUI(color=False if args.no_color else None, clear=not args.no_clear)
    language = choose_language(ui)
    t = TEXT[language]

    ui.clear()
    ui.banner()
    ui.section(t["title"], t["intro"])
    ui.section(t["output_title"], t["output_help"])
    output_root = choose_output_root(args, t, ui)
    plan_path = output_root / "selection.json"
    download_root = output_root / "downloads"
    ui.success(t["output_selected"].format(path=ui.path(display_path(output_root))))

    ui.clear()
    ui.banner()
    ui.section(t["hardware_title"], t["hardware_help"])
    card_id = numbered_choice(
        t["memory_card"],
        [(item["id"], item["name"]) for item in MEMORY_CARDS],
        t["invalid"],
        ui,
    )
    storage_id = numbered_choice(
        t["storage"],
        [(item["id"], item["name"]) for item in STORAGES],
        t["invalid"],
        ui,
    )

    catalog = load_catalog()
    resolver = None if args.offline else GitHubReleaseResolver()
    selected: list[tuple[dict[str, Any], ResolvedRelease | None]] = []

    ui.clear()
    ui.banner()
    ui.section(t["homebrew"], t["homebrew_help"])
    if resolver:
        ui.info(t["resolving"])

    for app in catalog["homebrews"]:
        options: list[ResolvedRelease] = []
        resolution_error: str | None = None
        if resolver:
            try:
                options = resolver.resolve_options(app)
            except GitHubError as exc:
                resolution_error = str(exc)

        print()
        print(ui.paint(app["name"], ui.BOLD, ui.CYAN))
        if options:
            print(t["available"])
            print_release_options(options, ui)
        elif resolution_error:
            ui.warning(t["resolve_failed"].format(name=app["name"], error=resolution_error))

        if app.get("required", False):
            ui.info(t["required"].format(name=app["name"]))
            chosen = select_release_option(app, options, t, ui)
            if chosen is None:
                ui.warning(t["unresolved"].format(name=app["name"]))
            selected.append((app, chosen))
            continue

        if not yes_no(
            t["install"].format(name=app["name"]),
            ui,
            default=app.get("default", False),
        ):
            continue

        chosen = select_release_option(app, options, t, ui)
        if chosen is None:
            ui.warning(t["unresolved"].format(name=app["name"]))
        selected.append((app, chosen))

    card = get_by_id(MEMORY_CARDS, card_id)
    storage = get_by_id(STORAGES, storage_id)
    plan: dict[str, Any] = {
        "schema_version": 3,
        "language": language,
        "output_root": str(output_root),
        "memory_card": card,
        "storage": storage,
        "homebrews": [app_plan_entry(app, resolved) for app, resolved in selected],
        "downloads": {},
        "package": None,
    }
    write_plan(plan, plan_path)

    optional_names = [
        f"{app['name']} {resolved.version if resolved else '(unresolved)'}"
        for app, resolved in selected
        if not app.get("required", False)
    ]

    ui.clear()
    ui.banner()
    ui.section(t["summary"], t["summary_help"])
    print(f"{ui.paint(t['card'] + ':', ui.BOLD)} {card['name']}")
    print(f"{ui.paint(t['selected_storage'] + ':', ui.BOLD)} {storage['name']}")
    print(
        f"{ui.paint(t['selected_apps'] + ':', ui.BOLD)} "
        f"{', '.join(optional_names) if optional_names else t['none']}"
    )
    ui.info(t["saved"].format(path=ui.path(display_path(plan_path))))

    should_download = False
    if not args.no_download and not args.offline:
        resolved_count = sum(1 for _, resolved in selected if resolved is not None)
        if resolved_count:
            should_download = yes_no(t["download"], ui, default=True)

    if should_download:
        ui.clear()
        ui.banner()
        ui.section(t["downloads_title"], t["downloads_help"])

        if needs_7z(selected) and not prepare_7z_dependency(t, ui):
            write_plan(plan, plan_path)
            return

        for app, resolved in selected:
            if resolved is None:
                continue
            ui.info(t["downloading"].format(name=app["name"], version=resolved.version))
            try:
                result = download_release(
                    resolved,
                    download_root,
                    elf_names=list(app.get("elf_names", [])),
                )
                plan["downloads"][app["id"]] = result
                ui.success(
                    t["downloaded"].format(
                        name=app["name"], path=ui.path(result["asset_path"])
                    )
                )
                if result.get("warning"):
                    ui.warning(
                        t["download_warning"].format(
                            name=app["name"], warning=result["warning"]
                        )
                    )
            except DownloadError as exc:
                plan["downloads"][app["id"]] = {"error": str(exc)}
                ui.error(t["download_failed"].format(name=app["name"], error=exc))
            write_plan(plan, plan_path)

    if should_download and not args.no_package:
        if yes_no(t["generate_package"], ui, default=True):
            ui.clear()
            ui.banner()
            ui.section(t["package_title"], t["package_help"])
            try:
                manifest = build_package(plan, output_root)
                plan["package"] = manifest
                ui.success(
                    t["package_done"].format(
                        path=ui.path(str(manifest["package_root"]))
                    )
                )
                for warning in manifest.get("warnings", []):
                    ui.warning(t["package_warning"].format(warning=warning))
            except PackageError as exc:
                plan["package"] = {"error": str(exc)}
                ui.error(t["package_failed"].format(error=exc))
            write_plan(plan, plan_path)

    print()
    ui.section(t["done_title"])
    ui.success(t["done"])


if __name__ == "__main__":
    main()
