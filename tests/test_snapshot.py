from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from backbone_state_tracker.core.models import CommandResult, Device
from backbone_state_tracker.core.snapshot import SnapshotStore, sanitize_filename


class SnapshotStoreTests(unittest.TestCase):
    def _result(self, device: Device, output: str = "Slot 1 Normal") -> CommandResult:
        return CommandResult(
            device_name=device.name,
            host=device.host,
            command_id="device_status",
            command="display device",
            category="hardware",
            phase="check",
            success=True,
            output=output,
            started_at="2026-06-11T10:00:00",
            ended_at="2026-06-11T10:00:01",
        )

    def test_write_and_load_snapshot_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SnapshotStore(root)
            device = Device(name="backbone3", host="192.0.2.3")
            result = self._result(device)

            snapshot_dir = store.write_snapshot("pre", [device], {device.name: [result]})
            loaded = SnapshotStore.load_snapshot(snapshot_dir)

            self.assertEqual(loaded.label, "pre")
            self.assertEqual(len(loaded.results), 1)
            raw_path = snapshot_dir / loaded.results[0].raw_file
            self.assertTrue(raw_path.exists())
            self.assertEqual(raw_path.read_text(encoding="utf-8"), "Slot 1 Normal")

    def test_write_snapshot_allocates_unique_folder_when_name_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SnapshotStore(root)
            device = Device(name="backbone3", host="192.0.2.3")
            fixed_now = datetime(2026, 6, 11, 10, 0, 0)

            with patch("backbone_state_tracker.core.snapshot.datetime") as fake_datetime:
                fake_datetime.now.return_value = fixed_now
                first = store.write_snapshot(
                    "pre",
                    [device],
                    {device.name: [self._result(device, "first")]},
                )
                second = store.write_snapshot(
                    "pre",
                    [device],
                    {device.name: [self._result(device, "second")]},
                )

            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertEqual(second.name, f"{first.name}_001")
            first_raw = first / "raw" / "backbone3" / "device_status.txt"
            second_raw = second / "raw" / "backbone3" / "device_status.txt"
            self.assertEqual(first_raw.read_text(encoding="utf-8"), "first")
            self.assertEqual(second_raw.read_text(encoding="utf-8"), "second")

    def test_sanitize_filename_preserves_korean_stage_label(self) -> None:
        self.assertEqual(sanitize_filename("점검시간_20260612_2130"), "점검시간_20260612_2130")


if __name__ == "__main__":
    unittest.main()
