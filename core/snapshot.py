from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import CommandResult, Device, Snapshot
from .redaction import redact_payload, redact_sensitive_text
from .version import APP_NAME, APP_VERSION

TRANSIENT_WRITE_RETRY_DELAYS = (0.05, 0.1, 0.2)


def sanitize_filename(value: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^\w_.-]+", "_", value.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("._")
    return cleaned or fallback


def atomic_replace_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    last_error: OSError | None = None
    for attempt, delay in enumerate((0.0, *TRANSIENT_WRITE_RETRY_DELAYS)):
        if delay:
            time.sleep(delay)
        try:
            os.replace(source, target)
            return
        except OSError as exc:
            last_error = exc
            if attempt == len(TRANSIENT_WRITE_RETRY_DELAYS):
                break
    if last_error is not None:
        raise last_error


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
        atomic_replace_file(temp_path, path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


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
                atomic_write_text(raw_path, result.output or "")
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
            atomic_write_text(device_dir / "_combined.txt", "\n".join(combined_lines))

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
        atomic_write_text(
            snapshot_dir / "snapshot.json",
            json.dumps(metadata_payload, indent=2, ensure_ascii=True),
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
