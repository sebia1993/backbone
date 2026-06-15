from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from .codes import DiagnosticCode
from ..version import APP_VERSION


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class DiagnosticEvent:
    timestamp: str
    app_version: str
    stage: str
    code: str
    severity: str
    status: str
    summary: str
    action_hint: str
    device_alias: str = ""
    safe_detail: str = ""
    raw_log_included: bool = False

    @classmethod
    def from_code(
        cls,
        code: DiagnosticCode,
        *,
        stage: str | None = None,
        status: str = "info",
        device_alias: str = "",
        safe_detail: str = "",
        summary: str | None = None,
        app_version: str = APP_VERSION,
    ) -> "DiagnosticEvent":
        return cls(
            timestamp=utc_timestamp(),
            app_version=app_version,
            stage=stage or code.area,
            code=code.code,
            severity=code.severity,
            status=status,
            summary=summary or code.summary,
            action_hint=code.action_hint,
            device_alias=device_alias,
            safe_detail=safe_detail,
            raw_log_included=False,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
