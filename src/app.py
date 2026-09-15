from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .config import LANGUAGES, MEMORY_CARDS, STORAGES, TEXT
from .boot import boot_method_meta
from .compatibility import check_compatibility
from .dependencies import DependencyError, ensure_py7zr, find_native_7z, module_available, running_on_android
from .downloads import DownloadError, download_release
from .package import PackageError, build_package
from .recipes import recipe_for
from .report import write_installation_report
from .update import UpdateError, apply_package_update, scan_existing_apps
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
    parser.add_argument("--offline", action="store_true", help="Skip network GitHub release resolution.")
    parser.add_argument("--no-package", action="store_true", help="Do not build the final PS2 package.")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear the terminal screen.")
    parser.add_argument("--keep-downloads", action="store_true", help="Keep downloaded/extracted temporary files for debugging.")
    parser.add_argument("--output", metavar="PATH", help="Use PATH as the output folder.")
    parser.add_argument("--update-memory-card-root", metavar="PATH", help="Update an existing Memory Card/VMC root.")
    parser.add_argument("--update-storage-root", metavar="PATH", help="Update an existing APPS storage root.")
    parser.add_argument("--local-elf", action="append", default=[], metavar="PATH", help="Import a local ELF (repeatable).")
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


def parse_multi_selection(raw: str, option_count: int, default_indices: list[int]) -> tuple[list[int], bool]:
    """Parse 1-based comma/space selections. Returns zero-based indexes + P shortcut flag."""
    value = raw.strip()
    if not value:
        return sorted(set(default_indices)), False

    tokens = [token for token in re.split(r"[,\s]+", value) if token]
    jump = any(token.upper() == "P" for token in tokens)
    choose_all = any(token.upper() == "A" for token in tokens)
    numeric_tokens = [token for token in tokens if token.upper() not in {"P", "A"}]

    if choose_all:
        selected = list(range(option_count))
    elif not numeric_tokens and jump:
        selected = sorted(set(default_indices))
    else:
        selected = []
        for token in numeric_tokens:
            if not token.isdigit():
                raise ValueError(token)
            index = int(token)
            if not 1 <= index <= option_count:
                raise ValueError(token)
            zero_based = index - 1
            if zero_based not in selected:
                selected.append(zero_based)
    return selected, jump


def parse_app_selection(raw: str, option_count: int, default_indices: list[int]) -> tuple[list[int], bool, bool]:
    """Extended selector: numeric/A/P plus L for local ELF import."""
    tokens = [token for token in re.split(r"[,\s]+", raw.strip()) if token]
    local = any(token.upper() == "L" for token in tokens)
    filtered = [token for token in tokens if token.upper() != "L"]
    selected, jump = parse_multi_selection(" ".join(filtered), option_count, default_indices)
    return selected, jump, local


def choose_optional_apps(apps: list[dict[str, Any]], text: dict[str, str]) -> tuple[list[dict[str, Any]], bool, bool]:
    default_indices = [index for index, app in enumerate(apps) if app.get("default", False)]
    print()
    current_category: str | None = None
    for index, app in enumerate(apps, start=1):
        category = str(app.get("category") or "Other")
        if category != current_category:
            current_category = category
            print(f"  -- {category} --")
        source_type = str(app.get("source_type") or "github")
        markers: list[str] = []
        if app.get("default", False):
            markers.append(text["default_marker"])
        if source_type == "manual":
            markers.append(text["manual_marker"])
        marker_text = f" [{' / '.join(markers)}]" if markers else ""
        description = str(app.get("description") or "").strip()
        suffix = f" — {description}" if description else ""
        print(f"  [{index}] {app['name']}{marker_text}{suffix}")
        if source_type == "manual":
            source_url = str(app.get("source_url") or "").strip()
            if source_url:
                print(f"      {text['source_label']}: {source_url}")

    info(text["multi_help"])
    while True:
        raw = input(f"\n{text['multi_prompt']}\n> ")
        try:
            indices, jump, local = parse_app_selection(raw, len(apps), default_indices)
        except ValueError:
            warn(text["invalid"])
            continue
        return [apps[index] for index in indices], jump, local


def _safe_local_folder(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._+-]+", "-", name.strip()).strip("-._")
    return cleaned or "LocalApp"


def _existing_directory(raw_path: str | Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(str(raw_path).strip()))
    if not expanded:
        raise ValueError("empty path")
    path = Path(expanded)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if not path.is_dir():
        raise ValueError(f"{path} is not an existing directory")
    return path


def _prompt_existing_directory(prompt: str) -> Path:
    while True:
        raw = input(f"{prompt}: ").strip()
        try:
            return _existing_directory(raw)
        except (OSError, ValueError) as exc:
            warn(str(exc))


def _local_app_from_path(path: Path, text: dict[str, str], ask_name: bool = True) -> dict[str, Any]:
    if not path.is_file() or path.suffix.lower() != ".elf":
        raise ValueError(text["local_invalid"].format(path=path))
    default_name = path.stem
    name = default_name
    if ask_name:
        raw_name = input(f"{text['local_name']} [{default_name}]: ").strip()
        if raw_name:
            name = raw_name
    folder = _safe_local_folder(name)
    return {
        "id": f"local-{folder.lower()}",
        "name": name,
        "category": "Local",
        "description": "User-supplied local ELF",
        "source_type": "local",
        "source_url": None,
        "local_path": str(path.resolve()),
        "required": False,
        "default": False,
        "folder": folder,
        "elf_names": [path.name],
        "menu_targets": {"osdmenu": True, "opl": True},
        "install": {"mode": "single-elf"},
        "recipe": {"id": "local-elf", "mode": "single-elf", "notes": ["User-supplied local ELF."]},
    }


def collect_local_apps(text: dict[str, str], initial_paths: list[str] | None = None, interactive: bool = False) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in initial_paths or []:
        path = Path(os.path.expanduser(os.path.expandvars(raw))).resolve()
        result.append(_local_app_from_path(path, text, ask_name=False))
    if not interactive:
        return result
    info(text["local_help"])
    while True:
        raw = input(f"{text['local_path']}: ").strip()
        if not raw:
            break
        try:
            app = _local_app_from_path(Path(os.path.expanduser(os.path.expandvars(raw))).resolve(), text)
        except ValueError as exc:
            warn(str(exc))
            continue
        # Avoid duplicate IDs by suffixing the folder when needed.
        used = {item["id"] for item in result}
        base_id = app["id"]
        counter = 2
        while app["id"] in used:
            app["id"] = f"{base_id}-{counter}"
            app["folder"] = f"{app['folder']}-{counter}"
            counter += 1
        result.append(app)
        ok(text["local_added"].format(name=app["name"], path=app["local_path"]))
        if not yes_no(text["local_more"], default=False):
            break
    return result


def choose_boot_method(text: dict[str, str]) -> dict[str, Any]:
    info(text["boot_help"])
    method_id = numbered_choice(
        text["boot_method"],
        [
            ("existing", text["boot_existing"]),
            ("opentuna", text["boot_opentuna"]),
            ("dev1", text["boot_dev1"]),
            ("system-update", text["boot_system_update"]),
            ("hdd-kelf", text["boot_hdd_kelf"]),
        ],
        text["invalid"],
        default_id="existing",
    )
    meta = boot_method_meta(method_id)
    meta["name"] = dict([
        ("existing", text["boot_existing"]),
        ("opentuna", text["boot_opentuna"]),
        ("dev1", text["boot_dev1"]),
        ("system-update", text["boot_system_update"]),
        ("hdd-kelf", text["boot_hdd_kelf"]),
    ])[method_id]
    return meta


def choose_r1_binding(storage_id: str, text: dict[str, str]) -> bool:
    if storage_id == "hdd-exfat":
        info(text["r1_exfat_unavailable"])
        return False
    return yes_no(text["r1_osdmenu"], default=True)


def choose_existing_removals(existing_apps: list[dict[str, Any]], text: dict[str, str]) -> list[str]:
    if not existing_apps or not yes_no(text["remove_existing_prompt"], default=False):
        return []
    print()
    for index, app in enumerate(existing_apps, start=1):
        print(f"  [{index}] {app['name']}  (APPS/{app['folder']})")
    info(text["remove_help"])
    while True:
        raw = input("\n> ").strip()
        if not raw:
            return []
        try:
            indices, _jump = parse_multi_selection(raw, len(existing_apps), [])
        except ValueError:
            warn(text["invalid"])
            continue
        return [str(existing_apps[index]["folder"]) for index in indices]


def _show_compatibility(findings: list[dict[str, str]], text: dict[str, str]) -> None:
    if not findings:
        return
    print(f"\n{text['compatibility_header']}")
    for item in findings:
        severity = str(item.get("severity") or "info")
        message = str(item.get("message") or "")
        if severity == "warning":
            warn(message)
        elif severity == "error":
            error(message)
        else:
            info(message)


def _valid_apa_partition(name: str) -> bool:
    return bool(name) and len(name) <= 32 and not any(ch in name for ch in ":/\\\r\n")


def choose_hdd_apa_partition(text: dict[str, str]) -> str:
    choice = numbered_choice(
        text["hdd_apa_partition"],
        [
            ("+OPL", text["hdd_apa_opl"]),
            ("__common", text["hdd_apa_common"]),
            ("custom", text["hdd_apa_custom"]),
        ],
        text["invalid"],
        default_id="+OPL",
    )
    if choice != "custom":
        return choice

    while True:
        value = input(f"{text['hdd_apa_custom_prompt']}: ").strip()
        if _valid_apa_partition(value):
            return value
        warn(text["hdd_apa_invalid"])


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
        if option.channel in {"development", "nightly"}:
            status = option.channel
        else:
            status = "prerelease" if option.prerelease else "stable"
        info(f"{option.channel_label}: {option.version} [{status}]")


def _recommended_release(app: dict[str, Any], options: list[ResolvedRelease]) -> ResolvedRelease | None:
    if not options:
        return None
    recommended = str(app.get("recommended_channel") or "")
    for option in options:
        if option.channel == recommended:
            return option
    return options[0]


def select_release_option(
    app: dict[str, Any],
    options: list[ResolvedRelease],
    text: dict[str, str],
    automatic: bool = False,
) -> ResolvedRelease | None:
    if not options:
        return None
    if automatic or len(options) == 1:
        return _recommended_release(app, options)
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
        "category": app.get("category"),
        "repository": app.get("repository"),
        "source_type": app.get("source_type", "github"),
        "source_url": app.get("source_url"),
        "manual_note": app.get("manual_note"),
        "local_path": app.get("local_path"),
        "folder": app.get("folder"),
        "elf_names": app.get("elf_names", []),
        "menu_targets": app.get("menu_targets", {}),
        "install": app.get("install", {"mode": "single-elf"}),
        "recipe": recipe_for(app),
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
        if app.get("id")
        and app.get("id") != "ps2bbl"
        and str(app.get("source_type") or "github") != "manual"
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


def _resolve_app(
    resolver: GitHubReleaseResolver,
    app: dict[str, Any],
    offline: bool,
) -> tuple[list[ResolvedRelease], str | None]:
    source_type = str(app.get("source_type") or "github")
    if source_type in {"manual", "local"}:
        return [], None
    if offline and source_type == "github":
        return [], None
    try:
        return resolver.resolve_options(app), None
    except GitHubError as exc:
        return [], str(exc)


def _sanitize_downloads(plan: dict[str, Any]) -> None:
    clean: dict[str, Any] = {}
    for app_id, result in (plan.get("downloads") or {}).items():
        if not isinstance(result, dict):
            continue
        clean[app_id] = {
            "downloaded": not bool(result.get("error")),
            "extracted": bool(result.get("extracted")),
            "warning": result.get("warning"),
            "error": result.get("error"),
        }
    plan["downloads"] = clean
    plan["downloads_temporary"] = True


def main() -> None:
    args = parse_args()
    language = choose_language(args.no_clear)
    t = TEXT[language]
    info(t["intro"])

    section(1, TOTAL_STEPS, t["step_output"])
    info(t["output_help"])
    output_root = choose_output_root(args, t)
    plan_path = output_root / "selection.json"
    ok(t["output_selected"].format(path=display_path(output_root)))
    workflow_mode = "update" if (args.update_memory_card_root or args.update_storage_root) else numbered_choice(
        t["workflow_mode"],
        [("new", t["workflow_new"]), ("update", t["workflow_update"])],
        t["invalid"],
        default_id="new",
    )

    section(2, TOTAL_STEPS, t["step_hardware"])
    info(t["hardware_help"])
    card_id = numbered_choice(t["memory_card"], [(i["id"], i["name"]) for i in MEMORY_CARDS], t["invalid"])
    storage_id = numbered_choice(t["storage"], [(i["id"], i["name"]) for i in STORAGES], t["invalid"])
    card = dict(get_by_id(MEMORY_CARDS, card_id))
    storage = dict(get_by_id(STORAGES, storage_id))
    if storage_id == "hdd-apa":
        storage["apa_partition"] = choose_hdd_apa_partition(t)
        ok(t["hdd_apa_selected"].format(partition=storage["apa_partition"]))
    elif storage_id == "hdd-exfat":
        warn(t["hdd_exfat_notice"])

    existing_apps: list[dict[str, Any]] = []
    workflow: dict[str, Any] = {"mode": workflow_mode, "rebuild_menus": True, "remove_folders": []}
    if workflow_mode == "update":
        info(t["update_paths_help"])
        try:
            mc_target = _existing_directory(args.update_memory_card_root) if args.update_memory_card_root else _prompt_existing_directory(t["update_mc_path"])
            storage_target = _existing_directory(args.update_storage_root) if args.update_storage_root else _prompt_existing_directory(t["update_storage_path"])
        except (OSError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
        existing_apps = scan_existing_apps(storage_target)
        info(t["existing_apps_found"].format(count=len(existing_apps)))
        remove_folders = choose_existing_removals(existing_apps, t)
        rebuild_menus = True if remove_folders else yes_no(t["rebuild_menus"], default=True)
        workflow.update({
            "memory_card_root": str(mc_target),
            "storage_root": str(storage_target),
            "remove_folders": remove_folders,
            "rebuild_menus": rebuild_menus,
        })

    boot = choose_boot_method(t)
    boot["r1_osdmenu"] = choose_r1_binding(storage_id, t)
    if workflow_mode == "update":
        boot_default = str(boot.get("id") or "") in {"opentuna", "dev1"}
        copy_boot_elf = yes_no(t["update_boot_elf"], default=boot_default)
        workflow["copy_boot_elf"] = copy_boot_elf

    section(3, TOTAL_STEPS, t["step_apps"])
    info(t["apps_help"])
    catalog = load_catalog()
    all_apps = list(catalog.get("homebrews") or [])
    required_apps = [app for app in all_apps if app.get("required", False)]
    optional_apps = [app for app in all_apps if not app.get("required", False)]
    chosen_optional, jump_to_downloads, local_requested = choose_optional_apps(optional_apps, t)
    local_apps = collect_local_apps(t, list(args.local_elf), interactive=local_requested)
    chosen_apps = required_apps + chosen_optional + local_apps

    resolver = GitHubReleaseResolver()
    selected: list[tuple[dict[str, Any], ResolvedRelease | None]] = []
    if not args.offline:
        info(t["resolving"])

    for app in chosen_apps:
        source_type = str(app.get("source_type") or "github")
        if source_type == "manual":
            source_url = str(app.get("source_url") or "-")
            info(t["manual_selected"].format(name=app["name"], url=source_url))
            selected.append((app, None))
            continue
        if source_type == "local":
            ok(t["local_selected"].format(name=app["name"]))
            selected.append((app, None))
            continue

        options, resolution_error = _resolve_app(resolver, app, args.offline)
        print(f"\n{app['name']}")
        if options:
            print(f"  {t['available']}:")
            print_release_options(options)
        elif resolution_error:
            warn(t["resolve_failed"].format(name=app["name"], error=resolution_error))

        if app.get("required", False):
            info(t["required"])
        chosen = select_release_option(app, options, t, automatic=jump_to_downloads)
        if chosen is None:
            warn(t["unresolved"])
        selected.append((app, chosen))

    plan: dict[str, Any] = {
        "schema_version": 9,
        "language": language,
        "output_root": str(output_root),
        "memory_card": card,
        "storage": storage,
        "boot": boot,
        "workflow": workflow,
        "existing_apps": existing_apps,
        "homebrews": [app_plan_entry(app, resolved) for app, resolved in selected],
        "downloads": {},
        "package": None,
    }
    for app, _resolved in selected:
        if str(app.get("source_type") or "github") != "local":
            continue
        local_path = Path(str(app.get("local_path") or ""))
        plan["downloads"][app["id"]] = {
            "asset_path": str(local_path),
            "extracted_path": None,
            "extracted": True,
            "elf_candidates": [str(local_path)],
            "warning": None,
            "local": True,
        }
    findings = check_compatibility(plan)
    plan["compatibility"] = findings
    write_plan(plan, plan_path)

    if not jump_to_downloads:
        section(4, TOTAL_STEPS, t["step_summary"])
        info(f"{t['card']}: {card['name']}")
        info(f"{t['selected_storage']}: {storage['name']}")
        info(t["boot_selected"].format(method=boot.get("name", boot.get("id"))))
        info(t["workflow_selected"].format(mode=t["workflow_update"] if workflow_mode == "update" else t["workflow_new"]))
        if storage.get("apa_partition"):
            info(t["hdd_apa_selected"].format(partition=storage["apa_partition"]))
        print(f"  {t['selected_apps']}:")
        optional_count = 0
        for app, resolved in selected:
            if app.get("required", False):
                continue
            optional_count += 1
            source_type = str(app.get("source_type") or "github")
            if source_type == "manual":
                source_url = str(app.get("source_url") or "-")
                info(f"{app['name']} [{t['manual_marker']}] — {t['source_label']}: {source_url}")
            elif source_type == "local":
                ok(f"{app['name']} [{t['local_marker']}]")
            else:
                version = resolved.version if resolved else "?"
                ok(f"{app['name']} {version}")
        if optional_count == 0:
            info(t["none"])
        info(t["saved"].format(path=display_path(plan_path)))
    else:
        ok(t["jumping_downloads"])

    _show_compatibility(findings, t)

    resolved_selected = [
        (app, resolved) for app, resolved in selected
        if resolved is not None and str(app.get("source_type") or "github") != "local"
    ]
    local_selected = [app for app, _resolved in selected if str(app.get("source_type") or "github") == "local"]
    should_download = False
    if not args.no_download and (resolved_selected or local_selected):
        should_download = True if jump_to_downloads else yes_no(t["download"], default=True)

    dependency_ready = True
    download_root: Path | None = None
    cleanup_root: Path | None = None

    try:
        section(5, TOTAL_STEPS, t["step_download"])
        if should_download:
            if args.keep_downloads:
                download_root = output_root / "downloads"
                download_root.mkdir(parents=True, exist_ok=True)
                info(t["downloads_kept"].format(path=display_path(download_root)))
            else:
                download_root = Path(tempfile.mkdtemp(prefix=".ps2installer-downloads-", dir=str(output_root)))
                cleanup_root = download_root
                info(t["downloads_temporary"])

            needs_7z = any(resolved.archive_type == "7z" for _, resolved in resolved_selected)
            if needs_7z:
                info(t["dependency_check"])
                native_7z = find_native_7z()
                if native_7z:
                    ok(t["native_7z"].format(path=native_7z))
                elif module_available("py7zr"):
                    ok(t["dependency_ok"])
                elif running_on_android():
                    dependency_ready = False
                    warn(t["termux_7z_missing"])
                else:
                    info(t["dependency_install"])
                    try:
                        ensure_py7zr(REQUIREMENTS_PATH)
                    except DependencyError as exc:
                        dependency_ready = False
                        error(t["dependency_fail"].format(error=exc))
                        warn(t["dependency_manual"])
                    else:
                        ok(t["dependency_ok"])

            for app in local_selected:
                ok(t["local_prepared"].format(name=app["name"]))

            for app, resolved in resolved_selected:
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
            info(t["skipped"])

        section(6, TOTAL_STEPS, t["step_package"])
        if should_download and not args.no_package and yes_no(t["generate_package"], default=True):
            try:
                manifest = build_package(plan, output_root)
                ready, missing = package_status(manifest, plan)
                save_package_status(manifest, ready, missing)
                manifest["report"] = write_installation_report(
                    Path(str(manifest["package_root"])), plan, manifest, findings
                )
                (Path(str(manifest["package_root"])) / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                plan["package"] = manifest
                write_plan(plan, plan_path)
                package_path = display_path(Path(str(manifest["package_root"])))
                if ready:
                    success_box(t["package_ready"], [t["package_path"].format(path=package_path)])
                    for package_warning in manifest.get("warnings", []):
                        warn(t["package_warning"].format(warning=package_warning))
                    if workflow_mode == "update" and yes_no(t["apply_update"], default=True):
                        try:
                            update_result = apply_package_update(
                                Path(str(manifest["package_root"])),
                                Path(str(workflow["memory_card_root"])),
                                Path(str(workflow["storage_root"])),
                                remove_folders=list(workflow.get("remove_folders") or []),
                                backup_parent=output_root / "Ps2Installer_Backups",
                                copy_configs=bool(workflow.get("rebuild_menus", True)),
                                copy_boot_elf=bool(workflow.get("copy_boot_elf", False)),
                            )
                        except UpdateError as exc:
                            error(t["update_failed"].format(error=exc))
                        else:
                            manifest["update"] = update_result
                            manifest["report"] = write_installation_report(
                                Path(str(manifest["package_root"])), plan, manifest, findings, update_result
                            )
                            (Path(str(manifest["package_root"])) / "manifest.json").write_text(
                                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                            )
                            plan["package"] = manifest
                            write_plan(plan, plan_path)
                            ok(t["update_applied"].format(backup=update_result["backup_root"]))
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
            info(t["skipped"])
    finally:
        if cleanup_root is not None:
            shutil.rmtree(cleanup_root, ignore_errors=True)
            _sanitize_downloads(plan)
            # Runtime extraction paths are intentionally ephemeral; do not persist dead paths.
            if isinstance(plan.get("package"), dict):
                package_data = plan["package"]
                ps2bbl = package_data.get("ps2bbl")
                if isinstance(ps2bbl, dict):
                    ps2bbl.pop("source", None)
                package_root_value = package_data.get("package_root")
                if package_root_value:
                    manifest_path = Path(str(package_root_value)) / "manifest.json"
                    if manifest_path.is_file():
                        manifest_path.write_text(
                            json.dumps(package_data, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )
            write_plan(plan, plan_path)
            info(t["downloads_cleaned"])

    print()
    ok(t["done"])
