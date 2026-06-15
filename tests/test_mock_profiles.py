from __future__ import annotations

import unittest
from pathlib import Path

from backbone_state_tracker.core.mockserver.profiles import MockProfileError, load_mock_profile, load_mock_profiles


PROJECT_DIR = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_DIR / "config" / "mock_profiles.yaml"


class MockProfileTests(unittest.TestCase):
    def test_loads_normal_profile_with_required_command_responses(self) -> None:
        profile = load_mock_profile(PROFILE_PATH, "normal")

        self.assertEqual("normal", profile.name)
        self.assertIn("Mock clock", profile.response_for("display clock"))
        self.assertIn("VRID 10", profile.response_for("show vrrp"))
        self.assertIn("Mock response", profile.response_for("display unknown-command"))

    def test_profile_inheritance_overrides_only_changed_commands(self) -> None:
        normal = load_mock_profile(PROFILE_PATH, "normal")
        vrrp = load_mock_profile(PROFILE_PATH, "vrrp_role_change")

        self.assertIn("State Master", normal.response_for("show vrrp"))
        self.assertIn("State Backup", vrrp.response_for("show vrrp"))
        self.assertEqual(normal.response_for("display clock"), vrrp.response_for("display clock"))

    def test_missing_profile_raises_actionable_diagnostic_code(self) -> None:
        with self.assertRaises(MockProfileError) as context:
            load_mock_profile(PROFILE_PATH, "missing")

        self.assertEqual("BST-MOCK-801", context.exception.code)

    def test_all_profiles_avoid_forbidden_realistic_sensitive_values(self) -> None:
        profiles = load_mock_profiles(PROFILE_PATH)
        forbidden_fragments = ["password=", "Authorization:", "snmp-server community", "10.10.", ".internal"]

        combined = "\n".join(
            "\n".join(profile.commands.values()) for profile in profiles.values()
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, combined)


if __name__ == "__main__":
    unittest.main()
