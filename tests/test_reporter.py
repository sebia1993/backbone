from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.diff_engine import DiffEngine
from backbone_state_tracker.core.models import CommandResult, Device
from backbone_state_tracker.core.reporter import ReportWriter
from backbone_state_tracker.core.snapshot import SnapshotStore


class ReportWriterTests(unittest.TestCase):
    def _snapshot(self, root: Path, label: str, output: str) -> Path:
        store = SnapshotStore(root)
        device = Device(name="backbone4", host="192.0.2.4")
        result = CommandResult(
            device_name=device.name,
            host=device.host,
            command_id="interface_brief",
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

    def test_html_and_xlsx_include_line_level_diff_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(root, "base", "GE1/0/1 UP\nGE1/0/2 UP")
            target = self._snapshot(root, "target", "GE1/0/1 DOWN\nGE1/0/2 UP")
            summary = DiffEngine().compare(base, target)

            paths = ReportWriter().write_reports(summary)

            html = paths["html"].read_text(encoding="utf-8")
            self.assertIn("변경 내용", html)
            self.assertIn("change-inline", html)
            self.assertIn("1 → 1", html)
            self.assertIn("GE1/0/1 UP</span><span class='diff-arrow'>→</span><span class='value-after'>GE1/0/1 DOWN", html)
            self.assertNotIn("<th>변경 전</th>", html)
            self.assertNotIn("<th>변경 후</th>", html)
            self.assertIn("GE1/0/1 UP", html)
            self.assertIn("GE1/0/1 DOWN", html)

            if "xlsx" not in paths:
                self.skipTest("openpyxl is not installed")

            from openpyxl import load_workbook

            workbook = load_workbook(paths["xlsx"])
            self.assertIn("diff_detail", workbook.sheetnames)
            detail_sheet = workbook["diff_detail"]
            rows = list(detail_sheet.iter_rows(values_only=True))
            self.assertIn("base_text", rows[0])
            self.assertTrue(any("GE1/0/1 UP" in row for row in rows[1:]))
            self.assertTrue(any("GE1/0/1 DOWN" in row for row in rows[1:]))


if __name__ == "__main__":
    unittest.main()
