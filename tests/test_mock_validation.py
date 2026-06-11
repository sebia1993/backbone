from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.connectivity import DEVICE_CONNECTIVITY_COMMAND_ID
from backbone_state_tracker.core.mock_validation import create_mock_validation_artifacts
from backbone_state_tracker.core.snapshot import SnapshotStore


class MockValidationTests(unittest.TestCase):
    def test_create_mock_validation_artifacts_generates_snapshots_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))

            result = create_mock_validation_artifacts(store)

            self.assertTrue((result.pre_snapshot / "snapshot.json").exists())
            self.assertTrue((result.off_snapshot / "snapshot.json").exists())
            self.assertTrue((result.restore_snapshot / "snapshot.json").exists())
            self.assertTrue(result.off_report.exists())
            self.assertTrue(result.restore_report.exists())
            self.assertTrue(result.restore_from_off_report.exists())
            self.assertTrue(result.off_share_zip.exists())
            self.assertTrue(result.restore_share_zip.exists())
            self.assertTrue(result.restore_from_off_share_zip.exists())

            self.assertGreaterEqual(result.off_summary.counts["Critical"], 1)
            failed = [
                item
                for item in result.off_summary.items
                if item.command_id == DEVICE_CONNECTIVITY_COMMAND_ID and item.severity == "Critical"
            ]
            self.assertEqual(len(failed), 1)
            self.assertEqual(failed[0].device_name, "backbone3")

            restored = [
                item
                for item in result.restore_from_off_summary.items
                if item.command_id == DEVICE_CONNECTIVITY_COMMAND_ID and item.severity == "Info"
            ]
            self.assertEqual(len(restored), 1)
            self.assertEqual(restored[0].device_name, "backbone3")

    def test_mock_validation_repeated_runs_keep_snapshots_separate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))

            first = create_mock_validation_artifacts(store)
            second = create_mock_validation_artifacts(store)

            self.assertNotEqual(first.pre_snapshot, second.pre_snapshot)
            self.assertNotEqual(first.off_snapshot, second.off_snapshot)
            self.assertNotEqual(first.restore_snapshot, second.restore_snapshot)


if __name__ == "__main__":
    unittest.main()
