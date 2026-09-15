from __future__ import annotations

from pathlib import Path
from typing import Any


def _localized(language: str, pt: str, en: str, es: str) -> str:
    if language.lower().startswith("pt"):
        return pt
    if language.lower().startswith("es"):
        return es
    return en


def write_installation_report(
    package_root: Path,
    plan: dict[str, Any],
    manifest: dict[str, Any],
    findings: list[dict[str, str]],
    update_result: dict[str, Any] | None = None,
) -> str:
    language = str(plan.get("language") or "en")
    title = _localized(language, "RELATÓRIO FINAL DE INSTALAÇÃO", "FINAL INSTALLATION REPORT", "INFORME FINAL DE INSTALACIÓN")
    lines = [title, "=" * len(title), ""]

    boot = manifest.get("boot") or plan.get("boot") or {}
    storage = plan.get("storage") or {}
    memory = plan.get("memory_card") or {}
    status = manifest.get("ready")
    status_text = "READY" if status is True else ("INCOMPLETE" if status is False else "NOT YET VALIDATED")
    lines.extend([
        f"Memory Card: {memory.get('name', '?')}",
        f"Storage: {storage.get('name', '?')}",
        f"PS2BBL boot: {boot.get('id', 'existing')}",
        f"Package status: {status_text}",
        "",
        _localized(language, "Aplicativos instalados:", "Installed apps:", "Aplicaciones instaladas:"),
    ])

    installed = manifest.get("installed_apps") or {}
    if installed:
        for item in installed.values():
            path = item.get("relative_path") or "(collection/no primary ELF)"
            tag = "KEEP" if item.get("existing") else "OK"
            lines.append(f"  [{tag}] {item.get('display_name') or item.get('name')} -> {path}")
    else:
        lines.append("  -")

    manual = manifest.get("manual_sources") or []
    if manual:
        lines.extend(["", _localized(language, "Ações manuais:", "Manual actions:", "Acciones manuales:")])
        for item in manual:
            lines.append(f"  [MANUAL] {item.get('name')}: {item.get('note')}")

    lines.extend(["", _localized(language, "Compatibilidade / avisos:", "Compatibility / warnings:", "Compatibilidad / avisos:")])
    if findings:
        for item in findings:
            severity = str(item.get("severity") or "info").upper()
            lines.append(f"  [{severity}] {item.get('message')}")
    else:
        lines.append("  [OK] No known plan-level compatibility warnings.")

    warnings = manifest.get("warnings") or []
    for warning in warnings:
        lines.append(f"  [WARNING] {warning}")

    if update_result:
        lines.extend(["", _localized(language, "Atualização aplicada:", "Existing installation updated:", "Instalación existente actualizada:")])
        lines.append(f"  Backup: {update_result.get('backup_root')}")
        for changed in update_result.get("changed") or []:
            lines.append(f"  [UPDATED] {changed}")
        for removed in update_result.get("removed") or []:
            lines.append(f"  [REMOVED] APPS/{removed}")

    lines.extend([
        "",
        _localized(
            language,
            "Consulte BOOT_METHOD.txt e README.txt antes de copiar/usar o pacote.",
            "Read BOOT_METHOD.txt and README.txt before copying/using the package.",
            "Lee BOOT_METHOD.txt y README.txt antes de copiar/usar el paquete.",
        ),
        "",
    ])

    report = package_root / "INSTALLATION_REPORT.txt"
    report.write_text("\n".join(lines), encoding="utf-8")
    return str(report)
