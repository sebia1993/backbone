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
from .models import Device
from .paths import resource_root, runtime_root
from .reporter import ReportWriter
from .snapshot import SnapshotStore
from .version import APP_NAME, APP_VERSION
from .workflow import (
    PRE_WORK_STAGE,
    WORK_STAGE_BY_NAME,
    WORK_STAGE_NAMES,
    WorkStage,
    build_snapshot_folder_label,
    find_latest_pre_work_snapshot,
    resolve_stage,
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


class BackboneStateTrackerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1180x780")
        self.minsize(1020, 720)

        self.snapshot_store = SnapshotStore(OUTPUT_DIR)
        self.latest_report: Path | None = None
        self.device_rows: list[dict[str, tk.Variable]] = []

        self._ensure_runtime_config_files()

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.timeout_var = tk.StringVar(value="30")
        self.stage_var = tk.StringVar(value=PRE_WORK_STAGE)
        self.custom_label_var = tk.StringVar()
        self.baseline_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.compare_status_var = tk.StringVar(value="작업 전 스냅샷을 수집하면 자동 비교 기준으로 지정됩니다.")

        self._build_menu()
        self._build_ui()
        self._load_initial_devices()
        self.refresh_snapshots(log_message=False)

    def _ensure_runtime_config_files(self) -> None:
        _copy_if_missing(BUNDLED_CONFIG_DIR / "commands.yaml", COMMANDS_PATH)
        _copy_if_missing(BUNDLED_CONFIG_DIR / "devices.example.yaml", DEVICES_EXAMPLE_PATH)

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="결과 폴더 열기", command=self.open_outputs)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.destroy)
        menu_bar.add_cascade(label="파일", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="사용자 가이드 열기", command=lambda: self.open_doc("USER_GUIDE.html"))
        help_menu.add_command(label="버전 변경내용 열기", command=lambda: self.open_doc("VERSION_HISTORY.html"))
        menu_bar.add_cascade(label="도움말", menu=help_menu)

        self.config(menu=menu_bar)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        header = ttk.Frame(self, padding=(12, 10, 12, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text=f"백본 상태 비교 추적 도구 v{APP_VERSION}",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="백본 3/4호기 작업 전, OFF 중, 복구 후 상태를 수집하고 작업 전 기준으로 자동 비교합니다.",
            foreground="#59636e",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self._build_step_connection()
        self._build_step_collection()
        self._build_step_compare()
        self._build_log()

    def _build_step_connection(self) -> None:
        frame = ttk.LabelFrame(self, text="1. 장비 및 접속 설정", padding=10)
        frame.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        frame.columnconfigure(7, weight=1)

        ttk.Label(frame, text="접속 계정").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.username_var).grid(row=0, column=1, sticky="ew", padx=(6, 16))
        ttk.Label(frame, text="암호").grid(row=0, column=2, sticky="w")
        ttk.Entry(frame, textvariable=self.password_var, show="*").grid(row=0, column=3, sticky="ew", padx=(6, 16))
        ttk.Label(frame, text="제한시간(초)").grid(row=0, column=4, sticky="w")
        ttk.Entry(frame, textvariable=self.timeout_var, width=8).grid(row=0, column=5, sticky="w", padx=(6, 16))

        device_header = ttk.Frame(frame)
        device_header.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(12, 2))
        headers = ["사용", "장비명", "IP/호스트", "포트", "장비 타입"]
        for col, header in enumerate(headers):
            ttk.Label(device_header, text=header, font=("Segoe UI", 9, "bold")).grid(row=0, column=col, sticky="w", padx=4)
        device_header.columnconfigure(2, weight=1)

        device_grid = ttk.Frame(frame)
        device_grid.grid(row=2, column=0, columnspan=8, sticky="ew")
        device_grid.columnconfigure(2, weight=1)
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
            row = row_index
            ttk.Checkbutton(device_grid, variable=enabled).grid(row=row, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(device_grid, textvariable=name, width=18).grid(row=row, column=1, sticky="ew", padx=4, pady=3)
            ttk.Entry(device_grid, textvariable=host).grid(row=row, column=2, sticky="ew", padx=4, pady=3)
            ttk.Entry(device_grid, textvariable=port, width=8).grid(row=row, column=3, sticky="w", padx=4, pady=3)
            ttk.Entry(device_grid, textvariable=device_type, width=22).grid(row=row, column=4, sticky="ew", padx=4, pady=3)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=8, sticky="ew", pady=(8, 0))
        ttk.Button(button_frame, text="장비 목록 불러오기", command=self.load_devices_dialog).pack(side="left")
        ttk.Button(button_frame, text="장비 목록 저장", command=self.save_devices_to_default).pack(side="left", padx=(8, 0))

    def _build_step_collection(self) -> None:
        frame = ttk.LabelFrame(self, text="2. 작업 단계 선택 및 상태 수집", padding=10)
        frame.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        frame.columnconfigure(5, weight=1)

        ttk.Label(frame, text="작업 단계").grid(row=0, column=0, sticky="w", padx=(0, 8))
        for index, stage_name in enumerate(WORK_STAGE_NAMES, start=1):
            ttk.Radiobutton(
                frame,
                text=stage_name,
                value=stage_name,
                variable=self.stage_var,
            ).grid(row=0, column=index, sticky="w", padx=4)

        ttk.Label(frame, text="사용자 지정명").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.custom_label_var).grid(row=1, column=1, columnspan=4, sticky="ew", padx=(0, 12), pady=(10, 0))
        ttk.Button(frame, text="상태 수집 시작", command=self.collect_snapshot).grid(row=1, column=5, sticky="e", pady=(10, 0))

    def _build_step_compare(self) -> None:
        frame = ttk.LabelFrame(self, text="3. 자동 비교 및 결과 확인", padding=10)
        frame.grid(row=3, column=0, sticky="ew", padx=12, pady=6)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text="기준 스냅샷(작업 전)").grid(row=0, column=0, sticky="w")
        self.baseline_combo = ttk.Combobox(frame, textvariable=self.baseline_var, state="readonly")
        self.baseline_combo.grid(row=0, column=1, sticky="ew", padx=(6, 14))
        ttk.Label(frame, text="비교 스냅샷").grid(row=0, column=2, sticky="w")
        self.target_combo = ttk.Combobox(frame, textvariable=self.target_var, state="readonly")
        self.target_combo.grid(row=0, column=3, sticky="ew", padx=(6, 14))

        ttk.Button(frame, text="목록 새로고침", command=self.refresh_snapshots).grid(row=0, column=4, sticky="e")

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(8, 0))
        ttk.Button(action_frame, text="선택 항목 다시 비교", command=self.compare_selected).pack(side="left")
        ttk.Button(action_frame, text="최근 리포트 열기", command=self.open_last_report).pack(side="left", padx=(8, 0))
        ttk.Button(action_frame, text="결과 폴더 열기", command=self.open_outputs).pack(side="left", padx=(8, 0))
        ttk.Label(action_frame, textvariable=self.compare_status_var, foreground="#59636e").pack(side="left", padx=(16, 0))

    def _build_log(self) -> None:
        frame = ttk.LabelFrame(self, text="작업 로그", padding=8)
        frame.grid(row=4, column=0, sticky="nsew", padx=12, pady=(6, 12))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(frame, height=14, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log("준비 완료. 장비 정보와 접속 계정을 확인한 뒤 작업 단계를 선택하세요.")

    def _load_initial_devices(self) -> None:
        path = DEVICES_PATH if DEVICES_PATH.exists() else DEVICES_EXAMPLE_PATH
        try:
            self._apply_devices(load_devices(path))
            self.log(f"장비 목록을 불러왔습니다: {path}")
        except Exception as exc:
            self.log(f"장비 목록을 불러오지 못했습니다: {exc}")

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
                    self.after(0, lambda: self.compare_status_var.set("작업 전 기준 스냅샷이 준비되었습니다."))
            except Exception:
                self.thread_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _select_snapshot_after_collect(self, snapshot_dir: Path, stage: WorkStage) -> None:
        self.refresh_snapshots(log_message=False)
        if stage.name == PRE_WORK_STAGE:
            self.baseline_var.set(snapshot_dir.name)
        else:
            self.target_var.set(snapshot_dir.name)

    def _auto_compare_against_pre_work(self, target_dir: Path) -> None:
        snapshot_dirs = [path for path in self.snapshot_store.list_snapshots() if path != target_dir]
        baseline_dir = find_latest_pre_work_snapshot(snapshot_dirs)
        if baseline_dir is None:
            self.thread_log("작업 전 스냅샷이 없어 자동 비교를 건너뜁니다. 먼저 [작업 전] 상태를 수집하세요.")
            self.after(0, lambda: self.compare_status_var.set("작업 전 스냅샷이 없어 자동 비교를 건너뜀"))
            return

        summary, paths = self._compare_snapshot_dirs(baseline_dir, target_dir)
        counts = summary.counts
        self.latest_report = paths["html"]
        self.thread_log(
            "자동 비교 완료: "
            f"긴급={counts.get('Critical', 0)}, "
            f"주의={counts.get('Warning', 0)}, "
            f"정보={counts.get('Info', 0)}, "
            f"변경없음={counts.get('Unchanged', 0)}"
        )
        self.thread_log(f"HTML 리포트: {paths['html']}")
        self.after(
            0,
            lambda: self._select_compared_snapshots(baseline_dir.name, target_dir.name, "자동 비교 완료"),
        )

    def _select_compared_snapshots(self, baseline_name: str, target_name: str, status: str) -> None:
        self.refresh_snapshots(log_message=False)
        self.baseline_var.set(baseline_name)
        self.target_var.set(target_name)
        self.compare_status_var.set(status)

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
        if log_message:
            self.log(f"스냅샷 목록을 새로고침했습니다: {len(values)}개")

    def compare_selected(self) -> None:
        base_name = self.baseline_var.get()
        target_name = self.target_var.get()
        if not base_name or not target_name:
            messagebox.showerror("비교 오류", "기준 스냅샷과 비교 스냅샷을 모두 선택하세요.")
            return
        if base_name == target_name:
            messagebox.showerror("비교 오류", "기준 스냅샷과 비교 스냅샷은 달라야 합니다.")
            return

        def worker() -> None:
            try:
                base_dir = OUTPUT_DIR / base_name
                target_dir = OUTPUT_DIR / target_name
                summary, paths = self._compare_snapshot_dirs(base_dir, target_dir)
                self.latest_report = paths["html"]
                counts = summary.counts
                self.thread_log(
                    "수동 비교 완료: "
                    f"긴급={counts.get('Critical', 0)}, "
                    f"주의={counts.get('Warning', 0)}, "
                    f"정보={counts.get('Info', 0)}, "
                    f"변경없음={counts.get('Unchanged', 0)}"
                )
                self.thread_log(f"HTML 리포트: {paths['html']}")
                self.after(0, lambda: self.compare_status_var.set("선택 항목 비교 완료"))
            except Exception:
                self.thread_log(traceback.format_exc())

        self.log(f"선택 항목을 비교합니다: {base_name} -> {target_name}")
        threading.Thread(target=worker, daemon=True).start()

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
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")


def main() -> None:
    app = BackboneStateTrackerApp()
    app.mainloop()


def smoke_check() -> None:
    app = BackboneStateTrackerApp()
    app.update()
    print(app.title())
    app.destroy()


def _copy_if_missing(source: Path, target: Path) -> None:
    if target.exists() or not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
