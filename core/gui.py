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


PROJECT_DIR = runtime_root()
RESOURCE_DIR = resource_root()
CONFIG_DIR = PROJECT_DIR / "config"
BUNDLED_CONFIG_DIR = RESOURCE_DIR / "config"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "snapshots"
COMMANDS_PATH = CONFIG_DIR / "commands.yaml"
DEVICES_PATH = CONFIG_DIR / "devices.yaml"
DEVICES_EXAMPLE_PATH = CONFIG_DIR / "devices.example.yaml"


class BackboneStateTrackerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1180x760")
        self.minsize(980, 680)

        self.snapshot_store = SnapshotStore(OUTPUT_DIR)
        self.latest_report: Path | None = None
        self.device_rows: list[dict[str, tk.Variable]] = []

        self._ensure_runtime_config_files()

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.timeout_var = tk.StringVar(value="30")
        self.snapshot_label_var = tk.StringVar(value="pre")
        self.baseline_var = tk.StringVar()
        self.target_var = tk.StringVar()

        self._build_ui()
        self._load_initial_devices()
        self.refresh_snapshots()

    def _ensure_runtime_config_files(self) -> None:
        _copy_if_missing(BUNDLED_CONFIG_DIR / "commands.yaml", COMMANDS_PATH)
        _copy_if_missing(BUNDLED_CONFIG_DIR / "devices.example.yaml", DEVICES_EXAMPLE_PATH)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)

        header = ttk.Frame(self, padding=(12, 10, 12, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=f"{APP_NAME} v{APP_VERSION}", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Read-only snapshot collection and comparison for backbone 3/4.",
            foreground="#59636e",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self._build_credentials()
        self._build_devices()
        self._build_actions()
        self._build_compare()
        self._build_log()

    def _build_credentials(self) -> None:
        frame = ttk.LabelFrame(self, text="Connection", padding=10)
        frame.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        for idx in (1, 3, 5, 7):
            frame.columnconfigure(idx, weight=1)

        ttk.Label(frame, text="Username").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.username_var).grid(row=0, column=1, sticky="ew", padx=(6, 16))
        ttk.Label(frame, text="Password").grid(row=0, column=2, sticky="w")
        ttk.Entry(frame, textvariable=self.password_var, show="*").grid(row=0, column=3, sticky="ew", padx=(6, 16))
        ttk.Label(frame, text="Timeout").grid(row=0, column=4, sticky="w")
        ttk.Entry(frame, textvariable=self.timeout_var, width=8).grid(row=0, column=5, sticky="w", padx=(6, 16))
        ttk.Label(frame, text="Snapshot label").grid(row=0, column=6, sticky="w")
        ttk.Entry(frame, textvariable=self.snapshot_label_var).grid(row=0, column=7, sticky="ew", padx=(6, 0))

    def _build_devices(self) -> None:
        frame = ttk.LabelFrame(self, text="Devices", padding=10)
        frame.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        frame.columnconfigure(2, weight=1)

        headers = ["Use", "Name", "Host", "Port", "Device type"]
        for col, header in enumerate(headers):
            ttk.Label(frame, text=header, font=("Segoe UI", 9, "bold")).grid(row=0, column=col, sticky="w", padx=4)

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
            ttk.Checkbutton(frame, variable=enabled).grid(row=row, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(frame, textvariable=name, width=18).grid(row=row, column=1, sticky="ew", padx=4, pady=3)
            ttk.Entry(frame, textvariable=host).grid(row=row, column=2, sticky="ew", padx=4, pady=3)
            ttk.Entry(frame, textvariable=port, width=8).grid(row=row, column=3, sticky="w", padx=4, pady=3)
            ttk.Entry(frame, textvariable=device_type, width=22).grid(row=row, column=4, sticky="ew", padx=4, pady=3)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=5, sticky="ew", pady=(8, 0))
        ttk.Button(button_frame, text="Load Devices", command=self.load_devices_dialog).pack(side="left")
        ttk.Button(button_frame, text="Save Devices", command=self.save_devices_to_default).pack(side="left", padx=(8, 0))

    def _build_actions(self) -> None:
        frame = ttk.Frame(self, padding=(12, 4))
        frame.grid(row=3, column=0, sticky="ew")
        ttk.Button(frame, text="Collect Snapshot", command=self.collect_snapshot).pack(side="left")
        ttk.Button(frame, text="Compare Selected", command=self.compare_selected).pack(side="left", padx=(8, 0))
        ttk.Button(frame, text="Open Last Report", command=self.open_last_report).pack(side="left", padx=(8, 0))
        ttk.Button(frame, text="Open Outputs", command=self.open_outputs).pack(side="left", padx=(8, 0))

    def _build_compare(self) -> None:
        frame = ttk.LabelFrame(self, text="Snapshot comparison", padding=10)
        frame.grid(row=4, column=0, sticky="ew", padx=12, pady=6)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text="Baseline").grid(row=0, column=0, sticky="w")
        self.baseline_combo = ttk.Combobox(frame, textvariable=self.baseline_var, state="readonly")
        self.baseline_combo.grid(row=0, column=1, sticky="ew", padx=(6, 14))
        ttk.Label(frame, text="Target").grid(row=0, column=2, sticky="w")
        self.target_combo = ttk.Combobox(frame, textvariable=self.target_var, state="readonly")
        self.target_combo.grid(row=0, column=3, sticky="ew", padx=(6, 14))
        ttk.Button(frame, text="Refresh", command=self.refresh_snapshots).grid(row=0, column=4, sticky="e")

    def _build_log(self) -> None:
        frame = ttk.LabelFrame(self, text="Run log", padding=8)
        frame.grid(row=5, column=0, sticky="nsew", padx=12, pady=(6, 12))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(frame, height=14, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log("Ready. Enter device IPs and collect a snapshot.")

    def _load_initial_devices(self) -> None:
        path = DEVICES_PATH if DEVICES_PATH.exists() else DEVICES_EXAMPLE_PATH
        try:
            self._apply_devices(load_devices(path))
            self.log(f"Loaded devices from {path}")
        except Exception as exc:
            self.log(f"Device load failed: {exc}")

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
                raise ValueError(f"Invalid port for {name or host}") from exc
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
            raise ValueError("At least one device must be enabled.")
        missing_host = [device.name for device in enabled if not device.host]
        if missing_host:
            raise ValueError(f"Missing host for: {', '.join(missing_host)}")
        return devices

    def load_devices_dialog(self) -> None:
        path = filedialog.askopenfilename(
            title="Load devices YAML",
            initialdir=str(CONFIG_DIR),
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self._apply_devices(load_devices(Path(path)))
            self.log(f"Loaded devices from {path}")
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))

    def save_devices_to_default(self) -> None:
        try:
            devices = self._read_devices_from_form()
            save_devices(DEVICES_PATH, devices)
            self.log(f"Saved device definitions to {DEVICES_PATH}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def collect_snapshot(self) -> None:
        try:
            devices = self._read_devices_from_form()
            username = self.username_var.get().strip()
            password = self.password_var.get()
            label = self.snapshot_label_var.get().strip() or "snapshot"
            timeout = int(self.timeout_var.get().strip() or "30")
            if not username:
                raise ValueError("Username is required.")
            if not password:
                raise ValueError("Password is required.")
        except Exception as exc:
            messagebox.showerror("Input error", str(exc))
            return

        def worker() -> None:
            try:
                commands = load_commands(COMMANDS_PATH)
                collector = SnapshotCollector(timeout=timeout, progress=self.thread_log)
                results = collector.collect(devices, commands, username, password)
                snapshot_dir = self.snapshot_store.write_snapshot(label, devices, results)
                self.thread_log(f"Snapshot saved: {snapshot_dir}")
                self.after(0, self.refresh_snapshots)
            except Exception:
                self.thread_log(traceback.format_exc())

        self.log("Starting snapshot collection.")
        threading.Thread(target=worker, daemon=True).start()

    def refresh_snapshots(self) -> None:
        snapshots = self.snapshot_store.list_snapshots()
        values = [path.name for path in snapshots]
        self.baseline_combo["values"] = values
        self.target_combo["values"] = values
        if len(values) >= 2:
            if not self.baseline_var.get():
                self.baseline_var.set(values[-2])
            if not self.target_var.get():
                self.target_var.set(values[-1])
        elif len(values) == 1:
            self.target_var.set(values[0])
        self.log(f"Snapshot list refreshed: {len(values)} found.")

    def compare_selected(self) -> None:
        base_name = self.baseline_var.get()
        target_name = self.target_var.get()
        if not base_name or not target_name:
            messagebox.showerror("Compare error", "Select both baseline and target snapshots.")
            return
        if base_name == target_name:
            messagebox.showerror("Compare error", "Baseline and target must be different.")
            return

        def worker() -> None:
            try:
                base_dir = OUTPUT_DIR / base_name
                target_dir = OUTPUT_DIR / target_name
                summary = DiffEngine().compare(base_dir, target_dir)
                paths = ReportWriter().write_reports(summary)
                self.latest_report = paths["html"]
                counts = summary.counts
                self.thread_log(
                    "Comparison complete: "
                    f"Critical={counts.get('Critical', 0)}, "
                    f"Warning={counts.get('Warning', 0)}, "
                    f"Info={counts.get('Info', 0)}, "
                    f"Unchanged={counts.get('Unchanged', 0)}"
                )
                self.thread_log(f"HTML report: {paths['html']}")
            except Exception:
                self.thread_log(traceback.format_exc())

        self.log(f"Comparing {base_name} -> {target_name}")
        threading.Thread(target=worker, daemon=True).start()

    def open_last_report(self) -> None:
        if self.latest_report and self.latest_report.exists():
            os.startfile(self.latest_report)
            return
        messagebox.showinfo("No report", "No comparison report has been generated in this session.")

    def open_outputs(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(OUTPUT_DIR)

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
