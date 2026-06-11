from __future__ import annotations

from datetime import datetime

from .models import CommandResult, Device
from .redaction import redact_sensitive_text


DEVICE_CONNECTIVITY_COMMAND_ID = "device_connectivity"
DEVICE_CONNECTIVITY_COMMAND = "connect"
DEVICE_CONNECTIVITY_DESCRIPTION = "Device connection status"
DEVICE_CONNECTIVITY_CATEGORY = "connection"
REACHABLE_OUTPUT = "reachable"
LEGACY_CONNECTION_FAILURE_IDS = {"authentication_failed", "timeout_failed", "connection_failed"}


def make_connectivity_result(
    device: Device,
    success: bool,
    reason: str = "",
    error_message: str = "",
) -> CommandResult:
    started_at = datetime.now().isoformat(timespec="seconds")
    return make_connectivity_result_for_device(
        device_name=device.name,
        host=device.host,
        success=success,
        reason=reason,
        error_message=error_message,
        started_at=started_at,
        ended_at=started_at,
    )


def make_connectivity_result_for_device(
    device_name: str,
    host: str,
    success: bool,
    reason: str = "",
    error_message: str = "",
    started_at: str = "",
    ended_at: str = "",
) -> CommandResult:
    return CommandResult(
        device_name=device_name,
        host=host,
        command_id=DEVICE_CONNECTIVITY_COMMAND_ID,
        command=DEVICE_CONNECTIVITY_COMMAND,
        description=DEVICE_CONNECTIVITY_DESCRIPTION,
        category=DEVICE_CONNECTIVITY_CATEGORY,
        phase="check",
        success=success,
        output=format_connectivity_output(success, reason),
        error_message=sanitize_connection_error(error_message),
        started_at=started_at,
        ended_at=ended_at,
    )


def format_connectivity_output(success: bool, reason: str = "") -> str:
    if success:
        return REACHABLE_OUTPUT
    return f"unreachable: {normalize_connection_reason(reason)}"


def normalize_connection_reason(reason: str) -> str:
    cleaned = (reason or "connection").strip().lower().replace("_", "-")
    return cleaned or "connection"


def sanitize_connection_error(message: str) -> str:
    text = " ".join(redact_sensitive_text(message or "").split())
    if len(text) > 300:
        return text[:297] + "..."
    return text


def is_connectivity_result(result: CommandResult) -> bool:
    return result.command_id == DEVICE_CONNECTIVITY_COMMAND_ID


def is_legacy_connection_failure(result: CommandResult) -> bool:
    return (
        result.command_id in LEGACY_CONNECTION_FAILURE_IDS
        and result.category == DEVICE_CONNECTIVITY_CATEGORY
        and not result.success
    )


def legacy_failure_reason(result: CommandResult) -> str:
    if result.command_id.endswith("_failed"):
        return result.command_id[: -len("_failed")]
    return "connection"
