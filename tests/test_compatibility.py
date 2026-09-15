from __future__ import annotations

import unittest

from src.compatibility import check_compatibility


class CompatibilityTests(unittest.TestCase):
    def test_popsloader_with_opl_warns(self) -> None:
        plan = {
            "language": "pt-BR",
            "homebrews": [{"id": "opl", "resolved": {"channel": "prerelease", "version": "v1.2.0-Beta-2165"}}, {"id": "popsloader"}],
            "storage": {"id": "usb"},
            "boot": {"id": "existing"},
        }
        findings = check_compatibility(plan)
        rules = {item["rule"] for item in findings}
        self.assertIn("opl-popsloader-apps", rules)

    def test_popsloader_does_not_warn_for_opl_110_from_beta_specific_rule(self) -> None:
        plan = {
            "language": "pt-BR",
            "homebrews": [
                {"id": "opl", "resolved": {"channel": "stable", "version": "v1.1.0"}},
                {"id": "popsloader"},
            ],
            "storage": {"id": "usb"},
            "boot": {"id": "existing"},
        }
        rules = {item["rule"] for item in check_compatibility(plan)}
        self.assertNotIn("opl-popsloader-apps", rules)

    def test_nhddl_without_neutrino_warns(self) -> None:
        plan = {
            "language": "en",
            "homebrews": [{"id": "nhddl"}],
            "storage": {"id": "usb"},
        }
        findings = check_compatibility(plan)
        self.assertIn("nhddl-neutrino", {item["rule"] for item in findings})

    def test_destructive_manual_tools_emit_safety_warnings(self) -> None:
        plan = {
            "language": "en",
            "homebrews": [
                {"id": "mechapwn"},
                {"id": "memory-card-annihilator"},
                {"id": "hddchecker"},
                {"id": "opentuna-installer"},
                {"id": "hdlgameinstaller"},
            ],
            "storage": {"id": "usb"},
            "boot": {"id": "existing"},
        }
        rules = {item["rule"] for item in check_compatibility(plan)}
        self.assertIn("mechapwn-hardware-config", rules)
        self.assertIn("memory-card-annihilator-destructive", rules)
        self.assertIn("hddchecker-destructive", rules)
        self.assertIn("opentuna-installer-card-changes", rules)
        self.assertIn("hdlgameinstaller-apaext", rules)

    def test_hdd_exfat_and_system_update_emit_separate_findings(self) -> None:
        plan = {
            "language": "en",
            "homebrews": [],
            "storage": {"id": "hdd-exfat"},
            "boot": {"id": "system-update"},
        }
        rules = {item["rule"] for item in check_compatibility(plan)}
        self.assertIn("ps2bbl-exfat-r1", rules)
        self.assertIn("system-update-model-compat", rules)


if __name__ == "__main__":
    unittest.main()
