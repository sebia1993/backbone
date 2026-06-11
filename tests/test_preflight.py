from __future__ import annotations

import unittest

from backbone_state_tracker.core.models import CommandSpec, Device
from backbone_state_tracker.core.preflight import preflight_summary_text, validate_preflight


class PreflightTests(unittest.TestCase):
    def test_valid_read_only_config_has_no_errors(self) -> None:
        result = validate_preflight(
            [
                Device(name="backbone3", host="10.0.0.3"),
                Device(name="backbone4", host="10.0.0.4"),
            ],
            [
                CommandSpec(id="disable_paging", command="screen-length disable", phase="setup"),
                CommandSpec(id="interface_brief", command="display interface brief", phase="check"),
            ],
        )

        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.warning_count, 0)
        self.assertIn("통과", preflight_summary_text(result))

    def test_duplicate_device_names_are_errors(self) -> None:
        result = validate_preflight(
            [
                Device(name="backbone", host="10.0.0.3"),
                Device(name="backbone", host="10.0.0.4"),
            ],
            [CommandSpec(id="clock", command="display clock", phase="check")],
        )

        self.assertTrue(result.has_errors)
        self.assertTrue(any("중복" in issue.message for issue in result.issues))

    def test_dangerous_commands_are_errors(self) -> None:
        result = validate_preflight(
            [
                Device(name="backbone3", host="10.0.0.3"),
                Device(name="backbone4", host="10.0.0.4"),
            ],
            [
                CommandSpec(id="bad_shutdown", command="shutdown", phase="check"),
                CommandSpec(id="bad_system_view", command="system-view", phase="setup"),
            ],
        )

        self.assertGreaterEqual(result.error_count, 2)
        self.assertTrue(any("변경성" in issue.message for issue in result.issues))

    def test_documentation_hosts_warn_but_do_not_block(self) -> None:
        result = validate_preflight(
            [
                Device(name="backbone3", host="192.0.2.3"),
                Device(name="backbone4", host="192.0.2.4"),
            ],
            [CommandSpec(id="clock", command="display clock", phase="check")],
        )

        self.assertEqual(result.error_count, 0)
        self.assertGreaterEqual(result.warning_count, 1)
        self.assertTrue(any("예시용 주소" in issue.message for issue in result.issues))

    def test_duplicate_command_ids_are_errors(self) -> None:
        result = validate_preflight(
            [
                Device(name="backbone3", host="10.0.0.3"),
                Device(name="backbone4", host="10.0.0.4"),
            ],
            [
                CommandSpec(id="clock", command="display clock", phase="check"),
                CommandSpec(id="clock", command="display version", phase="check"),
            ],
        )

        self.assertTrue(result.has_errors)
        self.assertTrue(any("명령 ID가 중복" in issue.message for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
