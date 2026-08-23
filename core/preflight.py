from __future__ import annotations

from dataclasses import dataclass, field

from .command_safety import (
    SUPPORTED_DEVICE_TYPES,
    CommandSafetyError,
    canonicalize_command,
)
from .models import CommandSpec, Device

DOCUMENTATION_HOST_PREFIXES = ("192.0.2.", "198.51.100.", "203.0.113.")


@dataclass(frozen=True)
class PreflightIssue:
    severity: str
    area: str
    message: str
    detail: str = ""


@dataclass
class PreflightResult:
    issues: list[PreflightIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "info")

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0

    def add(self, severity: str, area: str, message: str, detail: str = "") -> None:
        self.issues.append(PreflightIssue(severity=severity, area=area, message=message, detail=detail))


def validate_preflight(devices: list[Device], commands: list[CommandSpec]) -> PreflightResult:
    result = PreflightResult()
    validate_devices(devices, result)
    validate_commands(commands, result)
    if not result.issues:
        result.add("info", "summary", "설정 점검 통과", "차단 오류나 주의 항목이 없습니다.")
    return result


def validate_devices(devices: list[Device], result: PreflightResult) -> None:
    enabled_devices = [device for device in devices if device.enabled]
    if not enabled_devices:
        result.add("error", "device", "사용 설정된 장비가 없습니다.", "백본 3/4호기 중 최소 1대 이상을 사용으로 설정하세요.")
        return
    if len(enabled_devices) < 2:
        result.add("warning", "device", "사용 장비가 1대뿐입니다.", "백본 3/4호기 작업 검증에는 보통 2대가 필요합니다.")

    seen_names: dict[str, int] = {}
    seen_hosts: dict[str, int] = {}
    for device in enabled_devices:
        name = device.name.strip()
        host = device.host.strip()
        if not name:
            result.add("error", "device", "장비명이 비어 있습니다.", f"host={host or '-'}")
        if not host:
            result.add("error", "device", "장비 IP/호스트가 비어 있습니다.", f"device={name or '-'}")
        if host and any(char.isspace() for char in host):
            result.add("error", "device", "장비 IP/호스트에 공백이 있습니다.", f"device={name or '-'} host={host}")
        if not 1 <= int(device.port) <= 65535:
            result.add("error", "device", "장비 포트 범위가 올바르지 않습니다.", f"{name or host}: {device.port}")
        device_type = device.device_type.strip().lower()
        if not device_type:
            result.add("error", "device", "장비 타입이 비어 있습니다.", f"device={name or host or '-'}")
        elif device_type not in SUPPORTED_DEVICE_TYPES:
            result.add(
                "error",
                "device",
                "지원하지 않는 장비 타입입니다.",
                f"{name or host or '-'}: SSH 전용 hp_comware만 허용",
            )
        if host.startswith(DOCUMENTATION_HOST_PREFIXES) or host.endswith(".example.com"):
            result.add("warning", "device", "예시용 주소가 설정되어 있습니다.", f"{name or host}: {host}")
        if name:
            seen_names[name] = seen_names.get(name, 0) + 1
        if host:
            seen_hosts[host] = seen_hosts.get(host, 0) + 1

    for name, count in seen_names.items():
        if count > 1:
            result.add("error", "device", "장비명이 중복됩니다.", name)
    for host, count in seen_hosts.items():
        if count > 1:
            result.add("warning", "device", "동일한 IP/호스트가 여러 장비에 사용됩니다.", host)


def validate_commands(commands: list[CommandSpec], result: PreflightResult) -> None:
    if not commands:
        result.add("error", "command", "점검 명령이 없습니다.", "config/commands.yaml을 확인하세요.")
        return

    check_commands = [command for command in commands if command.phase == "check"]
    if not check_commands:
        result.add("error", "command", "check 단계 명령이 없습니다.", "실제 상태 비교에 사용할 읽기 전용 명령이 필요합니다.")

    seen_ids: dict[str, int] = {}
    for command in commands:
        command_id = command.id.strip()
        command_text = command.command.strip()
        if not command_id:
            result.add("error", "command", "명령 ID가 비어 있습니다.", command_text or "-")
        if not command_text:
            result.add("error", "command", "명령 원문이 비어 있습니다.", command_id or "-")
        if command_id:
            seen_ids[command_id] = seen_ids.get(command_id, 0) + 1
        if command.timeout < 1:
            result.add("error", "command", "명령 timeout 값이 올바르지 않습니다.", f"{command_id}: {command.timeout}")
        if command_text:
            validate_command_safety(command, result)

    for command_id, count in seen_ids.items():
        if count > 1:
            result.add("error", "command", "명령 ID가 중복됩니다.", command_id)


def validate_command_safety(command: CommandSpec, result: PreflightResult) -> None:
    try:
        canonicalize_command(command.command)
    except CommandSafetyError as exc:
        result.add(
            "error",
            "command",
            "읽기 전용 안전 경계를 통과하지 못한 명령이 있습니다.",
            f"{command.id}: {exc}",
        )


def preflight_summary_text(result: PreflightResult) -> str:
    if result.has_errors:
        return f"설정 점검 실패: 오류 {result.error_count}, 주의 {result.warning_count}"
    if result.warning_count:
        return f"설정 점검 주의: 주의 {result.warning_count}, 정보 {result.info_count}"
    return "설정 점검 통과"


def preflight_detail_text(result: PreflightResult) -> str:
    if not result.issues:
        return "설정 점검 결과가 없습니다."
    lines = [preflight_summary_text(result), ""]
    label = {"error": "오류", "warning": "주의", "info": "정보"}
    for issue in result.issues:
        detail = f" - {issue.detail}" if issue.detail else ""
        lines.append(f"[{label.get(issue.severity, issue.severity)}] {issue.message}{detail}")
    return "\n".join(lines)
