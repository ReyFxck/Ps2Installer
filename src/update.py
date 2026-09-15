from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


class UpdateError(RuntimeError):
    """Raised when an existing installation cannot be scanned or updated safely."""


def _parse_title_cfg(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip().lower()] = value.strip()
    return result


def scan_existing_apps(storage_root: Path) -> list[dict[str, Any]]:
    apps_root = storage_root / "APPS"
    if not apps_root.is_dir():
        return []

    found: list[dict[str, Any]] = []
    for folder in sorted((p for p in apps_root.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
        cfg = _parse_title_cfg(folder / "title.cfg")
        boot = cfg.get("boot")
        elf: Path | None = None
        if boot:
            candidate = (folder / boot).resolve()
            folder_root = folder.resolve()
            if (
                candidate.is_file()
                and candidate.suffix.lower() == ".elf"
                and (candidate == folder_root or folder_root in candidate.parents)
            ):
                elf = candidate
        if elf is None:
            candidates = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".elf")
            elf = candidates[0] if candidates else None
        if elf is None:
            continue
        found.append({
            "id": f"existing:{folder.name}",
            "name": cfg.get("title") or folder.name,
            "folder": folder.name,
            "relative_path": elf.relative_to(storage_root).as_posix(),
            "elf": elf.name,
            "menu_targets": {
                "osdmenu": True,
                "opl": bool((folder / "title.cfg").is_file()),
            },
            "existing": True,
        })
    return found


def _backup_path(source: Path, target_root: Path, relative: Path) -> None:
    if not source.exists():
        return
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)


def _merge_memory_card(
    source_root: Path,
    target_root: Path,
    backup_root: Path,
    copy_configs: bool = True,
    copy_boot_elf: bool = True,
) -> list[str]:
    changed: list[str] = []
    relatives: list[Path] = []
    if copy_boot_elf:
        relatives.append(Path("BOOT/BOOT.ELF"))
    if copy_configs:
        relatives.extend([Path("SYS-CONF/PS2BBL.INI"), Path("SYS-CONF/OSDMENU.CNF")])
    for relative in relatives:
        source = source_root / relative
        if not source.is_file():
            continue
        destination = target_root / relative
        _backup_path(destination, backup_root / "memory_card", relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        changed.append(f"MC:{relative.as_posix()}")
    return changed


def _merge_storage(source_root: Path, target_root: Path, backup_root: Path) -> list[str]:
    changed: list[str] = []
    source_apps = source_root / "APPS"
    target_apps = target_root / "APPS"
    target_apps.mkdir(parents=True, exist_ok=True)
    if not source_apps.is_dir():
        return changed

    for app_dir in sorted((p for p in source_apps.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
        destination = target_apps / app_dir.name
        relative = Path("APPS") / app_dir.name
        _backup_path(destination, backup_root / "storage", relative)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(app_dir, destination)
        changed.append(f"STORAGE:{relative.as_posix()}")
    return changed


def apply_package_update(
    package_root: Path,
    memory_card_root: Path,
    storage_root: Path,
    remove_folders: list[str] | None = None,
    backup_parent: Path | None = None,
    copy_configs: bool = True,
    copy_boot_elf: bool = True,
) -> dict[str, Any]:
    mc_candidates = sorted(p for p in package_root.iterdir() if p.is_dir() and p.name.startswith("1_"))
    storage_candidates = sorted(p for p in package_root.iterdir() if p.is_dir() and p.name.startswith("2_"))
    if len(mc_candidates) != 1 or len(storage_candidates) != 1:
        raise UpdateError("Generated package must contain exactly one 1_* Memory Card folder and one 2_* storage folder")

    memory_card_root.mkdir(parents=True, exist_ok=True)
    storage_root.mkdir(parents=True, exist_ok=True)
    backup_parent = backup_parent or package_root.parent / "Ps2Installer_Backups"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = backup_parent / stamp
    backup_root.mkdir(parents=True, exist_ok=True)

    changed = _merge_memory_card(
        mc_candidates[0],
        memory_card_root,
        backup_root,
        copy_configs=copy_configs,
        copy_boot_elf=copy_boot_elf,
    )

    # Remove requested old apps first, then install selected payloads. If a user
    # removes and re-selects the same APPS folder, the new version wins.
    removed: list[str] = []
    for folder_name in remove_folders or []:
        if not folder_name or "/" in folder_name or "\\" in folder_name or folder_name in {".", ".."}:
            raise UpdateError(f"Unsafe APPS folder name: {folder_name!r}")
        target = storage_root / "APPS" / folder_name
        if not target.exists():
            continue
        relative = Path("APPS") / folder_name
        _backup_path(target, backup_root / "storage", relative)
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        removed.append(folder_name)

    changed.extend(_merge_storage(storage_candidates[0], storage_root, backup_root))

    return {
        "backup_root": str(backup_root),
        "changed": changed,
        "removed": removed,
        "memory_card_root": str(memory_card_root),
        "storage_root": str(storage_root),
    }
