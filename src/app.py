from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .config import LANGUAGES, MEMORY_CARDS, STORAGES, TEXT
from .dependencies import DependencyError, ensure_py7zr, module_available
from .downloads import DownloadError, download_release
from .package import PackageError, build_package
from .releases import GitHubError, GitHubReleaseResolver, ResolvedRelease
from .ui import banner, clear_screen, error, info, ok, section, success_box, warn

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog" / "homebrews.json"
DEFAULT_OUTPUT_DIR = ROOT / "output"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
TOTAL_STEPS = 6

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a PS2 homebrew installation package.")
    parser.add_argument("--no-download", action="store_true", help="Resolve versions without downloading assets.")
    parser.add_argument("--offline", action="store_true", help="Skip GitHub release resolution.")
    parser.add_argument("--no-package", action="store_true", help="Do not build the final PS2 package.")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear the terminal screen.")
    parser.add_argument("--output", metavar="PATH", help="Use PATH as the output folder.")
    return parser.parse_args()


def numbered_choice(title: str, options: list[tuple[str, str]], invalid_text: str, default_id: str | None = None) -> str:
    while True:
        print(f"\n{title}")
        for index, (option_id, label) in enumerate(options, start=1):
            mark = "  < Enter" if option_id == default_id else ""
            print(f"  [{index}] {label}{mark}")
        raw = input("\n> ").strip()
        if not raw and default_id is not None:
            return default_id
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        warn(invalid_text)


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


def choose_language(no_clear: bool) -> str:
    if not no_clear:
        clear_screen()
    banner()
    print("Choose language / Escolha o idioma / Elige el idioma")
    for index, (_, label) in enumerate(LANGUAGES, start=1):
        print(f"  [{index}] {label}")
    while True:
        raw = input("\n> ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(LANGUAGES):
            language = LANGUAGES[int(raw) - 1][0]
            if not no_clear:
                clear_screen()
            banner()
            return language
        warn("Invalid / Inválido")


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


def choose_output_root(args: argparse.Namespace, text: dict[str, str]) -> Path:
    if args.output:
        try:
            return _prepare_output_path(args.output)
        except (OSError, ValueError) as exc:
            raise SystemExit(text["output_error"].format(error=exc)) from exc

    choice = numbered_choice(
        text["output_location"],
        [("project", text["output_project"]), ("custom", text["output_custom"])],
        text["invalid"],
        default_id="project",
    )
    if choice == "project":
        return _prepare_output_path(DEFAULT_OUTPUT_DIR)

    while True:
        raw = input(f"{text['custom_output']}: ").strip()
        try:
            return _prepare_output_path(raw)
        except (OSError, ValueError) as exc:
            warn(text["output_error"].format(error=exc))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def print_release_options(options: list[ResolvedRelease]) -> None:
    for option in options:
        if option.channel == "development":
            status = "development"
        else:
            status = "prerelease" if option.prerelease else "stable"
        info(f"{option.channel_label}: {option.version} [{status}]")


def select_release_option(app: dict[str, Any], options: list[ResolvedRelease], text: dict[str, str]) -> ResolvedRelease | None:
    if not options:
        return None
    if len(options) == 1:
        return options[0]
    recommended = app.get("recommended_channel")
    default_id = recommended if any(o.channel == recommended for o in options) else None
    selected_channel = numbered_choice(
        text["choose_channel"].format(name=app["name"]),
        [(o.channel, f"{o.channel_label}: {o.version}") for o in options],
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


def write_plan(plan: dict[str, Any], plan_path: Path) -> None:
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def package_status(manifest: dict[str, Any], plan: dict[str, Any]) -> tuple[bool, list[str]]:
    installed = set((manifest.get("installed_apps") or {}).keys())
    expected = {
        str(app.get("id")): str(app.get("name") or app.get("id"))
        for app in plan.get("homebrews", [])
        if app.get("id") and app.get("id") != "ps2bbl"
    }
    missing = [expected[app_id] for app_id in sorted(set(expected) - installed)]
    bootloader_ok = bool(manifest.get("ps2bbl"))
    ready = bootloader_ok and not missing
    if not bootloader_ok:
        missing.insert(0, "PS2BBL/BOOT.ELF")
    return ready, missing


def save_package_status(manifest: dict[str, Any], ready: bool, missing: list[str]) -> None:
    manifest["ready"] = ready
    manifest["missing"] = missing
    package_root = Path(str(manifest["package_root"]))
    (package_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    marker = package_root / "PACKAGE_INCOMPLETE.txt"
    if ready:
        marker.unlink(missing_ok=True)
    else:
        marker.write_text(
            "PACKAGE INCOMPLETE - DO NOT COPY TO THE PS2 YET.\n\nMissing:\n- "
            + "\n- ".join(missing)
            + "\n",
            encoding="utf-8",
        )


def main() -> None:
    args = parse_args()
    language = choose_language(args.no_clear)
    t = TEXT[language]
    info(t["intro"])

    section(1, TOTAL_STEPS, t["step_output"])
    info(t["output_help"])
    output_root = choose_output_root(args, t)
    plan_path = output_root / "selection.json"
    download_root = output_root / "downloads"
    ok(t["output_selected"].format(path=display_path(output_root)))

    section(2, TOTAL_STEPS, t["step_hardware"])
    info(t["hardware_help"])
    card_id = numbered_choice(t["memory_card"], [(i["id"], i["name"]) for i in MEMORY_CARDS], t["invalid"])
    storage_id = numbered_choice(t["storage"], [(i["id"], i["name"]) for i in STORAGES], t["invalid"])

    section(3, TOTAL_STEPS, t["step_apps"])
    info(t["apps_help"])
    catalog = load_catalog()
    resolver = None if args.offline else GitHubReleaseResolver()
    selected: list[tuple[dict[str, Any], ResolvedRelease | None]] = []
    if resolver:
        info(t["resolving"])

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
            print(f"  {t['available']}:")
            print_release_options(options)
        elif resolution_error:
            warn(t["resolve_failed"].format(name=app["name"], error=resolution_error))

        if app.get("required", False):
            info(t["required"])
            chosen = select_release_option(app, options, t)
            if chosen is None:
                warn(t["unresolved"])
            selected.append((app, chosen))
            continue

        if not yes_no(t["install"].format(name=app["name"]), default=app.get("default", False)):
            continue
        chosen = select_release_option(app, options, t)
        if chosen is None:
            warn(t["unresolved"])
        selected.append((app, chosen))

    card = get_by_id(MEMORY_CARDS, card_id)
    storage = get_by_id(STORAGES, storage_id)
    plan: dict[str, Any] = {
        "schema_version": 4,
        "language": language,
        "output_root": str(output_root),
        "memory_card": card,
        "storage": storage,
        "homebrews": [app_plan_entry(app, resolved) for app, resolved in selected],
        "downloads": {},
        "package": None,
    }
    write_plan(plan, plan_path)

    section(4, TOTAL_STEPS, t["step_summary"])
    info(f"{t['card']}: {card['name']}")
    info(f"{t['selected_storage']}: {storage['name']}")
    print(f"  {t['selected_apps']}:")
    optional_count = 0
    for app, resolved in selected:
        if app.get("required", False):
            continue
        optional_count += 1
        version = resolved.version if resolved else "?"
        ok(f"{app['name']} {version}")
    if optional_count == 0:
        info(t["none"])
    info(t["saved"].format(path=display_path(plan_path)))

    should_download = False
    if not args.no_download and not args.offline and any(resolved for _, resolved in selected):
        should_download = yes_no(t["download"], default=True)

    dependency_ready = True
    section(5, TOTAL_STEPS, t["step_download"])
    if should_download:
        needs_7z = any(resolved and resolved.archive_type == "7z" for _, resolved in selected)
        if needs_7z:
            info(t["dependency_check"])
            if not module_available("py7zr"):
                info(t["dependency_install"])
                try:
                    ensure_py7zr(REQUIREMENTS_PATH)
                except DependencyError as exc:
                    dependency_ready = False
                    error(t["dependency_fail"].format(error=exc))
                    warn(t["dependency_manual"])
                else:
                    dependency_ready = True
                    ok(t["dependency_ok"])
            else:
                ok(t["dependency_ok"])

        for app, resolved in selected:
            if resolved is None:
                continue
            info(t["downloading"].format(name=app["name"], version=resolved.version))
            try:
                result = download_release(resolved, download_root, elf_names=list(app.get("elf_names", [])))
                plan["downloads"][app["id"]] = result
                if result.get("warning"):
                    warn(t["download_warning"].format(name=app["name"], warning=result["warning"]))
                else:
                    ok(t["downloaded"].format(name=app["name"]))
            except DownloadError as exc:
                plan["downloads"][app["id"]] = {"error": str(exc)}
                error(t["download_failed"].format(name=app["name"], error=exc))
            write_plan(plan, plan_path)
    else:
        info("Skipped / Pulado / Omitido")

    section(6, TOTAL_STEPS, t["step_package"])
    if should_download and not args.no_package and yes_no(t["generate_package"], default=True):
        try:
            manifest = build_package(plan, output_root)
            ready, missing = package_status(manifest, plan)
            save_package_status(manifest, ready, missing)
            plan["package"] = manifest
            write_plan(plan, plan_path)
            package_path = display_path(Path(str(manifest["package_root"])))
            if ready:
                success_box(t["package_ready"], [t["package_path"].format(path=package_path)])
            else:
                error(t["package_incomplete"])
                warn(t["missing"].format(items=", ".join(missing)))
                info(t["package_path"].format(path=package_path))
                for package_warning in manifest.get("warnings", []):
                    warn(package_warning)
                if not dependency_ready:
                    warn(t["dependency_manual"])
        except PackageError as exc:
            plan["package"] = {"error": str(exc)}
            write_plan(plan, plan_path)
            error(t["package_failed"].format(error=exc))
    else:
        info("Skipped / Pulado / Omitido")

    print()
    ok(t["done"])

