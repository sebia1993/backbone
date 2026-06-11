from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import CommandResult, Device, Snapshot
from .redaction import redact_payload, redact_sensitive_text
from .version import APP_NAME, APP_VERSION


def sanitize_filename(value: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    cleaned = cleaned.strip("._")
    return cleaned or fallback


def read_text_lossless(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


class SnapshotStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def write_snapshot(
        self,
        label: str,
        devices: list[Device],
        results_by_device: dict[str, list[CommandResult]],
        folder_label: str | None = None,
        stage_name: str = "",
        stage_slug: str = "",
    ) -> Path:
        now = datetime.now()
        created_at = now.isoformat(timespec="seconds")
        stamp = now.strftime("%Y%m%d_%H%M%S")
        safe_label = sanitize_filename(folder_label or label, "snapshot")
        snapshot_dir = self._unique_snapshot_dir(stamp, safe_label)
        raw_dir = snapshot_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        metadata_results: list[dict[str, Any]] = []
        for device in devices:
            device_results = results_by_device.get(device.name, [])
            device_dir = raw_dir / sanitize_filename(device.name)
            device_dir.mkdir(parents=True, exist_ok=True)
            combined_lines: list[str] = []
            for result in device_results:
                raw_name = f"{sanitize_filename(result.command_id)}.txt"
                raw_path = device_dir / raw_name
                raw_path.write_text(result.output or "", encoding="utf-8")
                result.raw_file = str(raw_path.relative_to(snapshot_dir))
                metadata = redact_payload(result.to_metadata())
                metadata["sha256"] = hashlib.sha256((result.output or "").encode("utf-8")).hexdigest()
                metadata_results.append(metadata)

                combined_lines.extend(
                    [
                        f"=== {result.command_id} | {redact_sensitive_text(result.command)} ===",
                        f"success: {result.success}",
                        f"started_at: {result.started_at}",
                        f"ended_at: {result.ended_at}",
                        f"error: {redact_sensitive_text(result.error_message)}",
                        "",
                        result.output or "",
                        "",
                    ]
                )
            (device_dir / "_combined.txt").write_text("\n".join(combined_lines), encoding="utf-8")

        metadata_payload = {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "label": label,
            "stage_name": stage_name or label,
            "stage_slug": stage_slug,
            "created_at": created_at,
            "devices": [device.to_safe_dict() for device in devices],
            "results": metadata_results,
        }
        (snapshot_dir / "snapshot.json").write_text(
            json.dumps(metadata_payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return snapshot_dir

    def _unique_snapshot_dir(self, stamp: str, safe_label: str) -> Path:
        base_name = f"{stamp}_{safe_label}"
        candidate = self.root_dir / base_name
        if not candidate.exists():
            return candidate

        for index in range(1, 1000):
            candidate = self.root_dir / f"{base_name}_{index:03d}"
            if not candidate.exists():
                return candidate
        raise RuntimeError(f"Unable to allocate a unique snapshot folder for {base_name}")

    def list_snapshots(self) -> list[Path]:
        snapshots = [path for path in self.root_dir.iterdir() if (path / "snapshot.json").exists()]
        return sorted(snapshots, key=lambda path: path.name)

    @staticmethod
    def load_snapshot(snapshot_dir: Path) -> Snapshot:
        payload = json.loads((snapshot_dir / "snapshot.json").read_text(encoding="utf-8"))
        results = [CommandResult.from_metadata(item) for item in payload.get("results", [])]
        return Snapshot(
            path=str(snapshot_dir),
            label=str(payload.get("label", snapshot_dir.name)),
            created_at=str(payload.get("created_at", "")),
            devices=list(payload.get("devices", [])),
            results=results,
            stage_name=str(payload.get("stage_name", payload.get("label", ""))),
            stage_slug=str(payload.get("stage_slug", "")),
        )
