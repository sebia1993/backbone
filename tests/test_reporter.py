from __future__ import annotations

import json
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

    def test_reports_redact_sensitive_values_but_keep_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self._snapshot(
                root,
                "base",
                "snmp-server community UltraSnmpSecret RO\npassword=OldSecret\nGE1/0/1 UP",
            )
            target = self._snapshot(
                root,
                "target",
                "snmp-server community UltraSnmpSecret RW\npassword=NewSecret\nGE1/0/1 DOWN",
            )
            summary = DiffEngine().compare(base, target)

            paths = ReportWriter().write_reports(summary)

            html = paths["html"].read_text(encoding="utf-8")
            manifest = json.loads(paths["json"].read_text(encoding="utf-8"))
            manifest_text = json.dumps(manifest, ensure_ascii=False)

            for secret in ("UltraSnmpSecret", "OldSecret", "NewSecret"):
                self.assertNotIn(secret, html)
                self.assertNotIn(secret, manifest_text)
            self.assertIn("***", html)
            self.assertIn("***", manifest_text)

            if "xlsx" in paths:
                from openpyxl import load_workbook

                workbook = load_workbook(paths["xlsx"])
                all_values = "\n".join(
                    str(cell)
                    for sheet in workbook.worksheets
                    for row in sheet.iter_rows(values_only=True)
                    for cell in row
                    if cell is not None
                )
                for secret in ("UltraSnmpSecret", "OldSecret", "NewSecret"):
                    self.assertNotIn(secret, all_values)

            base_raw = base / "raw" / "backbone4" / "interface_brief.txt"
            target_raw = target / "raw" / "backbone4" / "interface_brief.txt"
            self.assertIn("OldSecret", base_raw.read_text(encoding="utf-8"))
            self.assertIn("NewSecret", target_raw.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
