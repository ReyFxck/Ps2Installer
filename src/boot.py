from __future__ import annotations

from pathlib import Path
from typing import Any


BOOT_METHOD_IDS = ("existing", "opentuna", "dev1", "system-update", "hdd-kelf")


def boot_method_meta(method_id: str) -> dict[str, Any]:
    methods: dict[str, dict[str, Any]] = {
        "existing": {
            "id": "existing",
            "external_required": False,
            "autoboot": False,
        },
        "opentuna": {
            "id": "opentuna",
            "external_required": True,
            "autoboot": True,
        },
        "dev1": {
            "id": "dev1",
            "external_required": False,
            "autoboot": True,
        },
        "system-update": {
            "id": "system-update",
            "external_required": True,
            "autoboot": True,
        },
        "hdd-kelf": {
            "id": "hdd-kelf",
            "external_required": True,
            "autoboot": True,
        },
    }
    return dict(methods.get(method_id, methods["existing"]))


def _localized(language: str, pt: str, en: str, es: str) -> str:
    if language.lower().startswith("pt"):
        return pt
    if language.lower().startswith("es"):
        return es
    return en


def write_boot_guide(package_root: Path, plan: dict[str, Any], ps2bbl_manifest: dict[str, Any] | None) -> dict[str, Any]:
    language = str(plan.get("language") or "en")
    selected = plan.get("boot") or {"id": "existing"}
    method_id = str(selected.get("id") or "existing")
    meta = boot_method_meta(method_id)
    payload_ready = bool(ps2bbl_manifest)

    if method_id == "opentuna":
        body = _localized(
            language,
            "OpenTuna: BOOT/BOOT.ELF foi preparado no Memory Card. O OpenTuna ainda precisa estar instalado; o PS2BBL oficial também publica um pacote PS2BBL + OpenTuna pronto para instalação. Este pacote não instala o exploit sozinho.",
            "OpenTuna: BOOT/BOOT.ELF is prepared on the Memory Card. OpenTuna still needs to be installed; official PS2BBL also publishes a ready PS2BBL + OpenTuna installer package. This package does not install the exploit by itself.",
            "OpenTuna: BOOT/BOOT.ELF está preparado en la Memory Card. OpenTuna todavía debe estar instalado; PS2BBL oficial también publica un paquete instalador PS2BBL + OpenTuna. Este paquete no instala el exploit por sí solo.",
        )
    elif method_id == "dev1":
        body = _localized(
            language,
            "Modchip DEV1: copie a pasta do Memory Card e configure/use o DEV1 do seu modchip para iniciar mc0:/BOOT/BOOT.ELF (ou o slot equivalente suportado pelo modchip).",
            "Modchip DEV1: copy the Memory Card folder and configure/use your modchip DEV1 entry to launch mc0:/BOOT/BOOT.ELF (or the equivalent slot supported by the modchip).",
            "Modchip DEV1: copia la carpeta de Memory Card y configura/usa DEV1 de tu modchip para iniciar mc0:/BOOT/BOOT.ELF (o el slot equivalente soportado por el modchip).",
        )
    elif method_id == "system-update":
        body = _localized(
            language,
            "System Update/KELF: o SYS-CONF/PS2BBL.INI está pronto, mas autoboot exige um KELF oficial (por exemplo SYSTEM.XLF/XSYSTEM.XLF/MX4SIO SYSTEM.XLF conforme o hardware) instalado com a ferramenta apropriada, como KELFBinder/instalador oficial. Não renomeie BOOT.ELF para SYSTEM.XLF: isso não cria um KELF válido.",
            "System Update/KELF: SYS-CONF/PS2BBL.INI is ready, but autoboot requires an official KELF (for example SYSTEM.XLF/XSYSTEM.XLF/MX4SIO SYSTEM.XLF depending on hardware) installed with the appropriate tool such as KELFBinder/the official installer. Do not rename BOOT.ELF to SYSTEM.XLF: that does not create a valid KELF.",
            "System Update/KELF: SYS-CONF/PS2BBL.INI está listo, pero el autoboot requiere un KELF oficial (por ejemplo SYSTEM.XLF/XSYSTEM.XLF/MX4SIO SYSTEM.XLF según el hardware) instalado con KELFBinder/el instalador oficial. No renombres BOOT.ELF a SYSTEM.XLF: eso no crea un KELF válido.",
        )
    elif method_id == "hdd-kelf":
        body = _localized(
            language,
            "Boot por HDD/KELF: use o HSYSTEM.XLF oficial/fluxo compatível com HDD. O pacote gera APPS/configuração, mas não cria, formata ou instala a entrada KELF do HDD.",
            "HDD/KELF boot: use the official HSYSTEM.XLF/compatible HDD installation flow. The package prepares APPS/configuration but does not create, format or install the HDD KELF boot entry.",
            "Arranque HDD/KELF: usa HSYSTEM.XLF oficial/un flujo HDD compatible. El paquete prepara APPS/configuración pero no crea, formatea ni instala la entrada KELF del HDD.",
        )
    else:
        body = _localized(
            language,
            "ELF existente/manual: BOOT/BOOT.ELF é um PS2BBL executável normal. Inicie-o por FMCB, wLaunchELF, OPL, FreeDVDBoot, outro launcher ou fluxo já existente. Este modo não promete autoboot.",
            "Existing/manual ELF: BOOT/BOOT.ELF is a normal PS2BBL executable. Launch it through FMCB, wLaunchELF, OPL, FreeDVDBoot, another launcher or an existing entry point. This mode does not promise autoboot.",
            "ELF existente/manual: BOOT/BOOT.ELF es un ejecutable normal de PS2BBL. Inícialo con FMCB, wLaunchELF, OPL, FreeDVDBoot, otro launcher o una entrada ya existente. Este modo no promete autoboot.",
        )

    r1_enabled = bool(selected.get("r1_osdmenu", True))
    r1_note = _localized(
        language,
        "Atalho R1: configurado para abrir o OSDMenu quando o armazenamento selecionado oferecer um caminho PS2BBL validado.",
        "R1 shortcut: configured to launch OSDMenu when the selected storage has a validated PS2BBL path.",
        "Acceso R1: configurado para abrir OSDMenu cuando el almacenamiento seleccionado tenga una ruta PS2BBL validada.",
    ) if r1_enabled else _localized(
        language,
        "Atalho R1: desativado neste pacote.",
        "R1 shortcut: disabled in this package.",
        "Acceso R1: desactivado en este paquete.",
    )

    header = _localized(language, "Ps2Installer - Método de boot do PS2BBL", "Ps2Installer - PS2BBL boot method", "Ps2Installer - Método de arranque de PS2BBL")
    text = f"{header}\n\n{body}\n\n{r1_note}\n"
    (package_root / "BOOT_METHOD.txt").write_text(text, encoding="utf-8")

    return {
        **meta,
        "payload_ready": payload_ready,
        "r1_osdmenu": r1_enabled,
        "guide": "BOOT_METHOD.txt",
    }
