from __future__ import annotations

from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

from backbone_state_tracker.core.gui import BackboneStateTrackerApp, PALETTE
from backbone_state_tracker.core.models import CommandResult, Device, DiffItem, DiffLine, DiffSummary
from backbone_state_tracker.core.snapshot import SnapshotStore


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

    def _find_widget_by_text(self, widget: tk.Widget, text: str) -> tk.Widget | None:
        try:
            value = str(widget.cget("text"))
        except tk.TclError:
            value = ""
        if value == text:
            return widget
        for child in widget.winfo_children():
            found = self._find_widget_by_text(child, text)
            if found is not None:
                return found
        return None

    def test_initial_screen_is_settings_with_workflow_order_nav(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            self.assertEqual(app.current_page, "settings")
            self.assertNotIn("dashboard", app.nav_buttons)
            self.assertNotIn("dashboard", app.pages)
            self.assertNotIn("collect", app.nav_buttons)
            self.assertNotIn("collect", app.pages)
            self.assertEqual(list(app.nav_buttons), ["settings", "compare", "logs"])
            self.assertIn("settings", app.nav_buttons)
            self.assertFalse(hasattr(app, "wizard_next_button"))
        finally:
            app.destroy()

    def test_airwave_common_theme_tokens_and_nav_state(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            self.assertEqual(PALETTE["accent"], "#01A982")
            self.assertEqual(PALETTE["sidebar"], "#18232B")
            self.assertEqual(PALETTE["log_bg"], "#101820")
            self.assertEqual(app.nav_buttons["settings"].cget("bg"), PALETTE["accent"])

            app.show_page("compare")

            self.assertEqual(app.nav_buttons["compare"].cget("bg"), PALETTE["accent"])
            self.assertEqual(app.nav_buttons["settings"].cget("bg"), PALETTE["sidebar"])
            self.assertEqual(app.nav_buttons["settings"].cget("fg"), PALETTE["sidebar_text"])
        finally:
            app.destroy()

    def test_settings_page_contains_collection_controls(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.show_page("settings")
            settings_page = app.pages["settings"]
            texts = self._widget_texts(settings_page)
            classes = self._widget_classes(settings_page)

            self.assertIn("접속 계정", texts)
            self.assertIn("대상 장비", texts)
            self.assertIn("장비 추가", texts)
            self.assertIn("상태 수집", texts)
            self.assertNotIn("수집 구분", texts)
            self.assertIn("수집 단계명(선택)", texts)
            self.assertTrue(any("점검시간_YYYYMMDD_HHMM" in text for text in texts))
            self.assertIn("점검 명령 세트", texts)
            self.assertEqual(app.stage_var.get(), "작업 전")
            self.assertEqual(app.device_summary_var.get(), "사용 2대 / 입력 2대 / 행 2개")
            self.assertIsNotNone(app.settings_canvas)
            self.assertIsNotNone(app.settings_scrollbar)
            self.assertNotIn("TRadiobutton", classes)
            self.assertNotIn("작업 진행 마법사", texts)
        finally:
            app.destroy()

    def test_add_device_row_keeps_blank_row_out_of_collection_targets(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            initial_count = len(app.device_rows)
            app.add_device_row()

            self.assertEqual(initial_count, 2)
            self.assertEqual(len(app.device_rows), 3)
            added = app.device_rows[-1]
            self.assertTrue(added["enabled"].get())
            self.assertEqual(added["name"].get(), "")
            self.assertEqual(added["host"].get(), "")
            self.assertEqual(added["port"].get(), "22")
            self.assertEqual(added["device_type"].get(), "hp_comware")
            self.assertEqual(app.device_summary_var.get(), "사용 2대 / 입력 2대 / 행 3개")
            self.assertEqual(len(app._read_devices_from_form()), 2)
        finally:
            app.destroy()

    def test_device_summary_updates_as_target_rows_change(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app._apply_devices([Device(name="backbone3", host="192.0.2.3"), Device(name="backbone4", host="192.0.2.4")])
            self.assertEqual(app.device_summary_var.get(), "사용 2대 / 입력 2대 / 행 2개")

            app.add_device_row()
            app.device_rows[2]["name"].set("backbone5")
            app.device_rows[2]["host"].set("192.0.2.5")
            self.assertEqual(app.device_summary_var.get(), "사용 3대 / 입력 3대 / 행 3개")

            app.device_rows[2]["enabled"].set(False)
            self.assertEqual(app.device_summary_var.get(), "사용 2대 / 입력 3대 / 행 3개")
        finally:
            app.destroy()

    def test_settings_page_scroll_region_expands_with_many_device_rows(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            self.assertIsNotNone(app.settings_canvas)
            for index in range(10):
                app._add_device_row(Device(name=f"extra{index}", host=f"192.0.2.{20 + index}"))
            app.update_idletasks()
            scroll_region = str(app.settings_canvas.cget("scrollregion"))

            self.assertTrue(scroll_region)
            self.assertEqual(app.device_summary_var.get(), "사용 12대 / 입력 12대 / 행 12개")
        finally:
            app.destroy()

    def test_apply_devices_expands_target_rows_for_more_than_two_devices(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            devices = [
                Device(name="backbone3", host="192.0.2.3"),
                Device(name="backbone4", host="192.0.2.4"),
                Device(name="backbone5", host="192.0.2.5", port=2022, device_type="hp_comware"),
            ]

            app._apply_devices(devices)

            self.assertEqual(len(app.device_rows), 3)
            self.assertEqual(app.device_rows[2]["name"].get(), "backbone5")
            self.assertEqual(app.device_rows[2]["host"].get(), "192.0.2.5")
            self.assertEqual(app.device_rows[2]["port"].get(), "2022")
            self.assertEqual([device.name for device in app._read_devices_from_form()], ["backbone3", "backbone4", "backbone5"])
        finally:
            app.destroy()

    def test_apply_devices_clears_stale_extra_rows_when_shorter_list_is_loaded(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app._apply_devices(
                [
                    Device(name="backbone3", host="192.0.2.3"),
                    Device(name="backbone4", host="192.0.2.4"),
                    Device(name="temporary", host="192.0.2.99"),
                ]
            )
            app._apply_devices([Device(name="backbone3", host="192.0.2.3")])

            self.assertEqual(len(app.device_rows), 3)
            self.assertEqual(app.device_rows[1]["name"].get(), "")
            self.assertEqual(app.device_rows[1]["host"].get(), "")
            self.assertEqual(app.device_rows[2]["name"].get(), "")
            self.assertEqual(app.device_rows[2]["host"].get(), "")
            self.assertEqual([device.name for device in app._read_devices_from_form()], ["backbone3"])
        finally:
            app.destroy()

    def test_default_collect_stage_becomes_custom_after_baseline_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = BackboneStateTrackerApp()
            app.withdraw()
            try:
                app.snapshot_store = SnapshotStore(Path(tmp))
                self.assertEqual(app._default_collect_stage_name(), "작업 전")

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
                app.snapshot_store.write_snapshot(
                    "작업 전",
                    [device],
                    {device.name: [result]},
                    folder_label="pre_work",
                    stage_name="작업 전",
                    stage_slug="pre_work",
                )
                self.assertEqual(app._default_collect_stage_name(), "사용자 지정")
            finally:
                app.destroy()

    def test_sample_baseline_does_not_change_first_real_collection_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = BackboneStateTrackerApp()
            app.withdraw()
            try:
                app.snapshot_store = SnapshotStore(Path(tmp))
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
                app.snapshot_store.write_snapshot(
                    "[샘플] 작업 전",
                    [device],
                    {device.name: [result]},
                    folder_label="sample_pre_work",
                    stage_name="[샘플] 작업 전",
                    stage_slug="sample_pre_work",
                )

                self.assertEqual(app._default_collect_stage_name(), "작업 전")
            finally:
                app.destroy()

    def test_runtime_summary_labels_sample_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = BackboneStateTrackerApp()
            app.withdraw()
            try:
                app.snapshot_store = SnapshotStore(Path(tmp))
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
                sample = app.snapshot_store.write_snapshot(
                    "[샘플] 작업 전",
                    [device],
                    {device.name: [result]},
                    folder_label="sample_pre_work",
                    stage_name="[샘플] 작업 전",
                    stage_slug="sample_pre_work",
                )
                real = app.snapshot_store.write_snapshot(
                    "작업 전",
                    [device],
                    {device.name: [result]},
                    folder_label="pre_work",
                    stage_name="작업 전",
                    stage_slug="pre_work",
                )

                app.baseline_var.set(sample.name)
                app.target_var.set(real.name)
                app._update_runtime_summary()

                self.assertEqual(app.baseline_display_var.get(), f"샘플: {sample.name}")
                self.assertEqual(app.target_display_var.get(), real.name)
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
            self.assertEqual(set(app.metric_chips), {"Critical", "Warning", "Info", "Unchanged"})
        finally:
            app.destroy()

    def test_workflow_pages_use_operational_status_panels(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            settings_texts = self._widget_texts(app.pages["settings"])
            log_texts = self._widget_texts(app.pages["logs"])

            self.assertIn("운영 입력 순서", settings_texts)
            self.assertIn("대상 요약", settings_texts)
            self.assertIn("수집 흐름", settings_texts)
            self.assertIn("설정 점검 상태", settings_texts)
            self.assertIn("실행 이력", log_texts)
            self.assertTrue(hasattr(app, "collection_flow_panel"))
            self.assertTrue(hasattr(app, "collection_status_panel"))
            self.assertTrue(hasattr(app, "compare_status_panel"))
            self.assertTrue(hasattr(app, "log_flow_panel"))
            self.assertEqual(app.collection_flow_panel.cget("bg"), PALETTE["accent_soft"])
            self.assertIn("Consolas", str(app.log_text.cget("font")))
        finally:
            app.destroy()

    def test_metric_chip_selection_uses_filled_state(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.set_diff_severity_filter("Critical")

            self.assertEqual(app.metric_chips["Critical"].cget("bg"), PALETTE["danger_soft"])
            self.assertEqual(app.metric_chips["Critical"].cget("highlightbackground"), PALETTE["danger"])
            self.assertEqual(int(app.metric_chips["Critical"].cget("highlightthickness")), 2)
            self.assertEqual(app.metric_chips["Warning"].cget("bg"), PALETTE["surface"])
        finally:
            app.destroy()

    def test_metric_chip_filter_shows_unchanged_summary_rows(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.show_page("compare")
            changed = DiffItem(
                device_name="backbone4",
                command_id="interface_brief",
                command="display interface brief",
                category="interface",
                severity="Critical",
                status="changed",
                summary="Critical state keyword detected in changed output.",
                changed_lines=[DiffLine(kind="changed", base_line_no=1, target_line_no=1, base_text="UP", target_text="DOWN")],
                change_count=1,
                change_preview="UP -> DOWN",
            )
            unchanged = DiffItem(
                device_name="backbone4",
                command_id="device_status",
                command="display device",
                category="hardware",
                severity="Unchanged",
                status="unchanged",
                summary="No meaningful change detected.",
            )
            app._update_diff_details(
                DiffSummary(base_snapshot="base", target_snapshot="target", generated_at="2026-06-12T10:00:00", items=[changed, unchanged])
            )

            self.assertEqual(len(app.diff_detail_rows), 1)
            app.set_diff_severity_filter("Unchanged")

            self.assertEqual(app.diff_severity_filter_var.get(), "변경없음")
            self.assertEqual(len(app.diff_detail_rows), 1)
            self.assertEqual(app.diff_detail_rows[0][0].command_id, "device_status")
            self.assertEqual(app.diff_detail_rows[0][1].kind, "unchanged")
        finally:
            app.destroy()

    def test_doc_lookup_checks_runtime_docs_before_packaged_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            docs_dir.mkdir()
            expected_docs = {
                "USER_GUIDE.html",
                "COMMAND_GUIDE.html",
                "VERSION_HISTORY.html",
            }
            for doc_name in expected_docs:
                (docs_dir / doc_name).write_text("<html>guide</html>", encoding="utf-8")

            with patch("backbone_state_tracker.core.gui.DOCS_DIR", docs_dir):
                for doc_name in expected_docs:
                    self.assertEqual(BackboneStateTrackerApp.find_doc_path(doc_name), docs_dir / doc_name)

    def test_help_menu_documents_exist_in_project_docs(self) -> None:
        expected_docs = (
            "USER_GUIDE.html",
            "COMMAND_GUIDE.html",
            "VERSION_HISTORY.html",
        )

        for doc_name in expected_docs:
            doc_path = BackboneStateTrackerApp.find_doc_path(doc_name)
            self.assertIsNotNone(doc_path, doc_name)
            self.assertTrue(doc_path.is_file(), doc_name)

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
            app.show_page("settings")
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

    def test_busy_guard_blocks_preflight_check(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.show_page("settings")
            app.workflow_busy = True
            with patch("backbone_state_tracker.core.gui.messagebox.showwarning") as warning:
                with patch.object(app, "_read_devices_from_form") as read_devices:
                    result = app.run_preflight_check()

            self.assertFalse(result)
            read_devices.assert_not_called()
            warning.assert_called_once()
            self.assertEqual(app.compare_status_var.get(), "진행 중")
            self.assertIn("현재 수집 또는 비교가 진행 중입니다.", app.log_text.get("1.0", "end"))
        finally:
            app.destroy()

    def test_busy_state_disables_preflight_and_snapshot_refresh_buttons(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.workflow_busy = True
            app._refresh_busy_sensitive_widgets()

            self.assertEqual(str(app.preflight_button.cget("state")), "disabled")
            self.assertEqual(str(app.snapshot_refresh_button.cget("state")), "disabled")

            app.workflow_busy = False
            app._refresh_busy_sensitive_widgets()

            self.assertEqual(str(app.preflight_button.cget("state")), "normal")
            self.assertEqual(str(app.snapshot_refresh_button.cget("state")), "normal")
        finally:
            app.destroy()

    def test_collect_validation_error_moves_to_logs(self) -> None:
        app = BackboneStateTrackerApp()
        app.withdraw()
        try:
            app.show_page("settings")
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
            app.show_page("settings")
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
