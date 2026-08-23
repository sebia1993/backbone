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

# 접속 실패는 원본 예외 메시지보다 코드가 중요합니다. 운영자가 외부에
# BST-CON-* 코드만 전달해도 원인 범위를 좁힐 수 있게 reason을 표준 코드로 바꿉니다.
CONNECTION_REASON_CODES = {
    "host-key": "BST-SEC-002",
    "timeout": "BST-CON-301",
    "authentication": "BST-CON-302",
    "auth": "BST-CON-302",
    "telnet": "BST-CON-303",
    "connection": "BST-CON-304",
    "refused": "BST-CON-304",
}


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
    # 연결 실패 결과도 일반 명령 결과와 같은 모델로 저장합니다.
    # 이렇게 하면 비교 엔진과 HTML 리포트가 별도 예외 처리 없이 같은 방식으로 표시합니다.
    diagnostic_code = diagnostic_code_for_connection_reason(reason) if not success else ""
    sanitized_error = sanitize_connection_error(error_message)
    if diagnostic_code and sanitized_error:
        sanitized_error = f"{diagnostic_code} {sanitized_error}"
    elif diagnostic_code:
        sanitized_error = diagnostic_code
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
        error_message=sanitized_error,
        started_at=started_at,
        ended_at=ended_at,
    )


def format_connectivity_output(success: bool, reason: str = "") -> str:
    if success:
        return REACHABLE_OUTPUT
    normalized = normalize_connection_reason(reason)
    return f"unreachable: {normalized} ({diagnostic_code_for_connection_reason(normalized)})"


def normalize_connection_reason(reason: str) -> str:
    cleaned = (reason or "connection").strip().lower().replace("_", "-")
    return cleaned or "connection"


def diagnostic_code_for_connection_reason(reason: str) -> str:
    normalized = normalize_connection_reason(reason)
    for key, code in CONNECTION_REASON_CODES.items():
        if key in normalized:
            return code
    return CONNECTION_REASON_CODES["connection"]


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
