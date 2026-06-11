from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.models import CommandResult, Device
from backbone_state_tracker.core.snapshot import SnapshotStore
from backbone_state_tracker.core.workflow import BB3_OFF_STAGE, POST_RESTORE_STAGE, PRE_WORK_STAGE
from backbone_state_tracker.core.workflow_wizard import (
    BB3_OFF_STEP,
    FINAL_REVIEW_STEP,
    OFF_REVIEW_STEP,
    POST_RESTORE_STEP,
    PRE_WORK_STEP,
    build_workflow_wizard_state,
)


class WorkflowWizardTests(unittest.TestCase):
    def _snapshot(self, root: Path, label: str, slug: str) -> Path:
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
        return store.write_snapshot(label, [device], {device.name: [result]}, folder_label=slug, stage_name=label, stage_slug=slug)

    def test_without_pre_work_next_action_collects_pre_work(self) -> None:
        state = build_workflow_wizard_state([], device_ready=True)

        self.assertEqual(state.active_step, PRE_WORK_STEP)
        self.assertEqual(state.next_action, "collect_pre")
        off_step = next(step for step in state.steps if step.key == BB3_OFF_STEP)
        self.assertEqual(off_step.status, "locked")

    def test_after_pre_work_next_action_collects_bb3_off(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pre = self._snapshot(Path(tmp), PRE_WORK_STAGE, "pre_work")

            state = build_workflow_wizard_state([pre], device_ready=True)

        self.assertEqual(state.active_step, BB3_OFF_STEP)
        self.assertEqual(state.next_action, "collect_off")

    def test_after_off_collection_requires_off_review_before_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pre = self._snapshot(root, PRE_WORK_STAGE, "pre_work")
            off = self._snapshot(root, BB3_OFF_STAGE, "bb3_off")

            state = build_workflow_wizard_state([pre, off], device_ready=True, latest_counts={"Critical": 1})

        self.assertEqual(state.active_step, OFF_REVIEW_STEP)
        self.assertEqual(state.next_action, "review_off")
        restore_step = next(step for step in state.steps if step.key == POST_RESTORE_STEP)
        self.assertEqual(restore_step.status, "locked")

    def test_after_off_review_next_action_collects_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pre = self._snapshot(root, PRE_WORK_STAGE, "pre_work")
            off = self._snapshot(root, BB3_OFF_STAGE, "bb3_off")

            state = build_workflow_wizard_state([pre, off], device_ready=True, off_review_confirmed=True)

        self.assertEqual(state.active_step, POST_RESTORE_STEP)
        self.assertEqual(state.next_action, "collect_restore")

    def test_after_restore_next_action_final_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pre = self._snapshot(root, PRE_WORK_STAGE, "pre_work")
            off = self._snapshot(root, BB3_OFF_STAGE, "bb3_off")
            restore = self._snapshot(root, POST_RESTORE_STAGE, "post_restore")

            state = build_workflow_wizard_state(
                [pre, off, restore],
                device_ready=True,
                off_review_confirmed=True,
                final_review_confirmed=False,
            )

        self.assertEqual(state.active_step, FINAL_REVIEW_STEP)
        self.assertEqual(state.next_action, "review_final")


if __name__ == "__main__":
    unittest.main()
