from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.connectivity import DEVICE_CONNECTIVITY_COMMAND_ID, make_connectivity_result_for_device
from backbone_state_tracker.core.diff_engine import DiffEngine
from backbone_state_tracker.core.models import CommandResult, Device
from backbone_state_tracker.core.snapshot import SnapshotStore


class DiffEngineTests(unittest.TestCase):
    def _snapshot(self, root: Path, label: str, output: str, command_id: str = "interface_brief", category: str = "interface") -> Path:
        store = SnapshotStore(root)
        device = Device(name="backbone4", host="192.0.2.4")
        result = self._command_result(device, command_id=command_id, output=output, category=category)
        return store.write_snapshot(label, [device], {device.name: [result]})

    def _command_result(
        self,
        device: Device,
        command_id: str = "interface_brief",
        output: str = "GE1/0/1 UP",
        category: str = "interface",
    ) -> CommandResult:
        return CommandResult(
            device_name=device.name,
            host=device.host,
            command_id=command_id,
            command="display interface brief",
            description="Interface summary",
            category=category,
            phase="check",
            success=True,
            output=output,
            started_at="2026-06-11T10:00:00",
            ended_at="2026-06-11T10:00:01",
        )

    def test_ignores_clock_like_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(root, "base", "Current time is 10:00:00\nGE1/0/1 UP")
            target = self._snapshot(root, "target", "Current time is 10:30:00\nGE1/0/1 UP")

            summary = DiffEngine().compare(base, target)

        self.assertEqual(summary.counts["Unchanged"], 2)
        self.assertEqual(summary.counts["Critical"], 0)

    def test_interface_down_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(root, "base", "GE1/0/1 UP\nGE1/0/2 UP")
            target = self._snapshot(root, "target", "GE1/0/1 DOWN\nGE1/0/2 UP")

            summary = DiffEngine().compare(base, target)

        changed = [item for item in summary.items if item.status == "changed"]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0].severity, "Critical")

    def test_lacp_selected_count_decrease_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(root, "base", "Aggregation1 selected ports: 4", command_id="link_aggregation_summary")
            target = self._snapshot(root, "target", "Aggregation1 selected ports: 2", command_id="link_aggregation_summary")

            summary = DiffEngine().compare(base, target)

        changed = [item for item in summary.items if item.status == "changed"]
        self.assertEqual(changed[0].severity, "Critical")

    def test_hardware_major_alarm_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(root, "base", "No alarm", command_id="alarm_status", category="hardware")
            target = self._snapshot(root, "target", "Major alarm: power failure", command_id="alarm_status", category="hardware")

            summary = DiffEngine().compare(base, target)

        changed = [item for item in summary.items if item.status == "changed"]
        self.assertEqual(changed[0].severity, "Critical")

    def test_minor_alarm_in_log_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            device = Device(name="backbone4", host="192.0.2.4")
            store = SnapshotStore(root)
            base = store.write_snapshot(
                "base",
                [device],
                {device.name: [self._command_result(device, command_id="recent_log", output="No alarm", category="log")]},
            )
            target = store.write_snapshot(
                "target",
                [device],
                {device.name: [self._command_result(device, command_id="recent_log", output="Minor alarm: fan speed changed", category="log")]},
            )

            summary = DiffEngine().compare(base, target)

        changed = [item for item in summary.items if item.status == "changed"]
        self.assertEqual(changed[0].severity, "Warning")

    def test_changed_lines_include_before_after_values_and_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(root, "base", "Header\nGE1/0/1 UP\nGE1/0/2 UP")
            target = self._snapshot(root, "target", "Header\nGE1/0/1 DOWN\nGE1/0/2 UP")

            summary = DiffEngine().compare(base, target)

        item = next(item for item in summary.items if item.status == "changed")
        change_lines = [line for line in item.changed_lines if line.kind != "context"]
        self.assertEqual(item.change_count, 1)
        self.assertEqual(change_lines[0].kind, "changed")
        self.assertEqual(change_lines[0].base_line_no, 2)
        self.assertEqual(change_lines[0].target_line_no, 2)
        self.assertEqual(change_lines[0].base_text, "GE1/0/1 UP")
        self.assertEqual(change_lines[0].target_text, "GE1/0/1 DOWN")
        self.assertIn("GE1/0/1 UP -> GE1/0/1 DOWN", item.change_preview)

    def test_added_and_removed_lines_are_classified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(root, "base", "A\nC")
            target = self._snapshot(root, "target", "A\nB\nC")
            added = DiffEngine().compare(base, target)

            base_removed = self._snapshot(root, "base_removed", "A\nB\nC", command_id="interface_brief_removed")
            target_removed = self._snapshot(root, "target_removed", "A\nC", command_id="interface_brief_removed")
            removed = DiffEngine().compare(base_removed, target_removed)

        added_item = next(item for item in added.items if item.status == "changed")
        added_lines = [line for line in added_item.changed_lines if line.kind != "context"]
        self.assertEqual(added_lines[0].kind, "added")
        self.assertEqual(added_lines[0].target_line_no, 2)
        self.assertEqual(added_lines[0].target_text, "B")

        removed_item = next(item for item in removed.items if item.status == "changed")
        removed_lines = [line for line in removed_item.changed_lines if line.kind != "context"]
        self.assertEqual(removed_lines[0].kind, "removed")
        self.assertEqual(removed_lines[0].base_line_no, 2)
        self.assertEqual(removed_lines[0].base_text, "B")

    def test_unreachable_target_device_is_single_critical_connectivity_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SnapshotStore(root)
            device = Device(name="backbone3", host="192.0.2.3")
            base = store.write_snapshot(
                "base",
                [device],
                {device.name: [self._command_result(device, output="GE1/0/1 UP")]},
            )
            target = store.write_snapshot(
                "target",
                [device],
                {
                    device.name: [
                        make_connectivity_result_for_device(
                            device_name=device.name,
                            host=device.host,
                            success=False,
                            reason="timeout",
                            started_at="2026-06-11T10:05:00",
                            ended_at="2026-06-11T10:05:00",
                        )
                    ]
                },
            )

            summary = DiffEngine().compare(base, target)

        connectivity = next(item for item in summary.items if item.command_id == DEVICE_CONNECTIVITY_COMMAND_ID)
        self.assertEqual(connectivity.severity, "Critical")
        self.assertEqual(connectivity.summary, "Target device connection failed.")
        self.assertEqual(connectivity.change_count, 1)
        self.assertEqual(connectivity.changed_lines[0].base_text, "reachable")
        self.assertEqual(connectivity.changed_lines[0].target_text, "unreachable: timeout")
        self.assertFalse(any(item.command_id == "interface_brief" and item.status == "removed" for item in summary.items))

    def test_restored_target_device_is_info_without_added_command_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SnapshotStore(root)
            device = Device(name="backbone3", host="192.0.2.3")
            base = store.write_snapshot(
                "base",
                [device],
                {
                    device.name: [
                        make_connectivity_result_for_device(
                            device_name=device.name,
                            host=device.host,
                            success=False,
                            reason="timeout",
                            started_at="2026-06-11T10:00:00",
                            ended_at="2026-06-11T10:00:00",
                        )
                    ]
                },
            )
            target = store.write_snapshot(
                "target",
                [device],
                {device.name: [self._command_result(device, output="GE1/0/1 UP")]},
            )

            summary = DiffEngine().compare(base, target)

        connectivity = next(item for item in summary.items if item.command_id == DEVICE_CONNECTIVITY_COMMAND_ID)
        self.assertEqual(connectivity.severity, "Info")
        self.assertEqual(connectivity.summary, "Target device connection restored.")
        self.assertEqual(connectivity.changed_lines[0].base_text, "unreachable: timeout")
        self.assertEqual(connectivity.changed_lines[0].target_text, "reachable")
        self.assertFalse(any(item.command_id == "interface_brief" and item.status == "added" for item in summary.items))

    def test_still_unreachable_target_device_remains_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SnapshotStore(root)
            device = Device(name="backbone3", host="192.0.2.3")
            failure = lambda: make_connectivity_result_for_device(
                device_name=device.name,
                host=device.host,
                success=False,
                reason="timeout",
                started_at="2026-06-11T10:00:00",
                ended_at="2026-06-11T10:00:00",
            )
            base = store.write_snapshot("base", [device], {device.name: [failure()]})
            target = store.write_snapshot("target", [device], {device.name: [failure()]})

            summary = DiffEngine().compare(base, target)

        connectivity = next(item for item in summary.items if item.command_id == DEVICE_CONNECTIVITY_COMMAND_ID)
        self.assertEqual(connectivity.severity, "Critical")
        self.assertEqual(connectivity.summary, "Target device connection failed.")
        self.assertEqual(connectivity.change_count, 1)


if __name__ == "__main__":
    unittest.main()
