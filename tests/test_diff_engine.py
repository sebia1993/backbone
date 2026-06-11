from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.diff_engine import DiffEngine
from backbone_state_tracker.core.models import CommandResult, Device
from backbone_state_tracker.core.snapshot import SnapshotStore


class DiffEngineTests(unittest.TestCase):
    def _snapshot(self, root: Path, label: str, output: str, command_id: str = "interface_brief") -> Path:
        store = SnapshotStore(root)
        device = Device(name="backbone4", host="192.0.2.4")
        result = CommandResult(
            device_name=device.name,
            host=device.host,
            command_id=command_id,
            command="display interface brief",
            description="Interface summary",
            category="interface",
            phase="check",
            success=True,
            output=output,
            started_at="2026-06-11T10:00:00",
            ended_at="2026-06-11T10:00:01",
        )
        return store.write_snapshot(label, [device], {device.name: [result]})

    def test_ignores_clock_like_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(root, "base", "Current time is 10:00:00\nGE1/0/1 UP")
            target = self._snapshot(root, "target", "Current time is 10:30:00\nGE1/0/1 UP")

            summary = DiffEngine().compare(base, target)

        self.assertEqual(summary.counts["Unchanged"], 1)
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


if __name__ == "__main__":
    unittest.main()

