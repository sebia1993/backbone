from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backbone_state_tracker.core.diagnostics.recorder import DiagnosticRecorder
from backbone_state_tracker.core.diagnostics.report import write_diagnostic_reports
from backbone_state_tracker.core.diagnostics.runner import run_self_check


class DiagnosticReportTests(unittest.TestCase):
    def test_safe_report_excludes_raw_values_and_keeps_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recorder = DiagnosticRecorder(app_version="0.9.0")
            recorder.record(
                "BST-CON-301",
                stage="network",
                status="failed",
                device_identity="real-backbone-3",
                safe_detail="host=core3.internal.example ip=10.10.10.3 password=SecretValue",
            )

            paths = write_diagnostic_reports(recorder.events, Path(tmp))
            report_text = paths.html.read_text(encoding="utf-8")
            ticket_text = paths.ticket.read_text(encoding="utf-8")
            payload = json.loads(paths.json.read_text(encoding="utf-8"))

            combined = report_text + ticket_text + json.dumps(payload, ensure_ascii=False)
            self.assertIn("BST-CON-301", combined)
            self.assertIn("DEV-001", combined)
            self.assertIn("IP-ALIAS-001", combined)
            self.assertIn("HOST-ALIAS-001", combined)
            self.assertIn("원본 로그 포함=false", combined)
            self.assertIn("진단 티켓", ticket_text)
            self.assertIn("TCP 연결 시간이 초과됐습니다.", combined)
            self.assertNotIn("real-backbone-3", combined)
            self.assertNotIn("10.10.10.3", combined)
            self.assertNotIn("core3.internal.example", combined)
            self.assertNotIn("SecretValue", combined)
            self.assertFalse(payload["raw_log_included"])
            self.assertFalse(payload["events"][0]["raw_log_included"])

    def test_self_check_creates_safe_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_self_check(Path(tmp))

            self.assertTrue(result.reports.html.exists())
            self.assertTrue(result.reports.json.exists())
            self.assertTrue(result.reports.ticket.exists())
            payload = json.loads(result.reports.json.read_text(encoding="utf-8"))
            codes = {event["code"] for event in payload["events"]}
            details = "\n".join(event["safe_detail"] for event in payload["events"])
            self.assertIn("BST-SYS-900", codes)
            self.assertIn("BST-SEC-201", codes)
            self.assertIn("BST-SEC-211", codes)
            self.assertIn("BST-REP-601", codes)
            self.assertIn("commands_config=loaded", details)
            self.assertIn("analysis_rules=loaded", details)
            self.assertIn("mock_profiles=loaded", details)
            self.assertIn("docs=present", details)
            self.assertIn("snapshot_report_bundle_write=passed", details)
            self.assertFalse(payload["raw_log_included"])

    def test_self_check_reports_invalid_analysis_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "backbone_state_tracker.core.diagnostics.runner.load_analysis_rules",
                side_effect=ValueError("invalid severity"),
            ):
                result = run_self_check(Path(tmp))

            payload = json.loads(result.reports.json.read_text(encoding="utf-8"))
            failures = [
                event
                for event in payload["events"]
                if event["code"] == "BST-CFG-122" and event["status"] == "failed"
            ]
            self.assertEqual(1, len(failures))
            self.assertIn("load_error=ValueError", failures[0]["safe_detail"])


if __name__ == "__main__":
    unittest.main()
