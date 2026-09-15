from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .boot import write_boot_guide
from .compatibility import check_compatibility
from .recipes import install_mode_for, recipe_for, recipe_notes, write_recipe_guide
from .report import write_installation_report


class PackageError(RuntimeError):
    """Raised when the ready-to-copy package cannot be generated."""


MEMORY_CARD_FOLDERS = {
    "standard": "1_MEMORY_CARD",
    "sd2psx": "1_SD2PSX_VMC",
    "memcard-pro2": "1_MEMCARD_PRO2_VMC",
    "psxmemcard-gen2": "1_PSXMEMCARD_GEN2_VMC",
    "other-mmce": "1_MMCE_VMC",
}


STORAGE_LAYOUTS: dict[str, dict[str, Any]] = {
    "mmce": {
        "folder": "2_MMCE_STORAGE",
        "osd_prefix": "mmce?:",
        "ps2bbl_prefix": "mmce?:",
        "ps2bbl_variant": "PS2_MMCE",
        "target": "MMCE SD root",
    },
    "mx4sio": {
        "folder": "2_MX4SIO",
        "osd_prefix": "mx4sio:",
        "ps2bbl_prefix": "massX:",
        "ps2bbl_variant": "PS2_MX4SIO",
        "target": "MX4SIO SD root",
    },
    "usb": {
        "folder": "2_USB",
        "osd_prefix": "usb:",
        "ps2bbl_prefix": "mass:",
        "ps2bbl_variant": "PS2",
        "target": "USB root",
    },
    "hdd-exfat": {
        "folder": "2_HDD_EXFAT",
        "osd_prefix": "ata:",
        "ps2bbl_prefix": None,
        # PS2BBL itself still belongs on the MC. Use the normal PS2 build,
        # but do not invent an unverified ata:/ R1 binding.
        "ps2bbl_variant": "PS2",
        "target": "internal exFAT HDD root",
        "warning": (
            "Internal exFAT HDD: OSDMenu/OPL paths use ata:/, but R1 in PS2BBL is left "
            "unbound because ata:/ launch support has not been verified for the packaged official build."
        ),
    },
}


def _safe_partition_folder(partition: str) -> str:
    if partition == "+OPL":
        return "PLUS_OPL"
    cleaned = re.sub(r"[^A-Za-z0-9._+-]+", "_", partition).strip("_")
    return cleaned or "PFS"


def _storage_layout(storage: dict[str, Any]) -> dict[str, Any]:
    storage_id = str(storage.get("id") or "")
    if storage_id != "hdd-apa":
        if storage_id not in STORAGE_LAYOUTS:
            raise PackageError(f"Unsupported storage: {storage_id}")
        return dict(STORAGE_LAYOUTS[storage_id])

    partition = str(storage.get("apa_partition") or "+OPL").strip()
    if not partition or len(partition) > 32 or any(ch in partition for ch in ":/\\\r\n"):
        raise PackageError(f"Invalid APA/PFS partition name: {partition!r}")
    prefix = f"hdd0:{partition}:pfs:"
    return {
        "folder": f"2_HDD_APA_{_safe_partition_folder(partition)}",
        "osd_prefix": prefix,
        "ps2bbl_prefix": prefix,
        "ps2bbl_variant": "PS2_HDD",
        "target": f"{prefix}/ (PFS partition root)",
        "apa_partition": partition,
        "warning": (
            f"APA/PFS: partition {partition} must already exist before copying files. "
            "Ps2Installer does not create or resize APA partitions."
        ),
    }


def _device_path(prefix: str, relative_path: str) -> str:
    return f"{prefix}/{relative_path.lstrip('/')}"


def _literal_elf_names(app: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for value in app.get("elf_names", []) or []:
        value = str(value)
        if "*" not in value and "?" not in value and value.lower().endswith(".elf"):
            result.append(value)
    return result


def _pick_elf(app: dict[str, Any], download: dict[str, Any]) -> Path | None:
    candidates = [Path(str(p)) for p in (download.get("elf_candidates") or [])]
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        return None

    preferred = {name.lower() for name in _literal_elf_names(app)}
    for candidate in candidates:
        if candidate.name.lower() in preferred:
            return candidate
    return candidates[0]


def _destination_elf_name(app: dict[str, Any], source: Path) -> str:
    literal = _literal_elf_names(app)
    if literal:
        return literal[0]
    return source.name


def _display_name(app: dict[str, Any]) -> str:
    name = str(app.get("name") or app.get("id") or "App")
    resolved = app.get("resolved") or {}
    version = str(resolved.get("version") or "").strip()
    base = f"{name} {version}".strip()

    channel = str(resolved.get("channel") or "").lower()
    if channel == "development":
        return f"{base} [Development]"
    if channel == "nightly":
        return f"{base} [Nightly]"

    if bool(resolved.get("prerelease")):
        low = version.lower()
        if not any(token in low for token in ("beta", "alpha", "rc", "pre")):
            return f"{base} [Prerelease]"
    return base



def _effective_tree_root(root: Path) -> Path:
    """Strip harmless single wrapper directories from extracted archives."""
    current = root
    for _ in range(3):
        if not current.is_dir():
            break
        children = [child for child in current.iterdir() if child.name != "__MACOSX"]
        files = [child for child in children if child.is_file()]
        dirs = [child for child in children if child.is_dir()]
        if files or len(dirs) != 1:
            break
        current = dirs[0]
    return current


def _copy_tree_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)


def _find_installed_elf(app: dict[str, Any], destination: Path) -> Path | None:
    candidates = sorted(
        path for path in destination.rglob("*")
        if path.is_file() and path.suffix.lower() == ".elf"
    )
    preferred = {name.lower() for name in _literal_elf_names(app)}
    for candidate in candidates:
        if candidate.name.lower() in preferred:
            return candidate
    return candidates[0] if candidates else None


def _install_app_payload(
    app: dict[str, Any],
    download: dict[str, Any],
    destination: Path,
) -> tuple[Path | None, str]:
    mode = install_mode_for(app)
    source = _pick_elf(app, download)

    if mode == "single-elf":
        if source is None:
            return None, mode
        destination.mkdir(parents=True, exist_ok=True)
        elf_name = _destination_elf_name(app, source)
        installed = destination / elf_name
        shutil.copy2(source, installed)
        return installed, mode

    if mode == "elf-directory":
        if source is None:
            return None, mode
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source.parent, destination)
        installed = destination / source.name
        return installed if installed.is_file() else _find_installed_elf(app, destination), mode

    if mode in {"archive-tree", "collection"}:
        extracted = download.get("extracted_path")
        if not extracted:
            return None, mode
        root = Path(str(extracted))
        if not root.is_dir():
            return None, mode
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)
        _copy_tree_contents(_effective_tree_root(root), destination)
        return _find_installed_elf(app, destination), mode

    raise PackageError(f"Unsupported install mode for {app.get('name', app.get('id'))}: {mode}")


def _write_manual_sources(package_root: Path, plan: dict[str, Any]) -> list[dict[str, str]]:
    manual: list[dict[str, str]] = []
    for app in plan.get("homebrews", []) or []:
        if str(app.get("source_type") or "github") != "manual":
            continue
        note_parts = [str(app.get("manual_note") or "Manual download/setup required.")]
        note_parts.extend(recipe_notes(app))
        required_files = recipe_for(app).get("required_user_files") or []
        if required_files:
            note_parts.append("User-supplied files required: " + ", ".join(str(value) for value in required_files))
        manual.append({
            "name": str(app.get("name") or app.get("id") or "Homebrew"),
            "url": str(app.get("source_url") or ""),
            "note": " ".join(part for part in note_parts if part.strip()),
        })

    if not manual:
        return manual

    language = str(plan.get("language") or "en")
    intro = _localized(
        language,
        "Estas entradas foram selecionadas, mas não são baixadas automaticamente. Siga a fonte indicada e os requisitos de cada projeto.",
        "These entries were selected but are not downloaded automatically. Follow the listed source and each project's setup requirements.",
        "Estas entradas fueron seleccionadas, pero no se descargan automáticamente. Sigue la fuente indicada y los requisitos de cada proyecto.",
    )
    lines = ["Ps2Installer - Manual Sources", "", intro, ""]
    for item in manual:
        lines.extend([item["name"], f"Source: {item['url'] or '-'}", f"Note: {item['note']}", ""])
    (package_root / "MANUAL_SOURCES.txt").write_text("\n".join(lines), encoding="utf-8")
    return manual

def _find_ps2bbl_elf(download: dict[str, Any], variant: str) -> Path | None:
    extracted = download.get("extracted_path")
    if extracted:
        root = Path(str(extracted))
        if root.exists():
            exact = [
                p
                for p in root.rglob("COMPRESSED_PS2BBL.ELF")
                if p.is_file() and p.parent.name == variant
            ]
            if exact:
                return sorted(exact)[0]

    for value in download.get("elf_candidates") or []:
        path = Path(str(value))
        if path.is_file() and path.name == "COMPRESSED_PS2BBL.ELF" and path.parent.name == variant:
            return path
    return None


def _build_ps2bbl_ini(
    layout: dict[str, Any],
    installed_apps: dict[str, Any],
    *,
    enable_r1: bool = True,
) -> str:
    lines = [
        "# Generated by Ps2Installer",
        "SKIP_PS2LOGO = 0",
        "EJECT_TRAY = 1",
        "OSDHISTORY_READ = 1",
        "KEY_READ_WAIT_TIME = 4000",
        "LOGO_DISPLAY = 2",
        "",
        "# Normal boot returns to the PS2 Browser/OSDSYS.",
        "LK_AUTO_E1 = $OSDSYS",
    ]

    osdmenu = installed_apps.get("osdmenu")
    prefix = layout.get("ps2bbl_prefix")
    if not enable_r1:
        lines.extend(
            [
                "",
                "# R1 -> OSDMenu was disabled by the user.",
            ]
        )
    elif osdmenu and prefix:
        lines.extend(
            [
                "",
                "# Hold R1 while PS2BBL is starting to launch OSDMenu.",
                f"LK_R1_E1 = {_device_path(str(prefix), osdmenu['relative_path'])}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "# R1 is intentionally not generated for this storage mode.",
                "# See the package README/warnings before copying the package.",
            ]
        )
    return "\n".join(lines) + "\n"


def _build_osdmenu_cnf(layout: dict[str, Any], installed_apps: dict[str, Any]) -> str:
    lines = [
        "# Generated by Ps2Installer",
        "OSDSYS_video_mode = AUTO",
        "OSDSYS_Skip_Disc = 1",
        "OSDSYS_boot = clock",
        "OSDSYS_custom_menu = 1",
        "OSDSYS_scroll_menu = 1",
        "OSDSYS_num_displayed_items = 7",
        "",
        "name_OSDSYS_ITEM_1 = Launch Disc",
        "path1_OSDSYS_ITEM_1 = cdrom",
        "arg_OSDSYS_ITEM_1 = -nologo",
    ]

    index = 10
    for app_id, item in installed_apps.items():
        if (
            app_id == "osdmenu"
            or not item.get("relative_path")
            or not (item.get("menu_targets") or {}).get("osdmenu")
        ):
            continue
        lines.extend(
            [
                "",
                f"name_OSDSYS_ITEM_{index} = {item['display_name']}",
                f"path1_OSDSYS_ITEM_{index} = {_device_path(str(layout['osd_prefix']), item['relative_path'])}",
            ]
        )
        index += 1

    lines.extend(
        [
            "",
            "name_OSDSYS_ITEM_200 = Shutdown",
            "path1_OSDSYS_ITEM_200 = POWEROFF",
        ]
    )
    return "\n".join(lines) + "\n"


def _localized(language: str, pt: str, en: str, es: str) -> str:
    if language.lower().startswith("pt"):
        return pt
    if language.lower().startswith("es"):
        return es
    return en


def _write_readmes(
    package_root: Path,
    mc_root: Path,
    storage_root: Path,
    plan: dict[str, Any],
    layout: dict[str, Any],
    warnings: list[str],
) -> None:
    language = str(plan.get("language") or "en")
    storage = plan.get("storage") or {}
    card = plan.get("memory_card") or {}
    apa_partition = layout.get("apa_partition")

    extra = ""
    if apa_partition:
        extra = _localized(
            language,
            f"\nHDD APA/PFS: monte/crie primeiro a partição {apa_partition} e copie APPS para a raiz PFS dela.\n",
            f"\nAPA/PFS HDD: create/mount partition {apa_partition} first and copy APPS to that PFS root.\n",
            f"\nHDD APA/PFS: crea/monta primero la partición {apa_partition} y copia APPS a su raíz PFS.\n",
        )
    elif storage.get("id") == "hdd-exfat":
        extra = _localized(
            language,
            "\nHDD exFAT: copie APPS para a raiz exFAT. O R1 do PS2BBL não é configurado neste modo.\n",
            "\nexFAT HDD: copy APPS to the exFAT root. PS2BBL R1 is not configured in this mode.\n",
            "\nHDD exFAT: copia APPS a la raíz exFAT. R1 de PS2BBL no se configura en este modo.\n",
        )

    warning_text = "\n".join(f"- {w}" for w in warnings) if warnings else _localized(language, "nenhum", "none", "ninguno")
    r1_enabled = bool((plan.get("boot") or {}).get("r1_osdmenu", True)) and bool(layout.get("ps2bbl_prefix"))
    r1_instruction = _localized(
        language,
        "3. Segure R1 durante o PS2BBL para abrir o OSDMenu.",
        "3. Hold R1 while PS2BBL starts to open OSDMenu.",
        "3. Mantén R1 durante PS2BBL para abrir OSDMenu.",
    ) if r1_enabled else _localized(
        language,
        "3. O atalho R1 -> OSDMenu não foi configurado neste pacote.",
        "3. The R1 -> OSDMenu shortcut is not configured in this package.",
        "3. El acceso R1 -> OSDMenu no está configurado en este paquete.",
    )
    main = _localized(
        language,
        f"""Ps2Installer - Pacote gerado\n\nMemory Card: {card.get('name', '?')}\nArmazenamento de apps: {storage.get('name', '?')}\n\n1. Copie o CONTEUDO da pasta do Memory Card/VMC para a raiz do seu MC/VMC.\n2. Copie o CONTEUDO da pasta de armazenamento para {layout['target']}.\n{r1_instruction}\n4. Os ELFs em APPS recebem title.cfg quando devem aparecer no OPL.\n{extra}\nIMPORTANTE: BOOT/BOOT.ELF e um ELF do PS2BBL; ele nao instala sozinho um exploit/autoboot.\n\nAvisos:\n{warning_text}\n""",
        f"""Ps2Installer - Generated package\n\nMemory Card: {card.get('name', '?')}\nApps storage: {storage.get('name', '?')}\n\n1. Copy the CONTENTS of the Memory Card/VMC folder to the MC/VMC root.\n2. Copy the CONTENTS of the storage folder to {layout['target']}.\n{r1_instruction}\n4. ELFs under APPS get title.cfg when they should appear in OPL.\n{extra}\nIMPORTANT: BOOT/BOOT.ELF is a PS2BBL ELF; it does not install an exploit/autoboot by itself.\n\nWarnings:\n{warning_text}\n""",
        f"""Ps2Installer - Paquete generado\n\nMemory Card: {card.get('name', '?')}\nAlmacenamiento de apps: {storage.get('name', '?')}\n\n1. Copia el CONTENIDO de la carpeta Memory Card/VMC a la raíz del MC/VMC.\n2. Copia el CONTENIDO de la carpeta de almacenamiento a {layout['target']}.\n{r1_instruction}\n4. Los ELF dentro de APPS reciben title.cfg cuando deben aparecer en OPL.\n{extra}\nIMPORTANTE: BOOT/BOOT.ELF es un ELF de PS2BBL; no instala por sí solo un exploit/autoboot.\n\nAdvertencias:\n{warning_text}\n""",
    )
    (package_root / "README.txt").write_text(main, encoding="utf-8")

    mc_copy = _localized(
        language,
        "COPIE O CONTEUDO DESTA PASTA PARA A RAIZ DO MEMORY CARD/VMC.\n",
        "COPY THE CONTENTS OF THIS FOLDER TO THE MEMORY CARD/VMC ROOT.\n",
        "COPIA EL CONTENIDO DE ESTA CARPETA A LA RAÍZ DE LA MEMORY CARD/VMC.\n",
    )
    (mc_root / "README-COPY-HERE.txt").write_text(mc_copy, encoding="utf-8")

    storage_copy = _localized(
        language,
        f"COPIE APPS PARA {layout['target']}.\n",
        f"COPY APPS TO {layout['target']}.\n",
        f"COPIA APPS A {layout['target']}.\n",
    )
    (storage_root / "README-COPY-HERE.txt").write_text(storage_copy, encoding="utf-8")


def _write_apa_opl_helper(package_root: Path, partition: str, language: str) -> str | None:
    if partition == "+OPL":
        return None

    helper = package_root / "3_HDD_APA_OPL_CONFIG" / "__common" / "OPL"
    helper.mkdir(parents=True, exist_ok=True)
    (helper / "conf_hdd.cfg").write_text(f"hdd_partition={partition}\n", encoding="utf-8")
    readme = package_root / "3_HDD_APA_OPL_CONFIG" / "README-COPY-HERE.txt"
    readme.write_text(
        _localized(
            language,
            "Copie OPL/conf_hdd.cfg para a raiz da particao __common. Isso faz o OPL usar a mesma particao PFS escolhida pelo Ps2Installer para APPS.\n",
            "Copy OPL/conf_hdd.cfg to the __common partition root. This makes OPL use the same PFS partition selected by Ps2Installer for APPS.\n",
            "Copia OPL/conf_hdd.cfg a la raíz de la partición __common. Esto hace que OPL use la misma partición PFS elegida por Ps2Installer para APPS.\n",
        ),
        encoding="utf-8",
    )
    return str(helper.parent.parent)


def build_package(plan: dict[str, Any], output_root: Path) -> dict[str, Any]:
    package_root = output_root / "Ps2Installer_Package"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True, exist_ok=True)

    memory = plan.get("memory_card") or {}
    storage = plan.get("storage") or {}
    mc_folder = MEMORY_CARD_FOLDERS.get(str(memory.get("id")), "1_MEMORY_CARD")
    layout = _storage_layout(storage)
    mc_root = package_root / mc_folder
    storage_root = package_root / str(layout["folder"])
    (mc_root / "BOOT").mkdir(parents=True, exist_ok=True)
    (mc_root / "SYS-CONF").mkdir(parents=True, exist_ok=True)
    (storage_root / "APPS").mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    if layout.get("warning"):
        warnings.append(str(layout["warning"]))

    installed_apps: dict[str, Any] = {}
    downloads = plan.get("downloads") or {}
    for app in plan.get("homebrews", []) or []:
        app_id = str(app.get("id") or "")
        if not app_id or app_id == "ps2bbl" or str(app.get("source_type") or "github") == "manual":
            continue
        download = downloads.get(app_id) or {}
        folder = str(app.get("folder") or app_id)
        dest_dir = storage_root / "APPS" / folder
        installed_elf, install_mode = _install_app_payload(app, download, dest_dir)
        if install_mode != "collection" and installed_elf is None:
            warnings.append(f"{app.get('name', app_id)}: no installable downloaded payload was found; skipped.")
            continue
        if install_mode == "collection" and not dest_dir.exists():
            warnings.append(f"{app.get('name', app_id)}: downloaded collection was not found; skipped.")
            continue

        display_name = _display_name(app)
        menu_targets = dict(app.get("menu_targets") or {})
        relative_path = None
        elf_name = None
        if installed_elf is not None:
            elf_name = installed_elf.name
            relative_path = installed_elf.relative_to(storage_root).as_posix()

        installed_apps[app_id] = {
            "name": app.get("name") or app_id,
            "display_name": display_name,
            "folder": folder,
            "elf": elf_name,
            "relative_path": relative_path,
            "install_mode": install_mode,
            "recipe": recipe_for(app).get("id"),
            "menu_targets": menu_targets,
        }
        if menu_targets.get("opl") and installed_elf is not None:
            boot_path = installed_elf.relative_to(dest_dir).as_posix()
            (dest_dir / "title.cfg").write_text(
                f"title={display_name}\nboot={boot_path}\n",
                encoding="utf-8",
            )

    # In update mode, keep existing APPS visible when rebuilding the menu.
    workflow = plan.get("workflow") or {}
    if str(workflow.get("mode") or "new") == "update" and bool(workflow.get("rebuild_menus", True)):
        removed_folders = {str(value).lower() for value in workflow.get("remove_folders", []) or []}
        selected_folders = {str(item.get("folder") or "").lower() for item in installed_apps.values()}
        for existing in plan.get("existing_apps", []) or []:
            folder = str(existing.get("folder") or "")
            if not folder or folder.lower() in removed_folders or folder.lower() in selected_folders:
                continue
            existing_id = str(existing.get("id") or f"existing:{folder}")
            installed_apps[existing_id] = {
                "name": existing.get("name") or folder,
                "display_name": existing.get("name") or folder,
                "folder": folder,
                "elf": existing.get("elf"),
                "relative_path": existing.get("relative_path"),
                "install_mode": "existing",
                "recipe": "existing-installation",
                "menu_targets": dict(existing.get("menu_targets") or {"osdmenu": True, "opl": False}),
                "existing": True,
            }

    ps2bbl_manifest: dict[str, Any] | None = None
    ps2bbl_download = downloads.get("ps2bbl") or {}
    variant = str(layout.get("ps2bbl_variant") or "")
    if variant:
        source = _find_ps2bbl_elf(ps2bbl_download, variant)
        if source:
            destination = mc_root / "BOOT" / "BOOT.ELF"
            shutil.copy2(source, destination)
            ps2bbl_manifest = {
                "variant": variant,
                "destination": str(destination),
            }
        else:
            warnings.append(f"PS2BBL: required variant {variant} was not found in the extracted archive.")

    boot_options = plan.get("boot") or {}
    enable_r1 = bool(boot_options.get("r1_osdmenu", True))
    (mc_root / "SYS-CONF" / "PS2BBL.INI").write_text(
        _build_ps2bbl_ini(layout, installed_apps, enable_r1=enable_r1), encoding="utf-8"
    )
    (mc_root / "SYS-CONF" / "OSDMENU.CNF").write_text(
        _build_osdmenu_cnf(layout, installed_apps), encoding="utf-8"
    )

    apa_helper = None
    if storage.get("id") == "hdd-apa":
        partition = str(layout.get("apa_partition") or "+OPL")
        apa_helper = _write_apa_opl_helper(package_root, partition, str(plan.get("language") or "en"))

    manual_sources = _write_manual_sources(package_root, plan)
    _write_readmes(package_root, mc_root, storage_root, plan, layout, warnings)
    boot_manifest = write_boot_guide(package_root, plan, ps2bbl_manifest)
    compatibility = check_compatibility(plan)

    manifest = {
        "schema_version": 4,
        "package_root": str(package_root),
        "memory_card_folder": mc_folder,
        "storage_folder": str(layout["folder"]),
        "storage_id": storage.get("id"),
        "apa_partition": layout.get("apa_partition"),
        "osdmenu_prefix": layout.get("osd_prefix"),
        "ps2bbl_prefix": layout.get("ps2bbl_prefix"),
        "ps2bbl": ps2bbl_manifest,
        "boot": boot_manifest,
        "installed_apps": installed_apps,
        "manual_sources": manual_sources,
        "opl_hdd_config_helper": apa_helper,
        "compatibility": compatibility,
        "warnings": warnings,
    }
    manifest["recipes_guide"] = write_recipe_guide(package_root, plan)
    manifest["report"] = write_installation_report(package_root, plan, manifest, compatibility)
    (package_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
