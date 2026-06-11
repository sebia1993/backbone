from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.models import CommandResult, Device
from backbone_state_tracker.core.snapshot import SnapshotStore


class SnapshotStoreTests(unittest.TestCase):
    def test_write_and_load_snapshot_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SnapshotStore(root)
            device = Device(name="backbone3", host="192.0.2.3")
            result = CommandResult(
                device_name=device.name,
                host=device.host,
                command_id="device_status",
                command="display device",
                category="hardware",
                phase="check",
                success=True,
                output="Slot 1 Normal",
                started_at="2026-06-11T10:00:00",
                ended_at="2026-06-11T10:00:01",
            )

            snapshot_dir = store.write_snapshot("pre", [device], {device.name: [result]})
            loaded = SnapshotStore.load_snapshot(snapshot_dir)

            self.assertEqual(loaded.label, "pre")
            self.assertEqual(len(loaded.results), 1)
            raw_path = snapshot_dir / loaded.results[0].raw_file
            self.assertTrue(raw_path.exists())
            self.assertEqual(raw_path.read_text(encoding="utf-8"), "Slot 1 Normal")


if __name__ == "__main__":
    unittest.main()

