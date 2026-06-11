from __future__ import annotations

import unittest

from backbone_state_tracker.core.gui import BackboneStateTrackerApp
from backbone_state_tracker.core.models import DiffItem, DiffLine


class GuiDiffFormattingTests(unittest.TestCase):
    def test_line_preview_and_location_show_inline_change(self) -> None:
        line = DiffLine(
            kind="changed",
            base_line_no=2,
            target_line_no=2,
            base_text="GE1/0/1 UP",
            target_text="GE1/0/1 DOWN",
        )

        self.assertEqual(BackboneStateTrackerApp._format_line_location(line), "2 → 2")
        self.assertEqual(BackboneStateTrackerApp._format_line_preview(line), "GE1/0/1 UP → GE1/0/1 DOWN")

    def test_selected_diff_detail_starts_with_operational_context(self) -> None:
        item = DiffItem(
            device_name="backbone4",
            command_id="interface_brief",
            command="display interface brief",
            category="interface",
            severity="Critical",
            status="changed",
            summary="Critical state keyword detected in changed output.",
            base_raw_file="raw/backbone4/interface_brief.txt",
            target_raw_file="raw/backbone4/interface_brief.txt",
        )
        line = DiffLine(
            kind="changed",
            base_line_no=2,
            target_line_no=2,
            base_text="GE1/0/1 UP",
            target_text="GE1/0/1 DOWN",
        )

        detail = BackboneStateTrackerApp._format_selected_diff_detail(item, line)

        self.assertIn("핵심 판단", detail)
        self.assertIn("- 등급: 긴급", detail)
        self.assertIn("- 판단: 변경 출력에서 긴급 상태 키워드 감지", detail)
        self.assertIn("- 위치: 2 → 2", detail)
        self.assertIn("기준: GE1/0/1 UP", detail)
        self.assertIn("비교: GE1/0/1 DOWN", detail)
        self.assertIn("작업 영향 가능성이 높으므로", detail)

    def test_diff_filter_matches_severity_and_search_terms(self) -> None:
        item = DiffItem(
            device_name="backbone4",
            command_id="interface_brief",
            command="display interface brief",
            category="interface",
            severity="Critical",
            status="changed",
            summary="Critical state keyword detected in changed output.",
        )
        line = DiffLine(
            kind="changed",
            base_line_no=2,
            target_line_no=2,
            base_text="GE1/0/1 UP",
            target_text="GE1/0/1 DOWN",
        )

        self.assertTrue(BackboneStateTrackerApp._diff_row_matches_filter(item, line, "Critical", "backbone4 down"))
        self.assertTrue(BackboneStateTrackerApp._diff_row_matches_filter(item, line, "", "interface 2"))
        self.assertFalse(BackboneStateTrackerApp._diff_row_matches_filter(item, line, "Warning", "backbone4"))
        self.assertFalse(BackboneStateTrackerApp._diff_row_matches_filter(item, line, "", "ospf"))

    def test_diff_filter_uses_redacted_values_for_search(self) -> None:
        item = DiffItem(
            device_name="backbone4",
            command_id="secret_check",
            command="display password=VerySecret",
            category="security",
            severity="Warning",
            status="changed",
            summary="Output changed.",
        )
        line = DiffLine(
            kind="changed",
            base_line_no=1,
            target_line_no=1,
            base_text="password=VerySecret",
            target_text="password=OtherSecret",
        )

        self.assertFalse(BackboneStateTrackerApp._diff_row_matches_filter(item, line, "", "VerySecret"))
        self.assertFalse(BackboneStateTrackerApp._diff_row_matches_filter(item, line, "", "OtherSecret"))
        self.assertTrue(BackboneStateTrackerApp._diff_row_matches_filter(item, line, "", "password ***"))


if __name__ == "__main__":
    unittest.main()
