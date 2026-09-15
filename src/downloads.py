from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from .releases import ResolvedRelease


class DownloadError(RuntimeError):
    """Raised when a release asset cannot be downloaded or extracted."""


def download_release(
    release: ResolvedRelease,
    output_root: Path,
    elf_names: list[str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    app_dir = output_root / release.app_id
    download_dir = app_dir / "download"
    extracted_dir = app_dir / "extracted"
    download_dir.mkdir(parents=True, exist_ok=True)

    asset_path = download_dir / release.asset_name
    _download_file(release.asset_url, asset_path, timeout)
    _verify_digest(asset_path, release.asset_digest)

    extracted = False
    warning: str | None = None

    if release.archive_type == "elf":
        _reset_directory(extracted_dir)
        shutil.copy2(asset_path, extracted_dir / release.asset_name)
        extracted = True
    elif release.archive_type == "zip":
        _reset_directory(extracted_dir)
        _safe_extract_zip(asset_path, extracted_dir)
        extracted = True
    elif release.archive_type == "7z":
        try:
            _reset_directory(extracted_dir)
            _safe_extract_7z(asset_path, extracted_dir)
            extracted = True
        except DownloadError as exc:
            warning = str(exc)

    candidates = _find_elf_candidates(extracted_dir, elf_names or []) if extracted else []
    return {
        "asset_path": str(asset_path),
        "extracted_path": str(extracted_dir) if extracted else None,
        "extracted": extracted,
        "elf_candidates": [str(path) for path in candidates],
        "warning": warning,
    }


def _reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _download_file(url: str, destination: Path, timeout: int) -> None:
    temp = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Ps2Installer/0.2"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, temp.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        os.replace(temp, destination)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        temp.unlink(missing_ok=True)
        raise DownloadError(f"Failed to download {url}: {exc}") from exc


def _verify_digest(path: Path, digest: str | None) -> None:
    if not digest or not digest.lower().startswith("sha256:"):
        return

    expected = digest.split(":", 1)[1].lower()
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)

    if hasher.hexdigest().lower() != expected:
        path.unlink(missing_ok=True)
        raise DownloadError(f"SHA-256 mismatch for {path.name}")


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zip_file:
        for member in zip_file.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise DownloadError(f"Unsafe ZIP entry: {member.filename}")
        zip_file.extractall(destination)


def _native_7z_command() -> str | None:
    for name in ("7z", "7zz", "7za", "7zr"):
        command = shutil.which(name)
        if command:
            return command
    return None


def _safe_extract_7z(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    native_7z = _native_7z_command()
    if native_7z:
        listing = subprocess.run(
            [native_7z, "l", "-slt", "-ba", str(archive)],
            check=False,
            capture_output=True,
            text=True,
        )
        if listing.returncode != 0:
            detail = (getattr(listing, "stderr", "") or getattr(listing, "stdout", "") or "").strip()
            raise DownloadError(
                f"7z could not read {archive.name}: {detail or f'exit status {listing.returncode}'}"
            )

        for line in (getattr(listing, "stdout", "") or "").splitlines():
            if not line.startswith("Path = "):
                continue
            name = line[len("Path = "):].strip()
            if not name:
                continue
            target = (destination / name).resolve()
            if target != root and root not in target.parents:
                raise DownloadError(f"Unsafe 7z entry: {name}")

        completed = subprocess.run(
            [
                native_7z,
                "x",
                "-y",
                "-bd",
                "-bso0",
                "-bsp0",
                str(archive),
                f"-o{destination}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = (getattr(completed, "stderr", "") or getattr(completed, "stdout", "") or "").strip()
            raise DownloadError(
                f"7z extraction failed for {archive.name}: "
                f"{detail or f'exit status {completed.returncode}'}"
            )
        return

    try:
        import py7zr  # type: ignore
    except ImportError as exc:
        raise DownloadError(
            "No 7z extraction backend was found. Install 7-Zip or py7zr. "
            "Termux/Android: pkg install 7zip"
        ) from exc

    with py7zr.SevenZipFile(archive, mode="r") as seven_zip:
        for name in seven_zip.getnames():
            target = (destination / name).resolve()
            if target != root and root not in target.parents:
                raise DownloadError(f"Unsafe 7z entry: {name}")
        seven_zip.extractall(path=destination)


def _find_elf_candidates(root: Path, preferred_names: list[str]) -> list[Path]:
    if not root.exists():
        return []

    all_elfs = sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".elf"
    )
    preferred = {name.lower() for name in preferred_names if "*" not in name and "?" not in name}
    if not preferred:
        return all_elfs

    first = [path for path in all_elfs if path.name.lower() in preferred]
    rest = [path for path in all_elfs if path not in first]
    return first + rest
