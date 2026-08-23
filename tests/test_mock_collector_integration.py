from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.collector import (
    SnapshotCollector,
    format_command_failure_message,
)
from backbone_state_tracker.core.mockserver.profiles import load_mock_profile
from backbone_state_tracker.core.mockserver.ssh_server import SshMockServer
from backbone_state_tracker.core.models import CommandSpec, Device

PROJECT_DIR = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_DIR / "config" / "mock_profiles.yaml"


class MockCollectorIntegrationTests(unittest.TestCase):
    def test_snapshot_collector_can_collect_from_mock_ssh_server(self) -> None:
        profile = load_mock_profile(PROFILE_PATH, "normal")
        with SshMockServer(profile) as server:
            device = Device(
                name="mock-device-a",
                host=server.host,
                port=server.port,
                device_type="hp_comware",
            )
            commands = [CommandSpec(id="system_clock", command="display clock", timeout=10)]

            with tempfile.TemporaryDirectory() as temp_dir:
                known_hosts = Path(temp_dir) / "known_hosts"
                known_hosts.write_text(
                    f"{server.known_hosts_name} {server.host_key.get_name()} {server.host_key.get_base64()}\n",
                    encoding="utf-8",
                )
                results = SnapshotCollector(timeout=10, known_hosts_file=known_hosts).collect(
                    [device], commands, profile.username, profile.password
                )

        device_results = results["mock-device-a"]
        self.assertTrue(device_results[0].success)
        self.assertEqual("device_connectivity", device_results[0].command_id)
        self.assertTrue(device_results[1].success)
        self.assertEqual("system_clock", device_results[1].command_id)
        self.assertIn("Mock clock", device_results[1].output)

    def test_changed_host_key_is_security_failure_and_runs_no_command(self) -> None:
        import paramiko

        profile = load_mock_profile(PROFILE_PATH, "normal")
        progress: list[str] = []
        with SshMockServer(profile) as server:
            device = Device(
                name="mock-device-a",
                host=server.host,
                port=server.port,
                device_type="hp_comware",
            )
            commands = [CommandSpec(id="system_clock", command="display clock", timeout=3)]
            wrong_key = paramiko.ECDSAKey.generate(bits=256)
            with tempfile.TemporaryDirectory() as temp_dir:
                known_hosts = Path(temp_dir) / "known_hosts"
                known_hosts.write_text(
                    f"{server.known_hosts_name} {wrong_key.get_name()} {wrong_key.get_base64()}\n",
                    encoding="utf-8",
                )
                results = SnapshotCollector(
                    timeout=3,
                    progress=progress.append,
                    known_hosts_file=known_hosts,
                ).collect([device], commands, profile.username, profile.password)

        device_results = results["mock-device-a"]
        self.assertEqual(len(device_results), 1)
        self.assertEqual(device_results[0].command_id, "device_connectivity")
        self.assertFalse(device_results[0].success)
        self.assertIn("BST-SEC-002", device_results[0].error_message)
        self.assertTrue(any("BST-SEC-002" in message for message in progress))

    def test_command_failure_message_includes_diagnostic_code_and_redacts_secret(self) -> None:
        message = format_command_failure_message(TimeoutError("read timeout password=UltraSecret"))

        self.assertIn("BST-COL-401", message)
        self.assertIn("명령 응답 시간이 초과", message)
        self.assertNotIn("UltraSecret", message)
        self.assertIn("***", message)


if __name__ == "__main__":
    unittest.main()
