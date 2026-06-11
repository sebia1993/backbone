from __future__ import annotations

import os
import shutil
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .collector import SnapshotCollector
from .config import load_commands, load_devices, save_devices
from .diff_engine import DiffEngine
from .models import Device, DiffItem, DiffLine, DiffSummary
from .mock_validation import create_mock_validation_artifacts
from .paths import resource_root, runtime_root
from .redaction import redact_sensitive_text
from .report_bundle import create_share_report_bundle
from .reporter import ReportWriter, change_type_label, summary_label
from .snapshot import SnapshotStore
from .version import APP_NAME, APP_VERSION
from .workflow import (
    BB3_OFF_STAGE,
    POST_RESTORE_STAGE,
    PRE_WORK_STAGE,
    WORK_STAGE_NAMES,
    WorkStage,
    build_snapshot_folder_label,
    find_latest_pre_work_snapshot,
    resolve_stage,
    severity_to_korean,
)
from .workflow_wizard import (
    WorkflowWizardState,
    action_stage_name,
    build_workflow_wizard_state,
    find_latest_stage_snapshot,
)


PROJECT_DIR = runtime_root()
RESOURCE_DIR = resource_root()
CONFIG_DIR = PROJECT_DIR / "config"
BUNDLED_CONFIG_DIR = RESOURCE_DIR / "config"
DOCS_DIR = PROJECT_DIR / "docs"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "snapshots"
COMMANDS_PATH = CONFIG_DIR / "commands.yaml"
DEVICES_PATH = CONFIG_DIR / "devices.yaml"
DEVICES_EXAMPLE_PATH = CONFIG_DIR / "devices.example.yaml"


PALETTE = {
    "bg": "#F4F7FA",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FBFC",
    "sidebar": "#FFFFFF",
    "border": "#D9E3EA",
    "text": "#1F2933",
    "muted": "#5E6C7A",
    "accent": "#01A982",
    "accent_dark": "#007A63",
    "accent_soft": "#E7F7F2",
    "danger": "#B42318",
    "danger_soft": "#FDECEB",
    "warning": "#B54708",
    "warning_soft": "#FFF4E5",
    "info": "#0F6CBD",
    "info_soft": "#EAF3FF",
    "neutral_soft": "#EEF2F6",
}

SEVERITY_META = {
    "Critical": ("긴급", PALETTE["danger"], PALETTE["danger_soft"]),
    "Warning": ("주의", PALETTE["warning"], PALETTE["warning_soft"]),
    "Info": ("정보", PALETTE["info"], PALETTE["info_soft"]),
    "Unchanged": ("변경없음", PALETTE["accent_dark"], PALETTE["accent_soft"]),
}
SEVERITY_FILTERS = {
    "전체": "",
    "긴급": "Critical",
    "주의": "Warning",
    "정보": "Info",
    "변경없음": "Unchanged",
}


class BackboneStateTrackerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1240x800")
        self.minsize(1080, 720)
        self.configure(bg=PALETTE["bg"])

        self.snapshot_store = SnapshotStore(OUTPUT_DIR)
        self.latest_report: Path | None = None
        self.latest_share_bundle: Path | None = None
        self.device_rows: list[dict[str, tk.Variable]] = []
        self.pages: dict[str, tk.Frame] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.current_page = "dashboard"
        self.last_counts = {key: 0 for key in SEVERITY_META}
        self.last_diff_summary: DiffSummary | None = None
        self.diff_detail_rows: list[tuple[DiffItem, DiffLine]] = []
        self.workflow_busy = False
        self.off_review_confirmed = False
        self.final_review_confirmed = False
        self.workflow_step_widgets: list[dict[str, tk.Widget]] = []
        self.current_wizard_state: WorkflowWizardState | None = None

        self._ensure_runtime_config_files()

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.timeout_var = tk.StringVar(value="30")
        self.stage_var = tk.StringVar(value=PRE_WORK_STAGE)
        self.custom_label_var = tk.StringVar()
        self.baseline_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.compare_status_var = tk.StringVar(value="작업 전 스냅샷을 수집하면 자동 비교 기준으로 지정됩니다.")
        self.page_title_var = tk.StringVar(value="대시보드")
        self.page_description_var = tk.StringVar(value="백본 3/4호기 작업 상태를 수집하고 변경점을 추적합니다.")
        self.baseline_display_var = tk.StringVar(value="-")
        self.target_display_var = tk.StringVar(value="-")
        self.latest_snapshot_var = tk.StringVar(value="-")
        self.latest_report_var = tk.StringVar(value="-")
        self.latest_share_bundle_var = tk.StringVar(value="-")
        self.diff_severity_filter_var = tk.StringVar(value="전체")
        self.diff_search_var = tk.StringVar()
        self.diff_filter_status_var = tk.StringVar(value="필터: -")
        self.status_chip_var = tk.StringVar(value="대기")
        self.wizard_title_var = tk.StringVar(value="작업 진행")
        self.wizard_message_var = tk.StringVar(value="작업 흐름을 확인하세요.")
        self.wizard_next_label_var = tk.StringVar(value="다음 단계")
        self.metric_vars = {key: tk.StringVar(value="0") for key in SEVERITY_META}

        self._configure_styles()
        self._build_menu()
        self._build_ui()
        self._load_initial_devices()
        self.refresh_snapshots(log_message=False)

    def _ensure_runtime_config_files(self) -> None:
        _copy_if_missing(BUNDLED_CONFIG_DIR / "commands.yaml", COMMANDS_PATH)
        _copy_if_missing(BUNDLED_CONFIG_DIR / "devices.example.yaml", DEVICES_EXAMPLE_PATH)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        base_font = ("Segoe UI", 10)
        style.configure(".", font=base_font, background=PALETTE["bg"], foreground=PALETTE["text"])
        style.configure("App.TFrame", background=PALETTE["bg"])
        style.configure("Surface.TFrame", background=PALETTE["surface"])
        style.configure("Muted.TLabel", background=PALETTE["surface"], foreground=PALETTE["muted"])
        style.configure("Title.TLabel", background=PALETTE["bg"], foreground=PALETTE["text"], font=("Segoe UI", 18, "bold"))
        style.configure("Subtle.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"], font=("Segoe UI", 10))
        style.configure("SectionTitle.TLabel", background=PALETTE["surface"], foreground=PALETTE["text"], font=("Segoe UI", 11, "bold"))
        style.configure("Primary.TButton", padding=(14, 8), background=PALETTE["accent"], foreground="#FFFFFF", borderwidth=0)
        style.map("Primary.TButton", background=[("active", PALETTE["accent_dark"]), ("pressed", PALETTE["accent_dark"])])
        style.configure("Secondary.TButton", padding=(12, 8), background=PALETTE["surface_alt"], foreground=PALETTE["text"])
        style.map("Secondary.TButton", background=[("active", PALETTE["accent_soft"])])
        style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=PALETTE["border"], lightcolor=PALETTE["border"])
        style.configure("TCombobox", fieldbackground="#FFFFFF", bordercolor=PALETTE["border"], lightcolor=PALETTE["border"])
        style.configure("TRadiobutton", background=PALETTE["surface"], foreground=PALETTE["text"])
        style.map("TRadiobutton", background=[("active", PALETTE["surface"])])
        style.configure("TCheckbutton", background=PALETTE["surface"], foreground=PALETTE["text"])

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="결과 폴더 열기", command=self.open_outputs)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.destroy)
        menu_bar.add_cascade(label="파일", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="사용자 가이드 열기", command=lambda: self.open_doc("USER_GUIDE.html"))
        help_menu.add_command(label="버전 변경내역 열기", command=lambda: self.open_doc("VERSION_HISTORY.html"))
        menu_bar.add_cascade(label="도움말", menu=help_menu)

        self.config(menu=menu_bar)

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = tk.Frame(
            self,
            bg=PALETTE["sidebar"],
            width=232,
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
        )
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        shell = tk.Frame(self, bg=PALETTE["bg"])
        shell.grid(row=0, column=1, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        self._build_topbar(shell)

        self.content = tk.Frame(shell, bg=PALETTE["bg"])
        self.content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self._build_pages()
        self.show_page("dashboard")

    def _build_sidebar(self, parent: tk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        brand = tk.Frame(parent, bg=PALETTE["sidebar"])
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 22))
        brand.columnconfigure(1, weight=1)

        logo = tk.Label(
            brand,
            text="BST",
            bg=PALETTE["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            width=5,
            height=2,
        )
        logo.grid(row=0, column=0, sticky="w", padx=(0, 10))
        tk.Label(
            brand,
            text="백본 상태\n추적 콘솔",
            bg=PALETTE["sidebar"],
            fg=PALETTE["text"],
            justify="left",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=1, sticky="w")

        nav_items = [
            ("dashboard", "대시보드", "핵심 상태 요약"),
            ("collect", "상태 수집", "작업 단계별 스냅샷"),
            ("compare", "비교 결과", "기준/대상 변경점"),
            ("settings", "장비 설정", "접속 계정과 대상 장비"),
            ("logs", "작업 로그", "실행 이력과 오류"),
        ]
        for row, (key, title, subtitle) in enumerate(nav_items, start=1):
            button = tk.Button(
                parent,
                text=f"{title}\n{subtitle}",
                anchor="w",
                justify="left",
                relief="flat",
                bd=0,
                padx=16,
                pady=11,
                bg=PALETTE["sidebar"],
                activebackground=PALETTE["accent_soft"],
                activeforeground=PALETTE["accent_dark"],
                fg=PALETTE["text"],
                font=("Segoe UI", 10, "bold"),
                command=lambda page=key: self.show_page(page),
            )
            button.grid(row=row, column=0, sticky="ew", padx=12, pady=3)
            self.nav_buttons[key] = button

        parent.rowconfigure(6, weight=1)
        footer = tk.Label(
            parent,
            text=f"v{APP_VERSION}\n읽기 전용 점검 명령만 실행",
            bg=PALETTE["sidebar"],
            fg=PALETTE["muted"],
            justify="left",
            font=("Segoe UI", 9),
        )
        footer.grid(row=7, column=0, sticky="sw", padx=18, pady=18)

    def _build_topbar(self, parent: tk.Frame) -> None:
        topbar = tk.Frame(parent, bg=PALETTE["bg"])
        topbar.grid(row=0, column=0, sticky="ew", padx=20, pady=18)
        topbar.columnconfigure(0, weight=1)

        title_block = tk.Frame(topbar, bg=PALETTE["bg"])
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, textvariable=self.page_title_var, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, textvariable=self.page_description_var, style="Subtle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))

        status = tk.Frame(
            topbar,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
        )
        status.grid(row=0, column=1, sticky="e")
        self._topbar_stat(status, "현재 상태", self.status_chip_var, 0)
        self._topbar_stat(status, "기준", self.baseline_display_var, 1)
        self._topbar_stat(status, "비교 대상", self.target_display_var, 2)

    def _topbar_stat(self, parent: tk.Frame, label: str, variable: tk.StringVar, column: int) -> None:
        cell = tk.Frame(parent, bg=PALETTE["surface"], padx=14, pady=8)
        cell.grid(row=0, column=column, sticky="nsew")
        tk.Label(cell, text=label, bg=PALETTE["surface"], fg=PALETTE["muted"], font=("Segoe UI", 8)).pack(anchor="w")
        tk.Label(cell, textvariable=variable, bg=PALETTE["surface"], fg=PALETTE["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")

    def _build_pages(self) -> None:
        self._build_dashboard_page()
        self._build_collect_page()
        self._build_compare_page()
        self._build_settings_page()
        self._build_logs_page()

    def _make_page(self, key: str) -> tk.Frame:
        page = tk.Frame(self.content, bg=PALETTE["bg"])
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(0, weight=1)
        self.pages[key] = page
        return page

    def _make_section(self, parent: tk.Frame, title: str, row: int, column: int = 0, columnspan: int = 1) -> tk.Frame:
        section = tk.Frame(
            parent,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
        )
        section.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=0, pady=(0, 14))
        section.columnconfigure(0, weight=1)
        tk.Label(
            section,
            text=title,
            bg=PALETTE["surface"],
            fg=PALETTE["text"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        return section

    def _build_dashboard_page(self) -> None:
        page = self._make_page("dashboard")
        page.rowconfigure(2, weight=1)

        metrics = tk.Frame(page, bg=PALETTE["bg"])
        metrics.grid(row=0, column=0, sticky="ew")
        for column in range(4):
            metrics.columnconfigure(column, weight=1)

        for column, key in enumerate(["Critical", "Warning", "Info", "Unchanged"]):
            label, accent, soft = SEVERITY_META[key]
            self._metric_card(metrics, column, label, self.metric_vars[key], accent, soft)

        wizard = self._make_section(page, "작업 진행 마법사", 1)
        wizard.rowconfigure(1, weight=1)
        wizard_body = tk.Frame(wizard, bg=PALETTE["surface"], padx=16, pady=16)
        wizard_body.grid(row=1, column=0, sticky="nsew")
        wizard_body.columnconfigure(0, weight=1)

        self.workflow_steps_frame = tk.Frame(wizard_body, bg=PALETTE["surface"])
        self.workflow_steps_frame.grid(row=0, column=0, sticky="ew")
        for column in range(6):
            self.workflow_steps_frame.columnconfigure(column, weight=1)
        self._build_wizard_step_cards()

        current = tk.Frame(
            wizard_body,
            bg=PALETTE["surface_alt"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        current.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        current.columnconfigure(0, weight=1)
        tk.Label(
            current,
            textvariable=self.wizard_title_var,
            bg=PALETTE["surface_alt"],
            fg=PALETTE["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            current,
            textvariable=self.wizard_message_var,
            bg=PALETTE["surface_alt"],
            fg=PALETTE["muted"],
            font=("Segoe UI", 9),
            wraplength=720,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.wizard_next_button = ttk.Button(
            current,
            textvariable=self.wizard_next_label_var,
            style="Primary.TButton",
            command=self._run_wizard_next_action,
        )
        self.wizard_next_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(14, 0))

        body = tk.Frame(page, bg=PALETTE["bg"])
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        manual = self._make_section(body, "수동 작업 바로가기", 0, 0)
        manual.rowconfigure(1, weight=1)
        manual_body = tk.Frame(manual, bg=PALETTE["surface"], padx=16, pady=16)
        manual_body.grid(row=1, column=0, sticky="nsew")
        manual_body.columnconfigure(0, weight=1)
        for row, stage_name in enumerate(WORK_STAGE_NAMES):
            stage = resolve_stage(stage_name)
            self._workflow_row(manual_body, row, stage.name, stage.description, stage.auto_compare)

        summary = self._make_section(body, "운영 요약", 0, 1)
        summary.rowconfigure(1, weight=1)
        summary_body = tk.Frame(summary, bg=PALETTE["surface"], padx=16, pady=16)
        summary_body.grid(row=1, column=0, sticky="nsew")
        summary_body.columnconfigure(1, weight=1)

        self._summary_row(summary_body, 0, "최근 스냅샷", self.latest_snapshot_var)
        self._summary_row(summary_body, 1, "최근 리포트", self.latest_report_var)
        self._summary_row(summary_body, 2, "최근 공유 ZIP", self.latest_share_bundle_var)
        self._summary_row(summary_body, 3, "비교 상태", self.compare_status_var)

        quick = tk.Frame(summary_body, bg=PALETTE["surface"])
        quick.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(quick, text="스냅샷 새로고침", style="Secondary.TButton", command=self.refresh_snapshots).pack(side="left")
        ttk.Button(quick, text="최근 리포트", style="Secondary.TButton", command=self.open_last_report).pack(side="left", padx=(8, 0))
        ttk.Button(quick, text="공유 ZIP", style="Secondary.TButton", command=self.open_last_share_bundle).pack(side="left", padx=(8, 0))
        ttk.Button(quick, text="결과 폴더", style="Secondary.TButton", command=self.open_outputs).pack(side="left", padx=(8, 0))
        ttk.Button(quick, text="샘플 검증 생성", style="Secondary.TButton", command=self.create_mock_validation).pack(
            side="left",
            padx=(8, 0),
        )

    def _build_wizard_step_cards(self) -> None:
        self.workflow_step_widgets = []
        for column in range(6):
            card = tk.Frame(
                self.workflow_steps_frame,
                bg=PALETTE["surface_alt"],
                highlightbackground=PALETTE["border"],
                highlightthickness=1,
                padx=10,
                pady=10,
            )
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
            marker = tk.Frame(card, bg=PALETTE["neutral_soft"], height=5)
            marker.grid(row=0, column=0, sticky="ew", pady=(0, 8))
            title = tk.Label(card, text="-", bg=PALETTE["surface_alt"], fg=PALETTE["text"], font=("Segoe UI", 9, "bold"), wraplength=130)
            title.grid(row=1, column=0, sticky="w")
            status = tk.Label(card, text="-", bg=PALETTE["surface_alt"], fg=PALETTE["muted"], font=("Segoe UI", 8), wraplength=130)
            status.grid(row=2, column=0, sticky="w", pady=(5, 0))
            card.columnconfigure(0, weight=1)
            self.workflow_step_widgets.append({"card": card, "marker": marker, "title": title, "status": status})

    def _metric_card(self, parent: tk.Frame, column: int, title: str, variable: tk.StringVar, accent: str, soft: str) -> None:
        card = tk.Frame(
            parent,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
        )
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0), pady=(0, 14))
        card.columnconfigure(1, weight=1)
        stripe = tk.Frame(card, bg=accent, width=5)
        stripe.grid(row=0, column=0, rowspan=2, sticky="nsw")
        tk.Label(card, text=title, bg=PALETTE["surface"], fg=PALETTE["muted"], font=("Segoe UI", 9, "bold")).grid(
            row=0, column=1, sticky="w", padx=14, pady=(12, 0)
        )
        tk.Label(card, textvariable=variable, bg=PALETTE["surface"], fg=accent, font=("Segoe UI", 24, "bold")).grid(
            row=1, column=1, sticky="w", padx=14, pady=(0, 12)
        )
        badge = tk.Frame(card, bg=soft, width=28, height=28)
        badge.grid(row=0, column=2, rowspan=2, padx=14, pady=14)
        badge.grid_propagate(False)

    def _workflow_row(self, parent: tk.Frame, row: int, title: str, description: str, auto_compare: bool) -> None:
        item = tk.Frame(parent, bg=PALETTE["surface_alt"], highlightbackground=PALETTE["border"], highlightthickness=1)
        item.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        item.columnconfigure(1, weight=1)

        marker_color = PALETTE["accent"] if auto_compare else PALETTE["info"]
        tk.Frame(item, bg=marker_color, width=4).grid(row=0, column=0, rowspan=2, sticky="nsw")
        tk.Label(item, text=title, bg=PALETTE["surface_alt"], fg=PALETTE["text"], font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, sticky="w", padx=12, pady=(10, 0)
        )
        tk.Label(item, text=description, bg=PALETTE["surface_alt"], fg=PALETTE["muted"], font=("Segoe UI", 9)).grid(
            row=1, column=1, sticky="w", padx=12, pady=(2, 10)
        )
        ttk.Button(item, text="수집", style="Secondary.TButton", command=lambda value=title: self.collect_stage(value)).grid(
            row=0, column=2, rowspan=2, sticky="e", padx=12, pady=10
        )

    def _refresh_wizard(self) -> None:
        if not hasattr(self, "wizard_next_button"):
            return

        snapshots = self.snapshot_store.list_snapshots()
        state = build_workflow_wizard_state(
            snapshots,
            device_ready=self._has_ready_device_config(),
            busy=self.workflow_busy,
            off_review_confirmed=self.off_review_confirmed,
            final_review_confirmed=self.final_review_confirmed,
            latest_counts=self.last_counts,
        )
        self.current_wizard_state = state
        self.wizard_title_var.set(self._active_step_title(state))
        self.wizard_message_var.set(state.message)
        self.wizard_next_label_var.set(state.next_label)
        self.wizard_next_button.configure(state="normal" if state.next_enabled else "disabled")

        for step, widgets in zip(state.steps, self.workflow_step_widgets):
            colors = self._wizard_status_colors(step.status)
            for key in ("card", "title", "status"):
                widgets[key].configure(bg=colors["bg"])
            widgets["marker"].configure(bg=colors["accent"])
            widgets["title"].configure(text=step.title, fg=colors["fg"])
            widgets["status"].configure(text=f"{self._wizard_status_label(step.status)} · {step.detail}", fg=colors["muted"])

    def _run_wizard_next_action(self) -> None:
        state = self.current_wizard_state
        if state is None or not state.next_enabled:
            return

        stage_name = action_stage_name(state.next_action)
        if stage_name is not None:
            self.stage_var.set(stage_name)
            self.show_page("dashboard")
            self.collect_stage(stage_name)
            return

        if state.next_action == "open_settings":
            self.show_page("settings")
            return
        if state.next_action == "review_off":
            self._review_stage_from_wizard("bb3_off")
            return
        if state.next_action == "review_final":
            self._review_stage_from_wizard("post_restore")
            return
        if state.next_action == "open_report":
            self.open_last_report()

    def _review_stage_from_wizard(self, stage_slug: str) -> None:
        snapshots = self.snapshot_store.list_snapshots()
        baseline = find_latest_pre_work_snapshot(snapshots)
        target = find_latest_stage_snapshot(snapshots, stage_slug)
        if baseline is None or target is None:
            messagebox.showerror("비교 오류", "비교할 기준 또는 대상 스냅샷을 찾을 수 없습니다.")
            return

        self.baseline_var.set(baseline.name)
        self.target_var.set(target.name)
        if stage_slug == "bb3_off":
            self.off_review_confirmed = True
        elif stage_slug == "post_restore":
            self.final_review_confirmed = True
        self.show_page("compare")
        self._refresh_wizard()

        if not self._last_summary_matches_target(target.name):
            self.compare_selected()

    def _last_summary_matches_target(self, target_name: str) -> bool:
        if self.last_diff_summary is None:
            return False
        return Path(self.last_diff_summary.target_snapshot).name == target_name

    def _has_ready_device_config(self) -> bool:
        for row in self.device_rows:
            if bool(row["enabled"].get()) and str(row["host"].get()).strip():
                return True
        return False

    @staticmethod
    def _active_step_title(state: WorkflowWizardState) -> str:
        current = next((step for step in state.steps if step.key == state.active_step), None)
        if current is None:
            return "작업 진행 완료"
        return f"현재 단계: {current.title}"

    @staticmethod
    def _wizard_status_label(status: str) -> str:
        return {
            "complete": "완료",
            "current": "진행 가능",
            "pending": "대기",
            "locked": "잠김",
        }.get(status, status)

    @staticmethod
    def _wizard_status_colors(status: str) -> dict[str, str]:
        if status == "complete":
            return {"bg": PALETTE["accent_soft"], "accent": PALETTE["accent"], "fg": PALETTE["accent_dark"], "muted": PALETTE["accent_dark"]}
        if status == "current":
            return {"bg": PALETTE["info_soft"], "accent": PALETTE["info"], "fg": PALETTE["text"], "muted": PALETTE["info"]}
        if status == "locked":
            return {"bg": PALETTE["neutral_soft"], "accent": PALETTE["border"], "fg": PALETTE["muted"], "muted": PALETTE["muted"]}
        return {"bg": PALETTE["surface_alt"], "accent": PALETTE["border"], "fg": PALETTE["text"], "muted": PALETTE["muted"]}

    def _summary_row(self, parent: tk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        tk.Label(parent, text=label, bg=PALETTE["surface"], fg=PALETTE["muted"], font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        tk.Label(
            parent,
            textvariable=variable,
            bg=PALETTE["surface"],
            fg=PALETTE["text"],
            font=("Segoe UI", 9, "bold"),
            wraplength=300,
            justify="left",
        ).grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=(8, 0))

    def _build_collect_page(self) -> None:
        page = self._make_page("collect")
        page.rowconfigure(1, weight=1)

        stage_section = self._make_section(page, "수집 단계", 0)
        form = tk.Frame(stage_section, bg=PALETTE["surface"], padx=16, pady=16)
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        for column, stage_name in enumerate(WORK_STAGE_NAMES):
            ttk.Radiobutton(form, text=stage_name, value=stage_name, variable=self.stage_var).grid(
                row=0, column=column, sticky="w", padx=(0, 16), pady=(0, 12)
            )

        tk.Label(form, text="사용자 지정 단계명", bg=PALETTE["surface"], fg=PALETTE["muted"], font=("Segoe UI", 9)).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Entry(form, textvariable=self.custom_label_var).grid(row=1, column=1, columnspan=3, sticky="ew", padx=(0, 12))
        ttk.Button(form, text="상태 수집 시작", style="Primary.TButton", command=self.collect_snapshot).grid(row=1, column=4, sticky="e")

        command_section = self._make_section(page, "점검 명령 세트", 1)
        command_body = tk.Frame(command_section, bg=PALETTE["surface"], padx=16, pady=16)
        command_body.grid(row=1, column=0, sticky="nsew")
        command_body.columnconfigure(0, weight=1)
        text = (
            "수집 시 config\\commands.yaml의 읽기 전용 점검 명령을 실행합니다.\n"
            "기본 명령은 인터페이스, 라우팅/이웃, LACP, 로그, 하드웨어 상태를 확인하도록 구성되어 있습니다."
        )
        tk.Label(command_body, text=text, bg=PALETTE["surface"], fg=PALETTE["muted"], justify="left").grid(row=0, column=0, sticky="w")
        ttk.Button(command_body, text="장비 설정으로 이동", style="Secondary.TButton", command=lambda: self.show_page("settings")).grid(
            row=0, column=1, sticky="e"
        )

    def _build_compare_page(self) -> None:
        page = self._make_page("compare")
        page.rowconfigure(2, weight=1)

        compare = self._make_section(page, "스냅샷 비교", 0)
        form = tk.Frame(compare, bg=PALETTE["surface"], padx=16, pady=16)
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        tk.Label(form, text="기준 스냅샷", bg=PALETTE["surface"], fg=PALETTE["muted"]).grid(row=0, column=0, sticky="w")
        self.baseline_combo = ttk.Combobox(form, textvariable=self.baseline_var, state="readonly")
        self.baseline_combo.grid(row=0, column=1, sticky="ew", padx=(8, 16))
        tk.Label(form, text="비교 스냅샷", bg=PALETTE["surface"], fg=PALETTE["muted"]).grid(row=0, column=2, sticky="w")
        self.target_combo = ttk.Combobox(form, textvariable=self.target_var, state="readonly")
        self.target_combo.grid(row=0, column=3, sticky="ew", padx=(8, 16))
        ttk.Button(form, text="목록 새로고침", style="Secondary.TButton", command=self.refresh_snapshots).grid(row=0, column=4, sticky="e")

        actions = tk.Frame(form, bg=PALETTE["surface"])
        actions.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(14, 0))
        ttk.Button(actions, text="선택 항목 비교", style="Primary.TButton", command=self.compare_selected).pack(side="left")
        ttk.Button(actions, text="샘플 검증 생성", style="Secondary.TButton", command=self.create_mock_validation).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="최근 리포트", style="Secondary.TButton", command=self.open_last_report).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="공유 ZIP", style="Secondary.TButton", command=self.open_last_share_bundle).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="결과 폴더", style="Secondary.TButton", command=self.open_outputs).pack(side="left", padx=(8, 0))
        tk.Label(actions, textvariable=self.compare_status_var, bg=PALETTE["surface"], fg=PALETTE["muted"]).pack(side="left", padx=(16, 0))

        result = self._make_section(page, "최근 비교 지표", 1)
        result_body = tk.Frame(result, bg=PALETTE["surface"], padx=16, pady=16)
        result_body.grid(row=1, column=0, sticky="nsew")
        for column in range(4):
            result_body.columnconfigure(column, weight=1)
        for column, key in enumerate(["Critical", "Warning", "Info", "Unchanged"]):
            label, accent, soft = SEVERITY_META[key]
            self._metric_card(result_body, column, label, self.metric_vars[key], accent, soft)

        detail = self._make_section(page, "최근 변경 상세", 2)
        detail.rowconfigure(1, weight=1)
        detail_body = tk.Frame(detail, bg=PALETTE["surface"], padx=16, pady=16)
        detail_body.grid(row=1, column=0, sticky="nsew")
        detail_body.rowconfigure(0, weight=0)
        detail_body.rowconfigure(1, weight=1)
        detail_body.rowconfigure(2, weight=1)
        detail_body.columnconfigure(0, weight=1)

        filter_bar = tk.Frame(detail_body, bg=PALETTE["surface"])
        filter_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        filter_bar.columnconfigure(3, weight=1)
        tk.Label(filter_bar, text="등급", bg=PALETTE["surface"], fg=PALETTE["muted"]).grid(row=0, column=0, sticky="w")
        severity_filter = ttk.Combobox(
            filter_bar,
            textvariable=self.diff_severity_filter_var,
            values=list(SEVERITY_FILTERS.keys()),
            width=10,
            state="readonly",
        )
        severity_filter.grid(row=0, column=1, sticky="w", padx=(8, 16))
        severity_filter.bind("<<ComboboxSelected>>", self._on_diff_filter_changed)
        tk.Label(filter_bar, text="검색", bg=PALETTE["surface"], fg=PALETTE["muted"]).grid(row=0, column=2, sticky="w")
        search_entry = ttk.Entry(filter_bar, textvariable=self.diff_search_var)
        search_entry.grid(row=0, column=3, sticky="ew", padx=(8, 8))
        search_entry.bind("<KeyRelease>", self._on_diff_filter_changed)
        ttk.Button(filter_bar, text="초기화", style="Secondary.TButton", command=self.reset_diff_filters).grid(row=0, column=4, sticky="e")
        tk.Label(filter_bar, textvariable=self.diff_filter_status_var, bg=PALETTE["surface"], fg=PALETTE["muted"]).grid(
            row=0,
            column=5,
            sticky="e",
            padx=(12, 0),
        )

        columns = ("severity", "device", "command", "impact", "kind", "line", "preview")
        self.diff_tree = ttk.Treeview(detail_body, columns=columns, show="headings", height=8, selectmode="browse")
        headings = {
            "severity": ("등급", 72),
            "device": ("장비", 120),
            "command": ("명령", 145),
            "impact": ("판단", 175),
            "kind": ("유형", 64),
            "line": ("라인", 92),
            "preview": ("변경 내용", 390),
        }
        for column, (label, width) in headings.items():
            self.diff_tree.heading(column, text=label)
            self.diff_tree.column(column, width=width, minwidth=50, stretch=column == "preview")
        for severity, (_label, accent, soft) in SEVERITY_META.items():
            self.diff_tree.tag_configure(f"severity_{severity}", foreground=accent, background=soft)
        self.diff_tree.grid(row=1, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(detail_body, orient="vertical", command=self.diff_tree.yview)
        tree_scroll.grid(row=1, column=1, sticky="ns")
        self.diff_tree.configure(yscrollcommand=tree_scroll.set)
        self.diff_tree.bind("<<TreeviewSelect>>", self._on_diff_detail_selected)

        self.diff_detail_text = tk.Text(
            detail_body,
            height=8,
            wrap="word",
            bg="#F8FBFC",
            fg=PALETTE["text"],
            relief="flat",
            padx=12,
            pady=10,
            font=("Consolas", 10),
        )
        self.diff_detail_text.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        self._set_diff_detail_text("비교 완료 후 변경된 라인을 선택하면 변경 전/후 값이 여기에 표시됩니다.")

    def _update_diff_details(self, summary: DiffSummary | None) -> None:
        self.last_diff_summary = summary
        self._render_diff_details()

    def _render_diff_details(self) -> None:
        if not hasattr(self, "diff_tree"):
            return
        self.diff_tree.delete(*self.diff_tree.get_children())
        self.diff_detail_rows = []
        summary = self.last_diff_summary
        if summary is None:
            self.diff_filter_status_var.set("필터: -")
            self._set_diff_detail_text("비교 완료 후 변경된 라인을 선택하면 변경 전/후 값이 여기에 표시됩니다.")
            return

        total_rows = 0
        severity_filter = self._selected_diff_severity_filter()
        query = self.diff_search_var.get().strip()
        for item in summary.items:
            if item.status == "unchanged":
                continue
            for line in item.changed_lines:
                if line.kind == "context":
                    continue
                total_rows += 1
                if not self._diff_row_matches_filter(item, line, severity_filter, query):
                    continue
                row_index = len(self.diff_detail_rows)
                self.diff_detail_rows.append((item, line))
                self.diff_tree.insert(
                    "",
                    "end",
                    iid=str(row_index),
                    values=(
                        severity_to_korean(item.severity),
                        item.device_name,
                        item.command_id,
                        self._shorten(summary_label(item), 80),
                        change_type_label(line.kind),
                        self._format_line_location(line),
                        self._shorten(self._format_line_preview(line), 120),
                    ),
                    tags=(f"severity_{item.severity}",),
                )

        self.diff_filter_status_var.set(f"표시: {len(self.diff_detail_rows)} / {total_rows}")
        if self.diff_detail_rows:
            self._set_diff_detail_text("위 목록에서 변경 행을 선택하면 기준/비교 값을 확인할 수 있습니다.")
        elif total_rows:
            self._set_diff_detail_text("현재 필터 조건에 맞는 변경 행이 없습니다.")
        else:
            self._set_diff_detail_text("표시할 행 단위 변경 상세가 없습니다. 전체 원본 diff는 HTML 리포트에서 확인하세요.")

    def _on_diff_filter_changed(self, _event: tk.Event | None = None) -> None:
        self._render_diff_details()

    def reset_diff_filters(self) -> None:
        self.diff_severity_filter_var.set("전체")
        self.diff_search_var.set("")
        self._render_diff_details()

    def _selected_diff_severity_filter(self) -> str:
        return SEVERITY_FILTERS.get(self.diff_severity_filter_var.get(), "")

    @staticmethod
    def _diff_row_matches_filter(item: DiffItem, line: DiffLine, severity_filter: str, query: str) -> bool:
        if severity_filter and item.severity != severity_filter:
            return False
        terms = [term for term in query.lower().split() if term]
        if not terms:
            return True
        haystack = " ".join(
            [
                item.severity,
                severity_to_korean(item.severity),
                item.status,
                item.device_name,
                item.command_id,
                redact_sensitive_text(item.command),
                item.category,
                summary_label(item),
                change_type_label(line.kind),
                BackboneStateTrackerApp._format_line_location(line),
                BackboneStateTrackerApp._format_line_preview(line),
                redact_sensitive_text(line.base_text),
                redact_sensitive_text(line.target_text),
            ]
        ).lower()
        return all(term in haystack for term in terms)

    def _on_diff_detail_selected(self, _event: tk.Event) -> None:
        selected = self.diff_tree.selection()
        if not selected:
            return
        try:
            item, line = self.diff_detail_rows[int(selected[0])]
        except (IndexError, ValueError):
            return
        self._set_diff_detail_text(self._format_selected_diff_detail(item, line))

    def _set_diff_detail_text(self, text: str) -> None:
        self.diff_detail_text.configure(state="normal")
        self.diff_detail_text.delete("1.0", "end")
        self.diff_detail_text.insert("1.0", text)
        self.diff_detail_text.configure(state="disabled")

    @staticmethod
    def _format_selected_diff_detail(item: DiffItem, line: DiffLine) -> str:
        return (
            "핵심 판단\n"
            f"- 등급: {severity_to_korean(item.severity)}\n"
            f"- 판단: {summary_label(item)}\n"
            f"- 장비/명령: {item.device_name} / {item.command_id}\n"
            f"- 위치: {BackboneStateTrackerApp._format_line_location(line)}\n"
            f"- 유형: {change_type_label(line.kind)}\n\n"
            "변경값\n"
            f"기준: {redact_sensitive_text(line.base_text) or '-'}\n"
            f"비교: {redact_sensitive_text(line.target_text) or '-'}\n\n"
            "추적 포인트\n"
            f"- 명령 원문: {redact_sensitive_text(item.command)}\n"
            f"- 분류: {item.category}\n"
            f"- 기준 원본: {item.base_raw_file or '-'}\n"
            f"- 비교 원본: {item.target_raw_file or '-'}\n"
            f"- 운영 메모: {BackboneStateTrackerApp._severity_guidance(item.severity)}"
        )

    @staticmethod
    def _change_kind_to_korean(kind: str) -> str:
        return change_type_label(kind)

    @staticmethod
    def _format_line_no(value: int | None) -> str:
        return "-" if value is None else str(value)

    @classmethod
    def _format_line_location(cls, line: DiffLine) -> str:
        base_line_no = cls._format_line_no(line.base_line_no)
        target_line_no = cls._format_line_no(line.target_line_no)
        return f"{base_line_no} → {target_line_no}"

    @staticmethod
    def _format_line_preview(line: DiffLine) -> str:
        if line.kind == "changed":
            return f"{redact_sensitive_text(line.base_text)} → {redact_sensitive_text(line.target_text)}"
        if line.kind == "added":
            return f"추가: {redact_sensitive_text(line.target_text)}"
        if line.kind == "removed":
            return f"삭제: {redact_sensitive_text(line.base_text)}"
        return redact_sensitive_text(line.target_text or line.base_text)

    @staticmethod
    def _severity_guidance(severity: str) -> str:
        return {
            "Critical": "작업 영향 가능성이 높으므로 장비 상태와 이중화 경로를 즉시 확인하세요.",
            "Warning": "승인된 작업 범위 안의 변화인지 확인하고 필요 시 원본 리포트에서 주변 문맥을 봅니다.",
            "Info": "상태 변화로 기록하고, 복구 완료 여부나 예상 변화인지 확인합니다.",
            "Unchanged": "의미 있는 변경이 감지되지 않았습니다.",
        }.get(severity, "리포트 원본과 장비 출력을 함께 확인하세요.")

    @staticmethod
    def _shorten(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: max(limit - 1, 0)] + "…"

    def _build_settings_page(self) -> None:
        page = self._make_page("settings")
        page.rowconfigure(1, weight=1)

        access = self._make_section(page, "접속 계정", 0)
        access_body = tk.Frame(access, bg=PALETTE["surface"], padx=16, pady=16)
        access_body.grid(row=1, column=0, sticky="ew")
        access_body.columnconfigure(1, weight=1)
        access_body.columnconfigure(3, weight=1)

        tk.Label(access_body, text="계정", bg=PALETTE["surface"], fg=PALETTE["muted"]).grid(row=0, column=0, sticky="w")
        ttk.Entry(access_body, textvariable=self.username_var).grid(row=0, column=1, sticky="ew", padx=(8, 16))
        tk.Label(access_body, text="암호", bg=PALETTE["surface"], fg=PALETTE["muted"]).grid(row=0, column=2, sticky="w")
        ttk.Entry(access_body, textvariable=self.password_var, show="*").grid(row=0, column=3, sticky="ew", padx=(8, 16))
        tk.Label(access_body, text="제한시간(초)", bg=PALETTE["surface"], fg=PALETTE["muted"]).grid(row=0, column=4, sticky="w")
        ttk.Entry(access_body, textvariable=self.timeout_var, width=8).grid(row=0, column=5, sticky="w", padx=(8, 0))

        devices = self._make_section(page, "대상 장비", 1)
        body = tk.Frame(devices, bg=PALETTE["surface"], padx=16, pady=16)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(2, weight=1)

        headers = ["사용", "장비명", "IP/호스트", "포트", "장비 타입"]
        for column, header in enumerate(headers):
            tk.Label(body, text=header, bg=PALETTE["surface"], fg=PALETTE["muted"], font=("Segoe UI", 9, "bold")).grid(
                row=0, column=column, sticky="w", padx=4, pady=(0, 6)
            )

        for row_index in range(2):
            enabled = tk.BooleanVar(value=True)
            name = tk.StringVar()
            host = tk.StringVar()
            port = tk.StringVar(value="22")
            device_type = tk.StringVar(value="hp_comware")
            self.device_rows.append(
                {
                    "enabled": enabled,
                    "name": name,
                    "host": host,
                    "port": port,
                    "device_type": device_type,
                }
            )
            row = row_index + 1
            ttk.Checkbutton(body, variable=enabled).grid(row=row, column=0, sticky="w", padx=4, pady=4)
            ttk.Entry(body, textvariable=name, width=18).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            ttk.Entry(body, textvariable=host).grid(row=row, column=2, sticky="ew", padx=4, pady=4)
            ttk.Entry(body, textvariable=port, width=8).grid(row=row, column=3, sticky="w", padx=4, pady=4)
            ttk.Entry(body, textvariable=device_type, width=22).grid(row=row, column=4, sticky="ew", padx=4, pady=4)

        actions = tk.Frame(body, bg=PALETTE["surface"])
        actions.grid(row=3, column=0, columnspan=5, sticky="ew", pady=(12, 0))
        ttk.Button(actions, text="장비 목록 불러오기", style="Secondary.TButton", command=self.load_devices_dialog).pack(side="left")
        ttk.Button(actions, text="장비 목록 저장", style="Primary.TButton", command=self.save_devices_to_default).pack(side="left", padx=(8, 0))

    def _build_logs_page(self) -> None:
        page = self._make_page("logs")
        page.rowconfigure(0, weight=1)

        section = self._make_section(page, "작업 로그", 0)
        section.rowconfigure(1, weight=1)
        log_frame = tk.Frame(section, bg=PALETTE["surface"], padx=16, pady=16)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=20,
            wrap="word",
            bg="#0F1720",
            fg="#E6EDF3",
            insertbackground="#E6EDF3",
            relief="flat",
            padx=12,
            pady=12,
            font=("Consolas", 10),
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log("준비 완료. 장비 정보와 접속 계정을 확인한 뒤 작업 단계별 상태를 수집하세요.")

    def show_page(self, page: str) -> None:
        titles = {
            "dashboard": ("대시보드", "백본 3/4호기 작업 상태를 수집하고 변경점을 추적합니다."),
            "collect": ("상태 수집", "작업 전, 백본3 OFF 중, 복구 후 단계별 스냅샷을 생성합니다."),
            "compare": ("비교 결과", "선택한 두 스냅샷의 명령 출력 차이를 리포트로 생성합니다."),
            "settings": ("장비 설정", "백본 3/4호기 접속 계정과 대상 장비 정보를 관리합니다."),
            "logs": ("작업 로그", "수집, 비교, 오류 이력을 시간 순서대로 확인합니다."),
        }
        for key, frame in self.pages.items():
            if key == page:
                frame.tkraise()
            else:
                frame.lower()
        self.current_page = page
        title, description = titles.get(page, titles["dashboard"])
        self.page_title_var.set(title)
        self.page_description_var.set(description)
        self._update_nav_state()

    def _update_nav_state(self) -> None:
        for key, button in self.nav_buttons.items():
            if key == self.current_page:
                button.configure(bg=PALETTE["accent_soft"], fg=PALETTE["accent_dark"])
            else:
                button.configure(bg=PALETTE["sidebar"], fg=PALETTE["text"])

    def _load_initial_devices(self) -> None:
        path = DEVICES_PATH if DEVICES_PATH.exists() else DEVICES_EXAMPLE_PATH
        try:
            self._apply_devices(load_devices(path))
            self.log(f"장비 목록을 불러왔습니다: {path}")
        except Exception as exc:
            self.log(f"장비 목록을 불러오지 못했습니다: {exc}")
        self._refresh_wizard()

    def _apply_devices(self, devices: list[Device]) -> None:
        for row, device in zip(self.device_rows, devices):
            row["enabled"].set(device.enabled)
            row["name"].set(device.name)
            row["host"].set(device.host)
            row["port"].set(str(device.port))
            row["device_type"].set(device.device_type)

    def _read_devices_from_form(self) -> list[Device]:
        devices: list[Device] = []
        for row in self.device_rows:
            name = str(row["name"].get()).strip()
            host = str(row["host"].get()).strip()
            if not name and not host:
                continue
            try:
                port = int(str(row["port"].get()).strip() or "22")
            except ValueError as exc:
                raise ValueError(f"{name or host} 장비의 포트 값이 올바르지 않습니다.") from exc
            devices.append(
                Device(
                    name=name or host,
                    host=host,
                    port=port,
                    device_type=str(row["device_type"].get()).strip() or "hp_comware",
                    enabled=bool(row["enabled"].get()),
                )
            )
        enabled = [device for device in devices if device.enabled]
        if not enabled:
            raise ValueError("사용할 장비를 최소 1대 이상 선택해야 합니다.")
        missing_host = [device.name for device in enabled if not device.host]
        if missing_host:
            raise ValueError(f"IP/호스트가 비어 있습니다: {', '.join(missing_host)}")
        return devices

    def load_devices_dialog(self) -> None:
        path = filedialog.askopenfilename(
            title="장비 목록 YAML 불러오기",
            initialdir=str(CONFIG_DIR),
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self._apply_devices(load_devices(Path(path)))
            self.log(f"장비 목록을 불러왔습니다: {path}")
        except Exception as exc:
            messagebox.showerror("불러오기 실패", str(exc))

    def save_devices_to_default(self) -> None:
        try:
            devices = self._read_devices_from_form()
            save_devices(DEVICES_PATH, devices)
            self.log(f"장비 목록을 저장했습니다: {DEVICES_PATH}")
        except Exception as exc:
            messagebox.showerror("저장 실패", str(exc))

    def collect_stage(self, stage_name: str) -> None:
        self.stage_var.set(stage_name)
        self.collect_snapshot()

    def collect_snapshot(self) -> None:
        try:
            devices = self._read_devices_from_form()
            username = self.username_var.get().strip()
            password = self.password_var.get()
            timeout = int(self.timeout_var.get().strip() or "30")
            stage = resolve_stage(self.stage_var.get(), self.custom_label_var.get())
            if not username:
                raise ValueError("접속 계정을 입력해야 합니다.")
            if not password:
                raise ValueError("암호를 입력해야 합니다.")
        except Exception as exc:
            messagebox.showerror("입력 오류", str(exc))
            return

        self.status_chip_var.set("수집 중")
        self.compare_status_var.set(f"[{stage.name}] 상태 수집 중")
        self.workflow_busy = True
        self._refresh_wizard()

        def worker() -> None:
            try:
                self.thread_log(f"[{stage.name}] 상태 수집을 시작합니다.")
                commands = load_commands(COMMANDS_PATH)
                collector = SnapshotCollector(timeout=timeout, progress=self.thread_log)
                results = collector.collect(devices, commands, username, password)
                snapshot_dir = self.snapshot_store.write_snapshot(
                    stage.name,
                    devices,
                    results,
                    folder_label=build_snapshot_folder_label(stage),
                    stage_name=stage.name,
                    stage_slug=stage.slug,
                )
                self.thread_log(f"[{stage.name}] 스냅샷 저장 완료: {snapshot_dir}")
                self.after(0, lambda: self._select_snapshot_after_collect(snapshot_dir, stage))

                if stage.auto_compare:
                    self._auto_compare_against_pre_work(snapshot_dir)
                else:
                    self.thread_log("[작업 전] 자동 비교 기준으로 지정했습니다.")
                    self.after(0, lambda: self._finish_baseline_collect(snapshot_dir))
            except Exception:
                self.thread_log(traceback.format_exc())
                self.after(0, lambda: self._set_failed_status("수집 실패"))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_baseline_collect(self, snapshot_dir: Path) -> None:
        self.baseline_var.set(snapshot_dir.name)
        self.compare_status_var.set("작업 전 기준 스냅샷이 준비되었습니다.")
        self.status_chip_var.set("기준 준비")
        self.workflow_busy = False
        self._update_diff_details(None)
        self._update_dashboard_metrics()
        self._refresh_wizard()

    def _set_failed_status(self, status: str) -> None:
        self.status_chip_var.set(status)
        self.compare_status_var.set(status)
        self.workflow_busy = False
        self._update_dashboard_metrics()
        self._refresh_wizard()

    def _select_snapshot_after_collect(self, snapshot_dir: Path, stage: WorkStage) -> None:
        self.refresh_snapshots(log_message=False)
        self.latest_snapshot_var.set(snapshot_dir.name)
        if stage.name == PRE_WORK_STAGE:
            self.baseline_var.set(snapshot_dir.name)
        elif stage.name == BB3_OFF_STAGE:
            self.target_var.set(snapshot_dir.name)
            self.off_review_confirmed = False
        elif stage.name == POST_RESTORE_STAGE:
            self.target_var.set(snapshot_dir.name)
            self.final_review_confirmed = False
        else:
            self.target_var.set(snapshot_dir.name)
        self._update_dashboard_metrics()
        self._refresh_wizard()

    def _auto_compare_against_pre_work(self, target_dir: Path) -> None:
        snapshot_dirs = [path for path in self.snapshot_store.list_snapshots() if path != target_dir]
        baseline_dir = find_latest_pre_work_snapshot(snapshot_dirs)
        if baseline_dir is None:
            self.thread_log("작업 전 스냅샷이 없어 자동 비교를 건너뜁니다. 먼저 [작업 전] 상태를 수집하세요.")
            self.after(0, lambda: self._set_failed_status("기준 없음"))
            return

        summary, paths = self._compare_snapshot_dirs(baseline_dir, target_dir)
        counts = summary.counts
        self.thread_log(f"자동 비교 완료: {self._format_counts(counts)}")
        self.thread_log(f"HTML 리포트: {paths['html']}")
        self.thread_log(f"공유 ZIP: {paths['share_zip']}")
        self.after(
            0,
            lambda summary=summary, html_path=paths["html"], share_zip_path=paths["share_zip"]: self._select_compared_snapshots(
                baseline_dir.name,
                target_dir.name,
                "자동 비교 완료",
                summary,
                html_path,
                share_zip_path,
            ),
        )

    def _select_compared_snapshots(
        self,
        baseline_name: str,
        target_name: str,
        status: str,
        summary: DiffSummary | None = None,
        report_path: Path | None = None,
        share_bundle_path: Path | None = None,
    ) -> None:
        self.refresh_snapshots(log_message=False)
        self.baseline_var.set(baseline_name)
        self.target_var.set(target_name)
        self.compare_status_var.set(status)
        self.status_chip_var.set("비교 완료")
        self.workflow_busy = False
        if summary is not None:
            self._apply_compare_summary(summary)
        if report_path is not None:
            self.latest_report = report_path
            self.latest_report_var.set(report_path.name)
        if share_bundle_path is not None:
            self.latest_share_bundle = share_bundle_path
            self.latest_share_bundle_var.set(share_bundle_path.name)
        self._update_dashboard_metrics()

    def refresh_snapshots(self, log_message: bool = True) -> None:
        snapshots = self.snapshot_store.list_snapshots()
        values = [path.name for path in snapshots]
        self.baseline_combo["values"] = values
        self.target_combo["values"] = values

        latest_pre = find_latest_pre_work_snapshot(snapshots)
        if latest_pre is not None and (not self.baseline_var.get() or self.baseline_var.get() not in values):
            self.baseline_var.set(latest_pre.name)
        if values and (not self.target_var.get() or self.target_var.get() not in values):
            self.target_var.set(values[-1])
        self.latest_snapshot_var.set(values[-1] if values else "-")
        if log_message:
            self.log(f"스냅샷 목록을 새로고침했습니다: {len(values)}개")
        self._update_dashboard_metrics()
        self._refresh_wizard()

    def compare_selected(self) -> None:
        base_name = self.baseline_var.get()
        target_name = self.target_var.get()
        if not base_name or not target_name:
            messagebox.showerror("비교 오류", "기준 스냅샷과 비교 스냅샷을 모두 선택하세요.")
            return
        if base_name == target_name:
            messagebox.showerror("비교 오류", "기준 스냅샷과 비교 스냅샷은 달라야 합니다.")
            return

        self.status_chip_var.set("비교 중")
        self.compare_status_var.set("선택 항목 비교 중")
        self.workflow_busy = True
        self._refresh_wizard()

        def worker() -> None:
            try:
                base_dir = OUTPUT_DIR / base_name
                target_dir = OUTPUT_DIR / target_name
                summary, paths = self._compare_snapshot_dirs(base_dir, target_dir)
                counts = summary.counts
                self.thread_log(f"수동 비교 완료: {self._format_counts(counts)}")
                self.thread_log(f"HTML 리포트: {paths['html']}")
                self.thread_log(f"공유 ZIP: {paths['share_zip']}")
                self.after(
                    0,
                    lambda summary=summary, html_path=paths["html"], share_zip_path=paths["share_zip"]: self._finish_manual_compare(
                        summary,
                        html_path,
                        share_zip_path,
                    ),
                )
            except Exception:
                self.thread_log(traceback.format_exc())
                self.after(0, lambda: self._set_failed_status("비교 실패"))

        self.log(f"선택 항목을 비교합니다: {base_name} -> {target_name}")
        threading.Thread(target=worker, daemon=True).start()

    def create_mock_validation(self) -> None:
        self.status_chip_var.set("샘플 생성 중")
        self.compare_status_var.set("샘플 검증 데이터 생성 중")
        try:
            result = create_mock_validation_artifacts(self.snapshot_store)
        except Exception:
            self.log(traceback.format_exc())
            self._set_failed_status("샘플 생성 실패")
            return

        self.log(f"샘플 작업 전 스냅샷: {result.pre_snapshot}")
        self.log(f"샘플 백본3 OFF 스냅샷: {result.off_snapshot}")
        self.log(f"샘플 복구 후 스냅샷: {result.restore_snapshot}")
        self.log(f"샘플 OFF 비교 리포트: {result.off_report}")
        self.log(f"샘플 복구 비교 리포트: {result.restore_report}")
        self.log(f"샘플 OFF 대비 복구 비교 리포트: {result.restore_from_off_report}")
        self.log(f"샘플 OFF 공유 ZIP: {result.off_share_zip}")
        self._select_compared_snapshots(
            result.pre_snapshot.name,
            result.off_snapshot.name,
            "샘플 검증 생성 완료",
            result.off_summary,
            result.off_report,
            result.off_share_zip,
        )
        self.latest_snapshot_var.set(result.restore_snapshot.name)
        self.show_page("compare")

    def _finish_manual_compare(self, summary: DiffSummary, report_path: Path, share_bundle_path: Path | None = None) -> None:
        self.latest_report = report_path
        self.latest_report_var.set(report_path.name)
        if share_bundle_path is not None:
            self.latest_share_bundle = share_bundle_path
            self.latest_share_bundle_var.set(share_bundle_path.name)
        self.compare_status_var.set("선택 항목 비교 완료")
        self.status_chip_var.set("비교 완료")
        self.workflow_busy = False
        self._apply_compare_summary(summary)
        self._update_dashboard_metrics()
        self._refresh_wizard()

    def _apply_compare_summary(self, summary: DiffSummary) -> None:
        self.last_diff_summary = summary
        self._apply_compare_counts(summary.counts)
        self._update_diff_details(summary)
        self._refresh_wizard()

    def _apply_compare_counts(self, counts: dict[str, int]) -> None:
        self.last_counts = {key: int(counts.get(key, 0)) for key in SEVERITY_META}
        for key, value in self.last_counts.items():
            self.metric_vars[key].set(str(value))

    def _update_dashboard_metrics(self) -> None:
        self.baseline_display_var.set(self.baseline_var.get() or "-")
        self.target_display_var.set(self.target_var.get() or "-")
        if self.latest_report and self.latest_report.exists():
            self.latest_report_var.set(self.latest_report.name)
        if self.latest_share_bundle and self.latest_share_bundle.exists():
            self.latest_share_bundle_var.set(self.latest_share_bundle.name)
        self._refresh_wizard()

    @staticmethod
    def _format_counts(counts: dict[str, int]) -> str:
        return (
            f"긴급={counts.get('Critical', 0)}, "
            f"주의={counts.get('Warning', 0)}, "
            f"정보={counts.get('Info', 0)}, "
            f"변경없음={counts.get('Unchanged', 0)}"
        )

    @staticmethod
    def _compare_snapshot_dirs(base_dir: Path, target_dir: Path):
        summary = DiffEngine().compare(base_dir, target_dir)
        paths = ReportWriter().write_reports(summary)
        return summary, paths

    def open_last_report(self) -> None:
        if self.latest_report and self.latest_report.exists():
            os.startfile(self.latest_report)
            return
        messagebox.showinfo("리포트 없음", "현재 실행 세션에서 생성된 비교 리포트가 없습니다.")

    def open_last_share_bundle(self) -> None:
        if self.latest_share_bundle and self.latest_share_bundle.exists():
            os.startfile(self.latest_share_bundle)
            return
        if self.latest_report and self.latest_report.exists():
            try:
                self.latest_share_bundle = create_share_report_bundle(self.latest_report.parent)
                self.latest_share_bundle_var.set(self.latest_share_bundle.name)
                os.startfile(self.latest_share_bundle)
                return
            except Exception:
                self.log(traceback.format_exc())
        messagebox.showinfo("공유 ZIP 없음", "먼저 비교 리포트를 생성한 뒤 공유 ZIP을 열 수 있습니다.")

    def open_outputs(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(OUTPUT_DIR)

    def open_doc(self, file_name: str) -> None:
        path = DOCS_DIR / file_name
        if path.exists():
            os.startfile(path)
            return
        messagebox.showinfo("문서 없음", f"문서를 찾을 수 없습니다: {path}")

    def thread_log(self, message: str) -> None:
        self.after(0, lambda: self.log(message))

    def log(self, message: str) -> None:
        self.log_text.insert("end", redact_sensitive_text(message) + "\n")
        self.log_text.see("end")


def main() -> None:
    app = BackboneStateTrackerApp()
    app.mainloop()


def smoke_check() -> None:
    app = BackboneStateTrackerApp()
    app.update()
    print(app.title())
    print(f"pages={','.join(sorted(app.pages))}")
    app.destroy()


def _copy_if_missing(source: Path, target: Path) -> None:
    if target.exists() or not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
