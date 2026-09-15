from __future__ import annotations

from typing import Any


def _finding(rule: str, severity: str, message: str) -> dict[str, str]:
    return {"rule": rule, "severity": severity, "message": message}


def _loc(language: str, pt: str, en: str, es: str) -> str:
    if language.lower().startswith("pt"):
        return pt
    if language.lower().startswith("es"):
        return es
    return en


def check_compatibility(plan: dict[str, Any]) -> list[dict[str, str]]:
    """Return deterministic compatibility/setup findings for the selected plan.

    The detector warns instead of guessing hardware facts the user did not
    provide. Rules are intentionally concrete and tied to known setup edges.
    """
    language = str(plan.get("language") or "en")
    apps = {str(app.get("id") or "") for app in plan.get("homebrews", []) or []}
    storage = plan.get("storage") or {}
    storage_id = str(storage.get("id") or "")
    boot = plan.get("boot") or {}
    boot_id = str(boot.get("id") or "existing")
    workflow = plan.get("workflow") or {}
    findings: list[dict[str, str]] = []

    opl_entry = next((app for app in plan.get("homebrews", []) or [] if str(app.get("id") or "") == "opl"), None)
    opl_resolved = (opl_entry or {}).get("resolved") or {}
    opl_channel = str(opl_resolved.get("channel") or "").lower()
    opl_version = str(opl_resolved.get("version") or "").lower()
    opl_is_beta = opl_channel in {"prerelease", "development", "nightly"} or any(
        token in opl_version for token in ("beta", "alpha", "rc", "pre")
    )
    if "popsloader" in apps and "opl" in apps and opl_is_beta:
        findings.append(_finding(
            "opl-popsloader-apps",
            "warning",
            _loc(
                language,
                "POPSLoader já teve travamento documentado ao ser iniciado pelo menu APPS do OPL em alguns builds beta 1.2. Se acontecer, mantenha um atalho direto pelo OSDMenu/FMCB/wLaunchELF.",
                "POPSLoader has had a documented hang when launched from the OPL APPS menu on some OPL 1.2 beta builds. Keep a direct OSDMenu/FMCB/wLaunchELF path available if affected.",
                "POPSLoader ha tenido un bloqueo documentado al iniciarse desde APPS de OPL en algunos builds beta 1.2. Conserva un acceso directo por OSDMenu/FMCB/wLaunchELF si ocurre.",
            ),
        ))

    if "nhddl" in apps and "neutrino" not in apps:
        findings.append(_finding(
            "nhddl-neutrino",
            "warning",
            _loc(
                language,
                "NHDDL depende de uma instalação compatível do Neutrino. Neutrino não está selecionado, então essa dependência precisa ser concluída manualmente.",
                "NHDDL depends on a compatible Neutrino setup. Neutrino is not selected, so finish that dependency manually.",
                "NHDDL depende de una instalación compatible de Neutrino. Neutrino no está seleccionado, por lo que esa dependencia debe completarse manualmente.",
            ),
        ))


    safety_notes = {
        "mechapwn": (
            "mechapwn-hardware-config",
            "MechaPwn altera configuração/região do MechaCon em modelos suportados. Confira compatibilidade e faça backup das informações do console antes de usar.",
            "MechaPwn changes MechaCon/region configuration on supported models. Verify compatibility and back up console information before use.",
            "MechaPwn modifica la configuración/región de MechaCon en modelos compatibles. Verifica compatibilidad y respalda la información de la consola antes de usarlo.",
        ),
        "memory-card-annihilator": (
            "memory-card-annihilator-destructive",
            "Memory Card Annihilator pode formatar e sobrescrever cartões. Faça dump/backup antes de qualquer operação destrutiva.",
            "Memory Card Annihilator can format and overwrite cards. Make a dump/backup before destructive operations.",
            "Memory Card Annihilator puede formatear y sobrescribir tarjetas. Haz un dump/backup antes de operaciones destructivas.",
        ),
        "hddchecker": (
            "hddchecker-destructive",
            "HDDChecker possui testes/operações destrutivas como zero-fill. Leia as opções com cuidado antes de executá-las no HDD do PS2.",
            "HDDChecker includes destructive tests/operations such as zero-fill. Read the options carefully before running them on the PS2 HDD.",
            "HDDChecker incluye pruebas/operaciones destructivas como zero-fill. Lee las opciones con cuidado antes de ejecutarlas en el HDD de PS2.",
        ),
        "opentuna-installer": (
            "opentuna-installer-card-changes",
            "O OpenTuna Installer altera pastas da Memory Card e pode remover estruturas conflitantes. Faça backup do cartão antes da instalação.",
            "The OpenTuna Installer changes Memory Card folders and may remove conflicting layouts. Back up the card before installation.",
            "OpenTuna Installer modifica carpetas de la Memory Card y puede eliminar estructuras en conflicto. Haz una copia de seguridad antes de instalar.",
        ),
        "hdlgameinstaller": (
            "hdlgameinstaller-apaext",
            "HDLGameInstaller não deve ser usado em HDD formatado com APAEXT/ToxicOS; o upstream alerta para risco de perda de dados.",
            "HDLGameInstaller must not be used on APAEXT/ToxicOS-formatted HDDs; upstream warns of possible data loss.",
            "HDLGameInstaller no debe usarse en HDD con APAEXT/ToxicOS; upstream advierte sobre posible pérdida de datos.",
        ),
    }
    for app_id, (rule, pt, en, es) in safety_notes.items():
        if app_id in apps:
            findings.append(_finding(rule, "warning", _loc(language, pt, en, es)))

    if "opl" in apps and "oplevolution" in apps:
        findings.append(_finding(
            "multiple-opl-builds",
            "info",
            _loc(
                language,
                "OPL oficial e OPL Evolution foram selecionados. Eles ficam em pastas separadas; mantenha o OPL oficial como opção de recuperação.",
                "Official OPL and OPL Evolution are both selected. They are installed in separate folders; keep the official build as a recovery option.",
                "OPL oficial y OPL Evolution están seleccionados. Se instalan en carpetas separadas; conserva OPL oficial como opción de recuperación.",
            ),
        ))

    if storage_id == "hdd-exfat":
        findings.append(_finding(
            "ps2bbl-exfat-r1",
            "warning",
            _loc(
                language,
                "OSDMenu pode usar ata:/ no HDD exFAT, mas o Ps2Installer deixa o R1 do PS2BBL sem vínculo até o lançamento via ata:/ ser validado no build oficial empacotado.",
                "OSDMenu can use ata:/ on the exFAT HDD, but Ps2Installer intentionally leaves PS2BBL R1 unbound until ata:/ launch support is verified for the packaged PS2BBL build.",
                "OSDMenu puede usar ata:/ en HDD exFAT, pero Ps2Installer deja R1 de PS2BBL sin enlace hasta verificar el lanzamiento ata:/ en el build oficial empaquetado.",
            ),
        ))

    if storage_id == "hdd-apa" and str(storage.get("apa_partition") or "+OPL") != "+OPL":
        findings.append(_finding(
            "opl-custom-apa-partition",
            "info",
            _loc(
                language,
                "Uma partição APA/PFS diferente de +OPL foi escolhida. O Ps2Installer gerará um helper conf_hdd.cfg para o OPL usar a mesma partição de APPS.",
                "A non-default APA/PFS partition is selected. Ps2Installer will generate an OPL conf_hdd.cfg helper so APPS uses the same partition.",
                "Se eligió una partición APA/PFS distinta de +OPL. Ps2Installer generará un helper conf_hdd.cfg para que OPL use la misma partición de APPS.",
            ),
        ))

    if boot_id == "system-update":
        findings.append(_finding(
            "system-update-model-compat",
            "warning",
            _loc(
                language,
                "O autoboot System Update/KELF do PS2BBL depende do modelo/boot ROM; SCPH-90xxx tardios e alguns modelos raros não conseguem autoboot por esse método. O pacote não tenta adivinhar o modelo do console.",
                "PS2BBL System Update/KELF autoboot is model/boot-ROM dependent; late SCPH-90xxx and some rare models cannot autoboot this way. The generated package does not guess the console model.",
                "El autoboot System Update/KELF de PS2BBL depende del modelo/boot ROM; SCPH-90xxx tardíos y algunos modelos raros no pueden autoboot con este método. El paquete no intenta adivinar el modelo.",
            ),
        ))
    elif boot_id == "hdd-kelf":
        if storage_id != "hdd-apa":
            findings.append(_finding(
                "hdd-kelf-storage",
                "warning",
                _loc(
                    language,
                    "Boot HDD/KELF foi escolhido sem armazenamento HDD APA/PFS. Esse método precisa de um setup de HDD interno compatível e instalação KELF externa.",
                    "HDD KELF boot was selected without APA/PFS HDD storage. The boot method requires a compatible internal-HDD setup and external KELF installation.",
                    "Se eligió arranque HDD/KELF sin almacenamiento HDD APA/PFS. Este método requiere un HDD interno compatible e instalación KELF externa.",
                ),
            ))
    elif boot_id == "dev1":
        findings.append(_finding(
            "dev1-modchip",
            "info",
            _loc(
                language,
                "DEV1 exige um modchip compatível configurado para iniciar o caminho BOOT/BOOT.ELF do Memory Card.",
                "DEV1 requires a compatible modchip configured to launch the Memory Card BOOT/BOOT.ELF path.",
                "DEV1 requiere un modchip compatible configurado para iniciar BOOT/BOOT.ELF desde la Memory Card.",
            ),
        ))
    elif boot_id == "opentuna":
        findings.append(_finding(
            "opentuna-entrypoint",
            "info",
            _loc(
                language,
                "BOOT/BOOT.ELF está preparado para um fluxo OpenTuna, mas o OpenTuna precisa já estar instalado ou ser instalado pelo pacote oficial PS2BBL + OpenTuna.",
                "BOOT/BOOT.ELF is prepared for an OpenTuna-style entry point, but OpenTuna itself must already be installed or installed with the official PS2BBL + OpenTuna package.",
                "BOOT/BOOT.ELF está preparado para un flujo OpenTuna, pero OpenTuna debe estar instalado o instalarse con el paquete oficial PS2BBL + OpenTuna.",
            ),
        ))

    if workflow.get("remove_folders") and not workflow.get("rebuild_menus", True):
        findings.append(_finding(
            "removed-app-stale-menu",
            "warning",
            _loc(
                language,
                "Há apps marcados para remoção, mas a reconstrução dos menus está desativada. Entradas antigas podem permanecer nos arquivos de configuração.",
                "Apps are marked for removal while menu rebuilding is disabled. Stale launcher entries may remain in configuration files.",
                "Hay apps marcadas para eliminar pero la reconstrucción de menús está desactivada. Pueden quedar entradas antiguas en la configuración.",
            ),
        ))

    return findings


def has_blocking_findings(findings: list[dict[str, str]]) -> bool:
    return any(str(item.get("severity")) == "error" for item in findings)
