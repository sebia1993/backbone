from __future__ import annotations

import re
from typing import Any


MASK = "***"

_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
_AUTH_HEADER_PATTERN = re.compile(
    r"(?i)\b(authorization\s*:\s*)(bearer|basic)\s+([A-Za-z0-9._~+/=-]+)"
)
_URL_CREDENTIAL_PATTERN = re.compile(r"(?i)(://[^/\s:@]+):([^@\s]+)@")
_KEY_VALUE_SECRET_PATTERN = re.compile(
    r"(?ix)"
    r"\b("
    r"password|passwd|pwd|secret|token|api[_-]?key|apikey|"
    r"access[_-]?token|refresh[_-]?token|private[_-]?key"
    r")\b"
    r"(\s*[:=]\s*|\s+)"
    r"(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_CISCO_TYPED_SECRET_PATTERN = re.compile(
    r"(?i)\b((?:enable\s+)?secret)\s+([0-9])\s+([^\s,;]+)"
)
_CISCO_USERNAME_SECRET_PATTERN = re.compile(
    r"(?i)\b(username\s+\S+\s+(?:password|secret))\s+(?:[0-9]\s+)?([^\s,;]+)"
)
_SNMP_COMMUNITY_PATTERN = re.compile(
    r"(?ix)"
    r"\b(snmp-server\s+community|snmp\s+community|community-string|community[_-]?name)"
    r"(\s*[:=]\s*|\s+)"
    r"(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)


def redact_sensitive_text(value: str) -> str:
    if not value:
        return value

    text = str(value)
    text = _PRIVATE_KEY_PATTERN.sub("-----BEGIN REDACTED PRIVATE KEY-----***-----END REDACTED PRIVATE KEY-----", text)
    text = _AUTH_HEADER_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)} {MASK}", text)
    text = _URL_CREDENTIAL_PATTERN.sub(lambda match: f"{match.group(1)}:{MASK}@", text)
    text = _CISCO_TYPED_SECRET_PATTERN.sub(lambda match: f"{match.group(1)} {match.group(2)} {MASK}", text)
    text = _CISCO_USERNAME_SECRET_PATTERN.sub(lambda match: f"{match.group(1)} {MASK}", text)
    text = _SNMP_COMMUNITY_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}{MASK}", text)
    text = _KEY_VALUE_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}{MASK}", text)
    return text


def redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: redact_payload(item) for key, item in value.items()}
    return value
