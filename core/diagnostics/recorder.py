from __future__ import annotations

import re
from dataclasses import dataclass, field

from .codes import DiagnosticCode, get_code
from .events import DiagnosticEvent
from ..redaction import redact_sensitive_text
from ..version import APP_VERSION


_IPV4_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
_KEYED_HOST_PATTERN = re.compile(
    r"(?i)\b(?P<key>host|hostname|ip|address|device|device_name)\s*=\s*(?P<value>[A-Za-z0-9_.:-]+)"
)


@dataclass
class AliasRegistry:
    device_aliases: dict[str, str] = field(default_factory=dict)
    ip_aliases: dict[str, str] = field(default_factory=dict)
    host_aliases: dict[str, str] = field(default_factory=dict)

    def device_alias(self, value: str) -> str:
        return self._alias(self.device_aliases, value, "DEV")

    def ip_alias(self, value: str) -> str:
        return self._alias(self.ip_aliases, value, "IP-ALIAS")

    def host_alias(self, value: str) -> str:
        return self._alias(self.host_aliases, value, "HOST-ALIAS")

    @staticmethod
    def _alias(store: dict[str, str], value: str, prefix: str) -> str:
        key = str(value or "").strip()
        if not key:
            return ""
        if key not in store:
            store[key] = f"{prefix}-{len(store) + 1:03d}"
        return store[key]


class DiagnosticRecorder:
    def __init__(self, app_version: str = APP_VERSION) -> None:
        self.app_version = app_version
        self.aliases = AliasRegistry()
        self._events: list[DiagnosticEvent] = []

    @property
    def events(self) -> tuple[DiagnosticEvent, ...]:
        return tuple(self._events)

    def record(
        self,
        code: str | DiagnosticCode,
        *,
        stage: str | None = None,
        status: str = "info",
        device_identity: str = "",
        safe_detail: str = "",
        summary: str | None = None,
    ) -> DiagnosticEvent:
        code_obj = code if isinstance(code, DiagnosticCode) else get_code(code)
        if code_obj is None:
            raise ValueError(f"Unknown diagnostic code: {code}")
        event = DiagnosticEvent.from_code(
            code_obj,
            stage=stage,
            status=status,
            device_alias=self.aliases.device_alias(device_identity),
            safe_detail=self.mask_text(safe_detail),
            summary=self.mask_text(summary) if summary else None,
            app_version=self.app_version,
        )
        self._events.append(event)
        return event

    def mask_text(self, value: str | None) -> str:
        text = redact_sensitive_text(str(value or ""))

        def replace_keyed_host(match: re.Match[str]) -> str:
            key = match.group("key")
            value = match.group("value")
            key_lower = key.lower()
            if key_lower in {"ip", "address"} and _IPV4_PATTERN.fullmatch(value):
                alias = self.aliases.ip_alias(value)
            elif key_lower.startswith("device"):
                alias = self.aliases.device_alias(value)
            else:
                alias = self.aliases.host_alias(value)
            return f"{key}={alias}"

        text = _KEYED_HOST_PATTERN.sub(replace_keyed_host, text)
        return _IPV4_PATTERN.sub(lambda match: self.aliases.ip_alias(match.group(0)), text)

    def counts_by_severity(self) -> dict[str, int]:
        counts = {"Critical": 0, "Warning": 0, "Info": 0}
        for event in self._events:
            counts[event.severity] = counts.get(event.severity, 0) + 1
        return counts
