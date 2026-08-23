from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import paramiko
from backbone_state_tracker.core.collector import CollectionError, SnapshotCollector
from backbone_state_tracker.core.command_safety import (
    CommandSafetyError,
    canonicalize_command,
)
from backbone_state_tracker.core.models import CommandSpec, Device


class _FakeConnection:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.disconnected = False

    def send_command_timing(self, *, command_string: str, **_kwargs: object) -> str:
        self.commands.append(command_string)
        return "safe output"

    def disconnect(self) -> None:
        self.disconnected = True


def _write_valid_known_hosts(path: Path) -> None:
    key = paramiko.ECDSAKey.generate(bits=256)
    path.write_text(f"example {key.get_name()} {key.get_base64()}\n", encoding="utf-8")


class CollectionSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.device = Device(name="backbone3", host="192.0.2.3", device_type="hp_comware")

    def test_canonicalization_rejects_control_unicode_and_command_chaining(self) -> None:
        unsafe = (
            "display clock\nsystem-view",
            "display clock | include up",
            "display clock；reboot",
            "display 상태",
            "save",
        )
        for command in unsafe:
            with self.subTest(command=command), self.assertRaises(CommandSafetyError):
                canonicalize_command(command)

    def test_unsafe_command_blocks_before_connect_handler(self) -> None:
        connect_handler = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            known_hosts = Path(temp_dir) / "known_hosts"
            _write_valid_known_hosts(known_hosts)
            with patch("netmiko.ConnectHandler", connect_handler):
                with self.assertRaisesRegex(CollectionError, "BST-SEC-001"):
                    SnapshotCollector(known_hosts_file=known_hosts).collect(
                        [self.device],
                        [CommandSpec(id="unsafe", command="display clock; reboot")],
                        "operator",
                        "secret",
                    )
        connect_handler.assert_not_called()

    def test_comments_only_known_hosts_blocks_before_connect_handler(self) -> None:
        connect_handler = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            known_hosts = Path(temp_dir) / "known_hosts"
            known_hosts.write_text("# fingerprints must be approved out of band\n\n", encoding="utf-8")
            with patch("netmiko.ConnectHandler", connect_handler):
                with self.assertRaisesRegex(CollectionError, "호스트 키 엔트리가 없습니다"):
                    SnapshotCollector(known_hosts_file=known_hosts).collect(
                        [self.device],
                        [CommandSpec(id="clock", command="display clock")],
                        "operator",
                        "secret",
                    )
        connect_handler.assert_not_called()

    def test_malformed_known_hosts_blocks_before_connect_handler(self) -> None:
        connect_handler = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            known_hosts = Path(temp_dir) / "known_hosts"
            known_hosts.write_text("example ssh-ed25519 not-base64!\n", encoding="utf-8")
            with patch("netmiko.ConnectHandler", connect_handler):
                with self.assertRaisesRegex(CollectionError, "호스트 키 파일을 해석할 수 없습니다"):
                    SnapshotCollector(known_hosts_file=known_hosts).collect(
                        [self.device],
                        [CommandSpec(id="clock", command="display clock")],
                        "operator",
                        "secret",
                    )
        connect_handler.assert_not_called()

    def test_mixed_valid_and_silently_skippable_known_hosts_line_blocks_before_connect_handler(self) -> None:
        for malformed_line in ("broken-line", "example unknown-key-type AAAA"):
            with self.subTest(malformed_line=malformed_line):
                connect_handler = Mock()
                with tempfile.TemporaryDirectory() as temp_dir:
                    known_hosts = Path(temp_dir) / "known_hosts"
                    _write_valid_known_hosts(known_hosts)
                    with known_hosts.open("a", encoding="utf-8") as handle:
                        handle.write(f"{malformed_line}\n")
                    with patch("netmiko.ConnectHandler", connect_handler):
                        with self.assertRaisesRegex(CollectionError, "올바른 known_hosts 엔트리가 아닙니다"):
                            SnapshotCollector(known_hosts_file=known_hosts).collect(
                                [self.device],
                                [CommandSpec(id="clock", command="display clock")],
                                "operator",
                                "secret",
                            )
                connect_handler.assert_not_called()

    def test_valid_base64_with_invalid_key_blob_is_wrapped_and_blocks_before_connect_handler(self) -> None:
        connect_handler = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            known_hosts = Path(temp_dir) / "known_hosts"
            _write_valid_known_hosts(known_hosts)
            with known_hosts.open("a", encoding="utf-8") as handle:
                handle.write("example ssh-ed25519 AAAA\n")
            with patch("netmiko.ConnectHandler", connect_handler):
                with self.assertRaisesRegex(CollectionError, "호스트 키 파일을 해석할 수 없습니다"):
                    SnapshotCollector(known_hosts_file=known_hosts).collect(
                        [self.device],
                        [CommandSpec(id="clock", command="display clock")],
                        "operator",
                        "secret",
                    )
        connect_handler.assert_not_called()

    def test_missing_known_hosts_blocks_before_connect_handler(self) -> None:
        connect_handler = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing-known-hosts"
            with patch("netmiko.ConnectHandler", connect_handler):
                with self.assertRaisesRegex(CollectionError, "호스트 키 파일이 없습니다"):
                    SnapshotCollector(known_hosts_file=missing).collect(
                        [self.device],
                        [CommandSpec(id="clock", command="display clock")],
                        "operator",
                        "secret",
                    )
        connect_handler.assert_not_called()

    def test_telnet_device_type_is_rejected_before_connect_handler(self) -> None:
        connect_handler = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            known_hosts = Path(temp_dir) / "known_hosts"
            _write_valid_known_hosts(known_hosts)
            telnet_device = Device(
                name="legacy",
                host="192.0.2.4",
                device_type="hp_comware_telnet",
            )
            with patch("netmiko.ConnectHandler", connect_handler):
                with self.assertRaisesRegex(CollectionError, "SSH 전용"):
                    SnapshotCollector(known_hosts_file=known_hosts).collect(
                        [telnet_device],
                        [CommandSpec(id="clock", command="display clock")],
                        "operator",
                        "secret",
                    )
        connect_handler.assert_not_called()

    def test_safe_command_is_canonicalized_and_strict_ssh_options_are_mandatory(self) -> None:
        connection = _FakeConnection()
        connect_handler = Mock(return_value=connection)
        with tempfile.TemporaryDirectory() as temp_dir:
            known_hosts = Path(temp_dir) / "known_hosts"
            _write_valid_known_hosts(known_hosts)
            with patch("netmiko.ConnectHandler", connect_handler):
                results = SnapshotCollector(known_hosts_file=known_hosts).collect(
                    [self.device],
                    [CommandSpec(id="clock", command="  display   clock  ")],
                    "operator",
                    "secret",
                )

        self.assertEqual(connection.commands, ["display clock"])
        self.assertTrue(connection.disconnected)
        self.assertTrue(results["backbone3"][1].success)
        options = connect_handler.call_args.kwargs
        self.assertEqual(options["device_type"], "hp_comware")
        self.assertIs(options["ssh_strict"], True)
        self.assertIs(options["system_host_keys"], False)
        self.assertIs(options["alt_host_keys"], True)
        self.assertEqual(options["alt_key_file"], str(known_hosts.resolve()))
        self.assertEqual(
            options["disabled_algorithms"],
            {"keys": ["ssh-rsa"], "pubkeys": ["ssh-rsa"]},
        )
        self.assertIs(options["use_keys"], False)
        self.assertIs(options["allow_agent"], False)


if __name__ == "__main__":
    unittest.main()
