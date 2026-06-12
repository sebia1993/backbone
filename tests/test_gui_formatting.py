from __future__ import annotations

from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

from backbone_state_tracker.core.gui import BackboneStateTrackerApp
from backbone_state_tracker.core.models import Device, DiffItem, DiffLine, DiffSummary


class GuiDiffFormattingTests(unittest.TestCase):
    def _widget_texts(self, widget: tk.Widget) -> list[str]:
        texts: list[str] = []
        try:
            value = str(widget.cget("text"))
        except tk.TclError:
            value = ""
        if value:
            texts.append(value)
        for child in widget.winfo_children():
            texts.extend(self._widget_texts(child))
        return texts

    def _widget_classes(self, widget: tk.Widget) -> list[str]:
        classes = [widget.winfo_class()]
        for child in widget.winfo_children():
            classes.extend(self._widget_classes(child))
        return classes

    def test_initial_screen_is_collect_without_dashboard_nav(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            self.assertEqual(app.current_page, "collect")
            self.assertNotIn("dashboard", app.nav_buttons)
            self.assertNotIn("dashboard", app.pages)
            self.assertIn("collect", app.nav_buttons)
            self.assertTrue(hasattr(app, "wizard_next_button"))
        finally:
            app.destroy()

    def test_collect_page_uses_single_custom_stage_name_input(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            collect_page = app.pages["collect"]
            texts = self._widget_texts(collect_page)
            classes = self._widget_classes(collect_page)

            self.assertIn("사용자 지정 단계명", texts)
            self.assertNotIn("작업 전", texts)
            self.assertNotIn("백본3 OFF 중", texts)
            self.assertNotIn("복구 후", texts)
            self.assertNotIn("TRadiobutton", classes)
        finally:
            app.destroy()

    def test_compare_page_uses_compact_metrics_above_details(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            compare_page = app.pages["compare"]
            texts = self._widget_texts(compare_page)

            self.assertIn("최근 변경 상세", texts)
            self.assertNotIn("최근 비교 지표", texts)
            self.assertTrue(hasattr(app, "compare_metric_bar"))

            app._apply_compare_counts({"Critical": 2, "Warning": 1, "Info": 3, "Unchanged": 4})
            self.assertEqual(app.metric_vars["Critical"].get(), "2")
            self.assertEqual(app.metric_vars["Warning"].get(), "1")
            self.assertEqual(app.metric_vars["Info"].get(), "3")
            self.assertEqual(app.metric_vars["Unchanged"].get(), "4")
        finally:
            app.destroy()

    def test_doc_lookup_checks_runtime_docs_before_packaged_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            docs_dir.mkdir()
            guide = docs_dir / "USER_GUIDE.html"
            guide.write_text("<html>guide</html>", encoding="utf-8")

            with patch("backbone_state_tracker.core.gui.DOCS_DIR", docs_dir):
                self.assertEqual(BackboneStateTrackerApp.find_doc_path("USER_GUIDE.html"), guide)

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

    def test_selected_raw_file_path_resolves_from_summary_snapshots(self) -> None:
        summary = DiffSummary(
            base_snapshot=str(Path("outputs") / "snapshots" / "pre"),
            target_snapshot=str(Path("outputs") / "snapshots" / "off"),
            generated_at="2026-06-11T20:30:00",
        )
        item = DiffItem(
            device_name="backbone4",
            command_id="interface_brief",
            command="display interface brief",
            category="interface",
            severity="Critical",
            status="changed",
            summary="Critical state keyword detected in changed output.",
            base_raw_file=str(Path("raw") / "backbone4" / "interface_brief.txt"),
            target_raw_file=str(Path("raw") / "backbone4" / "interface_brief.txt"),
        )

        self.assertEqual(
            BackboneStateTrackerApp._resolve_raw_file_path(summary, item, "base"),
            Path("outputs") / "snapshots" / "pre" / "raw" / "backbone4" / "interface_brief.txt",
        )
        self.assertEqual(
            BackboneStateTrackerApp._resolve_raw_file_path(summary, item, "target"),
            Path("outputs") / "snapshots" / "off" / "raw" / "backbone4" / "interface_brief.txt",
        )

    def test_busy_guard_blocks_collection_before_validation(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.show_page("collect")
            app.workflow_busy = True
            with patch("backbone_state_tracker.core.gui.messagebox.showwarning") as warning:
                with patch.object(app, "_read_devices_from_form") as read_devices:
                    app.collect_snapshot()

            read_devices.assert_not_called()
            warning.assert_called_once()
            self.assertEqual(app.compare_status_var.get(), "진행 중")
            self.assertEqual(app.current_page, "logs")
            self.assertIn("현재 수집 또는 비교가 진행 중입니다.", app.log_text.get("1.0", "end"))
        finally:
            app.destroy()

    def test_collect_validation_error_moves_to_logs(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.show_page("collect")
            with patch("backbone_state_tracker.core.gui.messagebox.showerror") as error:
                with patch.object(app, "_read_devices_from_form", side_effect=ValueError("테스트 입력 오류")):
                    app.collect_snapshot()

            error.assert_called_once()
            self.assertEqual(app.current_page, "logs")
            self.assertIn("상태 수집을 시작하지 못했습니다: 테스트 입력 오류", app.log_text.get("1.0", "end"))
            self.assertFalse(app.workflow_busy)
        finally:
            app.destroy()

    def test_collect_start_moves_to_logs_before_worker_runs(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.show_page("collect")
            app.username_var.set("operator")
            app.password_var.set("password")
            thread = MagicMock()
            with patch.object(app, "_read_devices_from_form", return_value=[Device(name="backbone3", host="192.0.2.3")]):
                with patch("backbone_state_tracker.core.gui.threading.Thread", return_value=thread) as thread_cls:
                    app.collect_snapshot()

            thread_cls.assert_called_once()
            thread.start.assert_called_once()
            self.assertEqual(app.current_page, "logs")
            self.assertTrue(app.workflow_busy)
            self.assertEqual(app.status_chip_var.get(), "수집 중")
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
