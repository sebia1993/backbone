from __future__ import annotations

import socket
import unittest
from pathlib import Path

from backbone_state_tracker.core.mockserver.profiles import load_mock_profile
from backbone_state_tracker.core.mockserver.telnet_server import TelnetMockServer


PROJECT_DIR = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_DIR / "config" / "mock_profiles.yaml"


def recv_until(sock: socket.socket, marker: bytes) -> bytes:
    chunks: list[bytes] = []
    while marker not in b"".join(chunks):
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


class MockTelnetServerTests(unittest.TestCase):
    def test_telnet_server_accepts_login_and_returns_command_response(self) -> None:
        profile = load_mock_profile(PROFILE_PATH, "normal")
        with TelnetMockServer(profile) as server:
            with socket.create_connection(server.address, timeout=5) as sock:
                sock.settimeout(5)
                self.assertIn(b"Username:", recv_until(sock, b"Username:"))
                sock.sendall((profile.username + "\n").encode("utf-8"))
                self.assertIn(b"Password:", recv_until(sock, b"Password:"))
                sock.sendall((profile.password + "\n").encode("utf-8"))
                self.assertIn(profile.prompt.encode("utf-8"), recv_until(sock, profile.prompt.encode("utf-8")))
                sock.sendall(b"display clock\n")
                payload = recv_until(sock, profile.prompt.encode("utf-8"))

        self.assertIn(b"Mock clock", payload)

    def test_telnet_server_rejects_auth_failed_profile(self) -> None:
        profile = load_mock_profile(PROFILE_PATH, "auth_failed")
        with TelnetMockServer(profile) as server:
            with socket.create_connection(server.address, timeout=5) as sock:
                sock.settimeout(5)
                recv_until(sock, b"Username:")
                sock.sendall((profile.username + "\n").encode("utf-8"))
                recv_until(sock, b"Password:")
                sock.sendall((profile.password + "\n").encode("utf-8"))
                payload = recv_until(sock, b"failed")

        self.assertIn(b"Authentication failed", payload)


if __name__ == "__main__":
    unittest.main()
