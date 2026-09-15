from __future__ import annotations

import unittest

from src.releases import GitHubReleaseResolver


class FakeResolver(GitHubReleaseResolver):
    def __init__(self, payload):
        super().__init__()
        self.payload = payload

    def releases(self, repository):
        return self.payload


class ReleaseResolverTests(unittest.TestCase):
    def test_stable_and_prerelease_are_kept_separate(self):
        payload = [
            {
                "tag_name": "latest",
                "name": "latest",
                "prerelease": True,
                "draft": False,
                "published_at": "2026-09-03T23:42:12Z",
                "assets": [
                    {
                        "name": "OPNPS2LD-v1.2.0-Beta-2245-3e3f34e.7z",
                        "browser_download_url": "https://example.invalid/beta.7z",
                        "size": 10,
                        "digest": "sha256:abc",
                    },
                    {
                        "name": "OPNPS2LD.ELF",
                        "browser_download_url": "https://example.invalid/OPNPS2LD.ELF",
                        "size": 5,
                        "digest": "sha256:def",
                    },
                ],
            },
            {
                "tag_name": "v1.1.0",
                "name": "v1.1.0",
                "prerelease": False,
                "draft": False,
                "published_at": "2021-09-09T19:08:06Z",
                "assets": [
                    {
                        "name": "OPNPS2LD-v1.1.0.7z",
                        "browser_download_url": "https://example.invalid/stable.7z",
                        "size": 10,
                        "digest": None,
                    }
                ],
            },
        ]
        app = {
            "id": "opl",
            "name": "Open PS2 Loader",
            "repository": "ps2homebrew/Open-PS2-Loader",
            "version_regex": r"(?P<version>v\d+\.\d+\.\d+(?:-Beta-\d+-[0-9a-f]+)?)",
            "channels": {
                "stable": {
                    "label": "Stable",
                    "release_kind": "stable",
                    "asset_patterns": [r"^OPNPS2LD-v.*\.7z$"],
                },
                "prerelease": {
                    "label": "Beta / prerelease",
                    "release_kind": "prerelease",
                    "asset_patterns": [r"^OPNPS2LD\.ELF$"],
                },
            },
        }

        options = FakeResolver(payload).resolve_options(app)
        self.assertEqual([option.channel for option in options], ["stable", "prerelease"])
        self.assertEqual(options[0].version, "v1.1.0")
        self.assertEqual(options[1].version, "v1.2.0-Beta-2245-3e3f34e")
        self.assertEqual(options[1].asset_name, "OPNPS2LD.ELF")

    def test_latest_tag_uses_date_fallback(self):
        payload = [
            {
                "tag_name": "latest",
                "name": "Latest development build",
                "prerelease": True,
                "published_at": "2026-09-03T23:40:47Z",
                "assets": [
                    {
                        "name": "BOOT.ELF",
                        "browser_download_url": "https://example.invalid/BOOT.ELF",
                        "size": 1,
                        "digest": None,
                    }
                ],
            }
        ]
        app = {
            "id": "wlaunchelf",
            "name": "wLaunchELF",
            "repository": "ps2homebrew/wLaunchELF",
            "channels": {
                "development": {
                    "label": "Development",
                    "release_kind": "development",
                    "tag": "latest",
                    "asset_patterns": [r"^BOOT\.ELF$"],
                    "fallback_version_prefix": "dev",
                }
            },
        }
        option = FakeResolver(payload).resolve_options(app)[0]
        self.assertEqual(option.version, "dev-2026-09-03")


if __name__ == "__main__":
    unittest.main()


class DirectReleaseResolverTests(unittest.TestCase):
    def test_direct_source_does_not_need_github_api(self):
        app = {
            "id": "libretro-fceumm",
            "name": "Libretro: FCEUmm",
            "source_type": "direct",
            "source_url": "https://buildbot.libretro.com/",
            "channels": {
                "nightly": {
                    "label": "Nightly / latest",
                    "version": "nightly-latest",
                    "url": "https://example.invalid/fceumm.zip",
                    "asset_name": "fceumm_libretro_ps2.elf.zip",
                    "archive_type": "zip",
                    "prerelease": True,
                }
            },
        }
        resolver = GitHubReleaseResolver()
        options = resolver.resolve_options(app)
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].channel, "nightly")
        self.assertEqual(options[0].version, "nightly-latest")
        self.assertEqual(options[0].asset_name, "fceumm_libretro_ps2.elf.zip")

    def test_manual_source_returns_no_release_options(self):
        resolver = GitHubReleaseResolver()
        self.assertEqual(
            resolver.resolve_options({"id": "pgen", "name": "PGEN", "source_type": "manual"}),
            [],
        )
