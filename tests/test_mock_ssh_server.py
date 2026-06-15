from __future__ import annotations

import unittest
from pathlib import Path

from backbone_state_tracker.core.mockserver.profiles import load_mock_profile
from backbone_state_tracker.core.mockserver.ssh_server import SshMockServer


PROJECT_DIR = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_DIR / "config" / "mock_profiles.yaml"


class MockSshServerTests(unittest.TestCase):
    def test_ssh_server_exec_command_returns_profile_response(self) -> None:
        try:
            import paramiko
        except ImportError:  # pragma: no cover
            self.skipTest("paramiko is not installed")

        profile = load_mock_profile(PROFILE_PATH, "normal")
        with SshMockServer(profile) as server:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    server.host,
                    port=server.port,
                    username=profile.username,
                    password=profile.password,
                    look_for_keys=False,
                    allow_agent=False,
                    timeout=5,
                    banner_timeout=5,
                    auth_timeout=5,
                )
                _stdin, stdout, _stderr = client.exec_command("show vrrp", timeout=5)
                payload = stdout.read().decode("utf-8", errors="replace")
            finally:
                client.close()

        self.assertIn("VRID 10", payload)
        self.assertIn("State Master", payload)


if __name__ == "__main__":
    unittest.main()
