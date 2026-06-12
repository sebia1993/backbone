from __future__ import annotations

from datetime import datetime
import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.models import CommandResult, Device
from backbone_state_tracker.core.snapshot import SnapshotStore
from backbone_state_tracker.core.workflow import (
    BB3_OFF_STAGE,
    PRE_WORK_STAGE,
    build_snapshot_folder_label,
    default_stage_label,
    find_latest_pre_work_snapshot,
    resolve_stage,
)


class WorkflowTests(unittest.TestCase):
    def _snapshot(self, root: Path, stage_name: str, stage_slug: str, folder_label: str | None = None) -> Path:
        store = SnapshotStore(root)
        device = Device(name="backbone4", host="192.0.2.4")
        result = CommandResult(
            device_name=device.name,
            host=device.host,
            command_id="interface_brief",
            command="display interface brief",
            category="interface",
            phase="check",
            success=True,
            output="GE1/0/1 UP",
            started_at="2026-06-11T10:00:00",
            ended_at="2026-06-11T10:00:01",
        )
        return store.write_snapshot(
            stage_name,
            [device],
            {device.name: [result]},
            folder_label=folder_label or stage_slug,
            stage_name=stage_name,
            stage_slug=stage_slug,
        )

    def test_stage_resolution_uses_stable_slug(self) -> None:
        stage = resolve_stage(BB3_OFF_STAGE, "OFF 중 점검")

        self.assertEqual(stage.name, "OFF 중 점검")
        self.assertEqual(stage.slug, "bb3_off")
        self.assertTrue(stage.auto_compare)
        self.assertEqual(build_snapshot_folder_label(stage), "OFF 중 점검")

    def test_pre_work_stage_does_not_auto_compare(self) -> None:
        stage = resolve_stage(PRE_WORK_STAGE, "작업 전 기준")

        self.assertEqual(stage.name, "작업 전 기준")
        self.assertEqual(stage.slug, "pre_work")
        self.assertFalse(stage.auto_compare)

    def test_empty_stage_label_defaults_to_check_time(self) -> None:
        moment = datetime(2026, 6, 12, 21, 30, 45)

        stage = resolve_stage(PRE_WORK_STAGE, "", moment)

        self.assertEqual(default_stage_label(moment), "점검시간_20260612_2130")
        self.assertEqual(stage.name, "점검시간_20260612_2130")
        self.assertEqual(stage.slug, "pre_work")

    def test_find_latest_pre_work_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self._snapshot(root, PRE_WORK_STAGE, "pre_work", "pre_work_a")
            self._snapshot(root, BB3_OFF_STAGE, "bb3_off", "bb3_off")
            second = self._snapshot(root, PRE_WORK_STAGE, "pre_work", "pre_work_b")

            latest = find_latest_pre_work_snapshot([first, second])

        self.assertIsNotNone(latest)
        self.assertEqual(latest.name, second.name)


if __name__ == "__main__":
    unittest.main()
