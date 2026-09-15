from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class GitHubError(RuntimeError):
    """Raised when GitHub release metadata cannot be resolved."""


@dataclass(frozen=True)
class ResolvedRelease:
    app_id: str
    name: str
    repository: str
    channel: str
    channel_label: str
    version: str
    prerelease: bool
    release_tag: str
    release_name: str
    published_at: str | None
    asset_name: str
    asset_url: str
    asset_size: int | None
    asset_digest: str | None
    archive_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "name": self.name,
            "repository": self.repository,
            "channel": self.channel,
            "channel_label": self.channel_label,
            "version": self.version,
            "prerelease": self.prerelease,
            "release_tag": self.release_tag,
            "release_name": self.release_name,
            "published_at": self.published_at,
            "asset": {
                "name": self.asset_name,
                "url": self.asset_url,
                "size": self.asset_size,
                "digest": self.asset_digest,
                "archive_type": self.archive_type,
            },
        }


class GitHubReleaseResolver:
    """Resolve stable/prerelease/development release assets from GitHub."""

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._token = os.environ.get("GITHUB_TOKEN", "").strip()

    def _get_json(self, url: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Ps2Installer/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise GitHubError(
                    "GitHub API rate limit reached. Set GITHUB_TOKEN and try again."
                ) from exc
            raise GitHubError(f"GitHub API returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GitHubError(f"Could not contact GitHub: {exc}") from exc

    def releases(self, repository: str) -> list[dict[str, Any]]:
        if repository not in self._cache:
            url = f"https://api.github.com/repos/{repository}/releases?per_page=100"
            payload = self._get_json(url)
            if not isinstance(payload, list):
                raise GitHubError(f"Unexpected releases response for {repository}")
            self._cache[repository] = [
                release for release in payload if not release.get("draft", False)
            ]
        return self._cache[repository]

    def resolve_options(self, app: dict[str, Any]) -> list[ResolvedRelease]:
        repository = app.get("repository")
        if not repository:
            raise GitHubError(f"{app.get('name', 'App')} has no repository configured")

        releases = self.releases(repository)
        results: list[ResolvedRelease] = []

        for channel_id, cfg in app.get("channels", {}).items():
            release = self._select_release(releases, cfg)
            if release is None:
                continue
            asset = self._select_asset(release, cfg)
            if asset is None:
                continue

            version = self._detect_version(app, release)
            if not version:
                version = self._fallback_version(release, cfg)

            results.append(
                ResolvedRelease(
                    app_id=app["id"],
                    name=app["name"],
                    repository=repository,
                    channel=channel_id,
                    channel_label=cfg.get("label", channel_id.title()),
                    version=version,
                    prerelease=bool(release.get("prerelease", False)),
                    release_tag=str(release.get("tag_name") or ""),
                    release_name=str(release.get("name") or release.get("tag_name") or ""),
                    published_at=release.get("published_at"),
                    asset_name=str(asset["name"]),
                    asset_url=str(asset["browser_download_url"]),
                    asset_size=asset.get("size"),
                    asset_digest=asset.get("digest"),
                    archive_type=cfg.get("archive_type", _archive_type(str(asset["name"]))),
                )
            )

        return results

    @staticmethod
    def _select_release(
        releases: list[dict[str, Any]], cfg: dict[str, Any]
    ) -> dict[str, Any] | None:
        tag = cfg.get("tag")
        kind = cfg.get("release_kind", "stable")

        if tag:
            candidates = [r for r in releases if r.get("tag_name") == tag]
        elif kind == "stable":
            candidates = [r for r in releases if not r.get("prerelease", False)]
        elif kind in {"prerelease", "development"}:
            candidates = [r for r in releases if r.get("prerelease", False)]
        elif kind == "any":
            candidates = releases
        else:
            raise GitHubError(f"Unknown release_kind: {kind}")

        return candidates[0] if candidates else None

    @staticmethod
    def _select_asset(
        release: dict[str, Any], cfg: dict[str, Any]
    ) -> dict[str, Any] | None:
        assets = list(release.get("assets") or [])
        patterns = cfg.get("asset_patterns") or []
        excludes = cfg.get("exclude_asset_patterns") or []

        def is_excluded(name: str) -> bool:
            return any(re.search(p, name, re.IGNORECASE) for p in excludes)

        for pattern in patterns:
            for asset in assets:
                name = str(asset.get("name") or "")
                if not is_excluded(name) and re.search(pattern, name, re.IGNORECASE):
                    return asset

        if not patterns:
            usable = [a for a in assets if not is_excluded(str(a.get("name") or ""))]
            if len(usable) == 1:
                return usable[0]
        return None

    @staticmethod
    def _detect_version(app: dict[str, Any], release: dict[str, Any]) -> str | None:
        regex = app.get("version_regex")
        if regex:
            sources = [
                str(release.get("tag_name") or ""),
                str(release.get("name") or ""),
            ]
            sources += [str(a.get("name") or "") for a in release.get("assets") or []]
            for source in sources:
                match = re.search(regex, source, re.IGNORECASE)
                if not match:
                    continue
                if "version" in match.groupdict():
                    return match.group("version")
                if match.groups():
                    return match.group(1)
                return match.group(0)

        tag = str(release.get("tag_name") or "").strip()
        if tag and tag.lower() not in {"latest", "nightly", "continuous"}:
            return tag
        return None

    @staticmethod
    def _fallback_version(release: dict[str, Any], cfg: dict[str, Any]) -> str:
        prefix = cfg.get("fallback_version_prefix", "build")
        timestamp = (
            release.get("published_at")
            or release.get("updated_at")
            or release.get("created_at")
        )
        if timestamp:
            try:
                day = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).date()
                return f"{prefix}-{day.isoformat()}"
            except ValueError:
                pass
        return prefix


def _archive_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".elf"):
        return "elf"
    if lower.endswith(".zip"):
        return "zip"
    if lower.endswith(".7z"):
        return "7z"
    return "file"
