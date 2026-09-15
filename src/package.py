from __future__ import annotations

import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any


class PackageError(RuntimeError):
    """Raised when a PS2 installation package cannot be generated."""


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
        # Official PS2BBL uses massX: for MX4SIO application paths.
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
        # OSDMenu supports ata:, but upstream PS2BBL does not expose ata: as an
        # application path in the common official build. Keep this explicit.
        "ps2bbl_prefix": None,
        "ps2bbl_variant": None,
        "target": "internal exFAT HDD root",
    },
    "hdd-apa": {
        "folder": "2_HDD_APA",
        "osd_prefix": "hdd0:__common:pfs:",
        "ps2bbl_prefix": "hdd0:__common:pfs:",
        "ps2bbl_variant": "PS2_HDD",
        "target": "hdd0:__common:pfs:/",
    },
}

MEMORY_CARD_FOLDERS = {
    "standard": "1_MEMORY_CARD",
    "sd2psx": "1_SD2PSX_VMC",
    "memcard-pro2": "1_MEMCARD_PRO2_VMC",
    "psxmemcard-gen2": "1_PSXMEMCARD_GEN2_VMC",
    "other-mmce": "1_MMCE_VMC",
}


def build_package(plan: dict[str, Any], output_root: Path) -> dict[str, Any]:
    storage_id = str(plan.get("storage", {}).get("id") or "")
    storage_cfg = STORAGE_LAYOUTS.get(storage_id)
    if storage_cfg is None:
        raise PackageError(f"Unsupported storage type: {storage_id or 'unknown'}")

    card_id = str(plan.get("memory_card", {}).get("id") or "standard")
    mc_folder = MEMORY_CARD_FOLDERS.get(card_id, "1_MEMORY_CARD")

    package_root = output_root / "Ps2Installer_Package"
    if package_root.exists():
        shutil.rmtree(package_root)

    mc_root = package_root / mc_folder
    storage_root = package_root / str(storage_cfg["folder"])
    (mc_root / "BOOT").mkdir(parents=True, exist_ok=True)
    (mc_root / "SYS-CONF").mkdir(parents=True, exist_ok=True)
    (storage_root / "APPS").mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    installed: dict[str, dict[str, Any]] = {}

    for app in plan.get("homebrews", []):
        app_id = str(app.get("id") or "")
        if app_id == "ps2bbl":
            continue

        source = _select_app_elf(app, plan.get("downloads", {}).get(app_id))
        if source is None:
            warnings.append(f"{app.get('name', app_id)}: no downloaded ELF was found; skipped.")
            continue

        folder = str(app.get("folder") or app_id or "APP")
        app_dir = storage_root / "APPS" / folder
        app_dir.mkdir(parents=True, exist_ok=True)
        destination = app_dir / source.name
        shutil.copy2(source, destination)

        display_name = _display_name(app)
        if app.get("menu_targets", {}).get("opl", False):
            (app_dir / "title.cfg").write_text(
                f"title={display_name}\nboot={destination.name}\n",
                encoding="utf-8",
            )

        installed[app_id] = {
            "name": app.get("name", app_id),
            "display_name": display_name,
            "folder": folder,
            "elf": destination.name,
            "relative_path": str(PurePosixPath("APPS") / folder / destination.name),
            "menu_targets": app.get("menu_targets", {}),
        }

    bootloader = _install_ps2bbl(plan, mc_root, storage_cfg, warnings)

    osdmenu_ini = _build_osdmenu_cnf(installed, storage_cfg)
    (mc_root / "SYS-CONF" / "OSDMENU.CNF").write_text(osdmenu_ini, encoding="utf-8")

    ps2bbl_ini = _build_ps2bbl_ini(storage_cfg, installed, warnings)
    (mc_root / "SYS-CONF" / "PS2BBL.INI").write_text(ps2bbl_ini, encoding="utf-8")

    _write_destination_readmes(plan, package_root, mc_root, storage_root, storage_cfg, warnings)

    manifest = {
        "schema_version": 1,
        "package_root": str(package_root),
        "memory_card_folder": mc_root.name,
        "storage_folder": storage_root.name,
        "storage_id": storage_id,
        "ps2bbl": bootloader,
        "installed_apps": installed,
        "warnings": warnings,
    }
    (package_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _install_ps2bbl(
    plan: dict[str, Any],
    mc_root: Path,
    storage_cfg: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any] | None:
    variant = storage_cfg.get("ps2bbl_variant")
    if not variant:
        warnings.append(
            "PS2BBL: upstream official builds do not provide the required ata: "
            "launch path for this internal exFAT layout. OSDMenu files were packaged, "
            "but R1 boot requires a compatible PS2BBL Extended build or another entry point."
        )
        return None

    download = plan.get("downloads", {}).get("ps2bbl")
    if not isinstance(download, dict):
        warnings.append("PS2BBL: release was not downloaded, so BOOT/BOOT.ELF was not generated.")
        return None

    extracted = download.get("extracted_path")
    if not extracted:
        warnings.append("PS2BBL: archive was not extracted; install py7zr and run again.")
        return None

    root = Path(str(extracted))
    if not root.exists():
        warnings.append(f"PS2BBL: extracted directory no longer exists: {root}")
        return None

    candidates = [
        path
        for path in root.rglob("COMPRESSED_PS2BBL.ELF")
        if path.is_file() and variant in path.parts
    ]
    if not candidates:
        warnings.append(
            f"PS2BBL: could not find {variant}/COMPRESSED_PS2BBL.ELF in the downloaded archive."
        )
        return None

    source = sorted(candidates, key=lambda path: (len(path.parts), str(path)))[0]
    destination = mc_root / "BOOT" / "BOOT.ELF"
    shutil.copy2(source, destination)
    return {
        "variant": variant,
        "source": str(source),
        "destination": str(destination),
    }


def _select_app_elf(app: dict[str, Any], download: Any) -> Path | None:
    if not isinstance(download, dict) or download.get("error"):
        return None

    raw_candidates = download.get("elf_candidates") or []
    candidates = [Path(str(path)) for path in raw_candidates]
    candidates = [path for path in candidates if path.is_file()]
    if not candidates:
        return None

    preferred = [str(name).lower() for name in app.get("elf_names", [])]
    for preferred_name in preferred:
        for path in candidates:
            if path.name.lower() == preferred_name:
                return path
    return candidates[0]


def _display_name(app: dict[str, Any]) -> str:
    name = str(app.get("name") or app.get("id") or "Application")
    resolved = app.get("resolved") or {}
    version = str(resolved.get("version") or "").strip()
    channel = str(resolved.get("channel") or "").lower()
    prerelease = bool(resolved.get("prerelease", False))

    label = f"{name} {version}".strip()
    lowered = version.lower()
    if channel == "development" and not any(token in lowered for token in ("dev", "nightly")):
        label += " [Dev]"
    elif prerelease and not any(token in lowered for token in ("beta", "alpha", "rc", "pre")):
        label += " [Prerelease]"
    return label


def _build_osdmenu_cnf(
    installed: dict[str, dict[str, Any]], storage_cfg: dict[str, Any]
) -> str:
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
        "",
    ]

    index = 10
    prefix = str(storage_cfg["osd_prefix"])
    for app in installed.values():
        if not app.get("menu_targets", {}).get("osdmenu", False):
            continue
        if index >= 200:
            break
        path = _device_path(prefix, str(app["relative_path"]))
        lines.extend(
            [
                f"name_OSDSYS_ITEM_{index} = {app['display_name']}",
                f"path1_OSDSYS_ITEM_{index} = {path}",
                "",
            ]
        )
        index += 1

    lines.extend(
        [
            "name_OSDSYS_ITEM_200 = Shutdown",
            "path1_OSDSYS_ITEM_200 = POWEROFF",
            "",
        ]
    )
    return "\n".join(lines)


def _build_ps2bbl_ini(
    storage_cfg: dict[str, Any],
    installed: dict[str, dict[str, Any]],
    warnings: list[str],
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

    osdmenu = installed.get("osdmenu")
    prefix = storage_cfg.get("ps2bbl_prefix")
    if osdmenu and prefix:
        lines.extend(
            [
                "",
                "# Hold R1 while PS2BBL is starting to launch OSDMenu.",
                f"LK_R1_E1 = {_device_path(str(prefix), str(osdmenu['relative_path']))}",
            ]
        )
    elif not osdmenu:
        warnings.append("OSDMenu: no ELF was packaged, therefore R1 has no OSDMenu target.")
        lines.extend(["", "# R1 target omitted: OSDMenu ELF was not available."])
    else:
        lines.extend(
            [
                "",
                "# R1 target omitted: selected storage needs a PS2BBL build with ata: support.",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def _device_path(prefix: str, relative: str) -> str:
    return f"{prefix}/{relative.lstrip('/')}"


def _write_destination_readmes(
    plan: dict[str, Any],
    package_root: Path,
    mc_root: Path,
    storage_root: Path,
    storage_cfg: dict[str, Any],
    warnings: list[str],
) -> None:
    language = str(plan.get("language") or "en")
    card_name = str(plan.get("memory_card", {}).get("name") or "Memory Card")
    storage_name = str(plan.get("storage", {}).get("name") or storage_cfg["target"])

    text = _readme_text(language, card_name, storage_name, storage_cfg, warnings)
    (package_root / "README.txt").write_text(text, encoding="utf-8")

    if language == "pt-BR":
        mc_text = (
            "COPIE O CONTEUDO DESTA PASTA PARA A RAIZ DO MEMORY CARD/VMC.\n\n"
            "Exemplo: BOOT/BOOT.ELF deve terminar como mc0:/BOOT/BOOT.ELF ou mc1:/BOOT/BOOT.ELF.\n"
            "Nao copie a pasta externa inteira para dentro do Memory Card.\n"
        )
        storage_text = (
            f"COPIE O CONTEUDO DESTA PASTA PARA {storage_cfg['target']}.\n\n"
            "A pasta APPS deve ficar diretamente no destino indicado.\n"
        )
    elif language == "es":
        mc_text = (
            "COPIA EL CONTENIDO DE ESTA CARPETA A LA RAIZ DE LA MEMORY CARD/VMC.\n\n"
            "Ejemplo: BOOT/BOOT.ELF debe terminar como mc0:/BOOT/BOOT.ELF o mc1:/BOOT/BOOT.ELF.\n"
            "No copies la carpeta externa completa dentro de la Memory Card.\n"
        )
        storage_text = (
            f"COPIA EL CONTENIDO DE ESTA CARPETA A {storage_cfg['target']}.\n\n"
            "La carpeta APPS debe quedar directamente en el destino indicado.\n"
        )
    else:
        mc_text = (
            "COPY THE CONTENTS OF THIS FOLDER TO THE ROOT OF THE MEMORY CARD/VMC.\n\n"
            "Example: BOOT/BOOT.ELF must end up as mc0:/BOOT/BOOT.ELF or mc1:/BOOT/BOOT.ELF.\n"
            "Do not copy the outer destination folder itself into the Memory Card.\n"
        )
        storage_text = (
            f"COPY THE CONTENTS OF THIS FOLDER TO {storage_cfg['target']}.\n\n"
            "The APPS folder must live directly at the indicated destination.\n"
        )

    (mc_root / "README-COPY-HERE.txt").write_text(mc_text, encoding="utf-8")
    (storage_root / "README-COPY-HERE.txt").write_text(storage_text, encoding="utf-8")


def _readme_text(
    language: str,
    card_name: str,
    storage_name: str,
    storage_cfg: dict[str, Any],
    warnings: list[str],
) -> str:
    if warnings:
        warning_lines = "\n".join(f"- {warning}" for warning in warnings) + "\n"
    elif language == "pt-BR":
        warning_lines = "nenhum\n"
    elif language == "es":
        warning_lines = "ninguno\n"
    else:
        warning_lines = "none\n"

    if language == "pt-BR":
        return (
            "Ps2Installer - Pacote gerado\n\n"
            f"Memory Card: {card_name}\n"
            f"Armazenamento de apps: {storage_name}\n\n"
            "1. Copie o CONTEUDO da pasta do Memory Card/VMC para a raiz do seu MC/VMC.\n"
            f"2. Copie o CONTEUDO da pasta de armazenamento para {storage_cfg['target']}.\n"
            "3. Ao iniciar o PS2BBL, segure R1 para abrir o OSDMenu.\n"
            "4. Os mesmos ELFs em APPS tambem recebem title.cfg quando devem aparecer no OPL.\n\n"
            "IMPORTANTE: BOOT/BOOT.ELF e um ELF do PS2BBL. Ele nao cria sozinho um "
            "exploit/autoboot em um Memory Card comum. O console ainda precisa de um ponto "
            "de entrada compativel (por exemplo, System Update/OpenTuna/modchip conforme seu setup).\n\n"
            "Avisos:\n"
            f"{warning_lines}"
        )
    if language == "es":
        return (
            "Ps2Installer - Paquete generado\n\n"
            f"Memory Card: {card_name}\n"
            f"Almacenamiento de apps: {storage_name}\n\n"
            "1. Copia el CONTENIDO de la carpeta de Memory Card/VMC a la raiz de tu MC/VMC.\n"
            f"2. Copia el CONTENIDO de la carpeta de almacenamiento a {storage_cfg['target']}.\n"
            "3. Al iniciar PS2BBL, manten R1 para abrir OSDMenu.\n"
            "4. Los mismos ELFs en APPS reciben title.cfg cuando deben aparecer en OPL.\n\n"
            "IMPORTANTE: BOOT/BOOT.ELF es un ELF de PS2BBL. Por si solo no instala un "
            "exploit/autoboot en una Memory Card normal; aun necesitas un punto de entrada "
            "compatible con tu setup.\n\n"
            "Avisos:\n"
            f"{warning_lines}"
        )
    return (
        "Ps2Installer - Generated package\n\n"
        f"Memory Card: {card_name}\n"
        f"App storage: {storage_name}\n\n"
        "1. Copy the CONTENTS of the Memory Card/VMC folder to the root of your MC/VMC.\n"
        f"2. Copy the CONTENTS of the storage folder to {storage_cfg['target']}.\n"
        "3. Hold R1 while PS2BBL starts to open OSDMenu.\n"
        "4. The same ELFs under APPS receive title.cfg when they should also appear in OPL.\n\n"
        "IMPORTANT: BOOT/BOOT.ELF is a PS2BBL ELF. It does not by itself install an "
        "exploit/autoboot on a normal Memory Card; your console still needs a compatible "
        "entry point for your setup.\n\n"
        "Warnings:\n"
        f"{warning_lines}"
    )
