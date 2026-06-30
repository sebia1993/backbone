from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


from .version import APP_NAME, APP_VERSION


@dataclass
class Device:
    name: str
    host: str
    port: int = 22
    device_type: str = "hp_comware"
    enabled: bool = True

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "Device":
        return cls(
            name=str(payload.get("name", "")).strip(),
            host=str(payload.get("host", "")).strip(),
            port=int(payload.get("port", 22) or 22),
            device_type=str(payload.get("device_type", "hp_comware")).strip() or "hp_comware",
            enabled=bool(payload.get("enabled", True)),
        )

    def to_safe_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CommandSpec:
    id: str
    command: str
    description: str = ""
    category: str = "general"
    phase: str = "check"
    allow_failure: bool = True
    timeout: int = 30

    @classmethod
    def from_mapping(cls, payload: dict[str, Any], default_phase: str = "check") -> "CommandSpec":
        return cls(
            id=str(payload.get("id", "")).strip(),
            command=str(payload.get("command", "")).strip(),
            description=str(payload.get("description", "")).strip(),
            category=str(payload.get("category", "general")).strip() or "general",
            phase=str(payload.get("phase", default_phase)).strip() or default_phase,
            allow_failure=bool(payload.get("allow_failure", True)),
            timeout=int(payload.get("timeout", 30) or 30),
        )


@dataclass
class CommandResult:
    device_name: str
    host: str
    command_id: str
    command: str
    description: str = ""
    category: str = "general"
    phase: str = "check"
    success: bool = True
    output: str = ""
    error_message: str = ""
    started_at: str = ""
    ended_at: str = ""
    elapsed_seconds: float = 0.0
    raw_file: str = ""
    sha256: str = ""

    @classmethod
    def started(cls, device: Device, command: CommandSpec) -> "CommandResult":
        return cls(
            device_name=device.name,
            host=device.host,
            command_id=command.id,
            command=command.command,
            description=command.description,
            category=command.category,
            phase=command.phase,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )

    def finish(self) -> "CommandResult":
        self.ended_at = datetime.now().isoformat(timespec="seconds")
        try:
            start_dt = datetime.fromisoformat(self.started_at)
            end_dt = datetime.fromisoformat(self.ended_at)
            self.elapsed_seconds = round((end_dt - start_dt).total_seconds(), 3)
        except ValueError:
            self.elapsed_seconds = 0.0
        return self

    def to_metadata(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("output", None)
        return payload

    @classmethod
    def from_metadata(cls, payload: dict[str, Any]) -> "CommandResult":
        return cls(**payload)


@dataclass
class Snapshot:
    path: str
    label: str
    created_at: str
    devices: list[dict[str, Any]]
    results: list[CommandResult]
    stage_name: str = ""
    stage_slug: str = ""


@dataclass
class DiffLine:
    kind: str
    base_line_no: int | None = None
    target_line_no: int | None = None
    base_text: str = ""
    target_text: str = ""


@dataclass
class DiffItem:
    device_name: str
    command_id: str
    command: str
    category: str
    severity: str
    status: str
    summary: str
    diff: str = ""
    base_raw_file: str = ""
    target_raw_file: str = ""
    changed_lines: list[DiffLine] = field(default_factory=list)
    change_count: int = 0
    change_preview: str = ""
    finding_title: str = ""
    impact_reason: str = ""
    evidence: str = ""
    action_hint: str = ""
    expectation: str = "unknown"
    priority: int = 50


@dataclass
class DiffSummary:
    base_snapshot: str
    target_snapshot: str
    generated_at: str
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    items: list[DiffItem] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        counts = {"Critical": 0, "Warning": 0, "Info": 0, "Unchanged": 0}
        for item in self.items:
            counts[item.severity] = counts.get(item.severity, 0) + 1
        return counts
