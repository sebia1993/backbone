from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from pathlib import Path

from .models import CommandSpec, Device
from .paths import runtime_root

MAX_COMMAND_LENGTH = 512
SUPPORTED_DEVICE_TYPES = frozenset({"hp_comware"})
SSH_DISABLED_ALGORITHMS = {
    "keys": ["ssh-rsa"],
    "pubkeys": ["ssh-rsa"],
}
_ALLOWED_COMMAND = re.compile(
    r"(?:display|show) [A-Za-z0-9][A-Za-z0-9 ._:/-]*|"
    r"screen-length disable|"
    r"terminal length (?:0|[1-9][0-9]{0,3})",
    re.ASCII | re.IGNORECASE,
)
_DANGEROUS_META = re.compile(r"[;&|<>`]|\$\(", re.ASCII)


class CommandSafetyError(ValueError):
    """Raised when input cannot cross the read-only collection boundary."""


def canonicalize_command(command: str) -> str:
    """Return one bounded, ASCII, read-only device command or fail closed."""

    if not isinstance(command, str):
        raise CommandSafetyError("명령은 문자열이어야 합니다.")
    if not command or len(command) > MAX_COMMAND_LENGTH:
        raise CommandSafetyError(f"명령 길이는 1~{MAX_COMMAND_LENGTH}자여야 합니다.")
    if any(unicodedata.category(character) == "Cc" for character in command):
        raise CommandSafetyError("명령에 제어 문자를 사용할 수 없습니다.")

    normalized = unicodedata.normalize("NFKC", command)
    try:
        normalized.encode("ascii")
    except UnicodeEncodeError as exc:
        raise CommandSafetyError("장비 명령은 ASCII 문자만 사용할 수 있습니다.") from exc
    canonical = " ".join(normalized.strip().split())
    if not canonical or len(canonical) > MAX_COMMAND_LENGTH:
        raise CommandSafetyError(f"정규화된 명령 길이는 1~{MAX_COMMAND_LENGTH}자여야 합니다.")
    if _DANGEROUS_META.search(canonical):
        raise CommandSafetyError("명령 체이닝, 파이프 또는 리디렉션 문자를 사용할 수 없습니다.")
    if _ALLOWED_COMMAND.fullmatch(canonical) is None:
        raise CommandSafetyError("허용된 display/show/페이징 제어 명령이 아닙니다.")
    return canonical


def canonicalize_commands(commands: list[CommandSpec]) -> list[CommandSpec]:
    """Canonicalize every command before any network connection is attempted."""

    canonical: list[CommandSpec] = []
    for item in commands:
        try:
            command_text = canonicalize_command(item.command)
        except CommandSafetyError as exc:
            command_id = item.id.strip() or "<missing-id>"
            raise CommandSafetyError(f"명령 {command_id!r} 차단: {exc}") from exc
        canonical.append(replace(item, command=command_text))
    return canonical


def validate_collection_devices(devices: list[Device]) -> None:
    for device in (item for item in devices if item.enabled):
        device_type = device.device_type.strip().lower()
        if device_type not in SUPPORTED_DEVICE_TYPES:
            raise CommandSafetyError(
                f"장비 {device.name!r} 차단: SSH 전용 hp_comware 타입만 지원합니다."
            )


def default_known_hosts_file() -> Path:
    return runtime_root() / "config" / "known_hosts"


def require_known_hosts_file(path: str | Path | None) -> Path:
    resolved = Path(path) if path is not None else default_known_hosts_file()
    resolved = resolved.expanduser().resolve()
    if not resolved.is_file():
        raise CommandSafetyError(
            f"승인된 SSH 호스트 키 파일이 없습니다: {resolved}. SECURITY.md 절차로 먼저 등록하세요."
        )
    try:
        from paramiko.hostkeys import HostKeyEntry, HostKeys, InvalidHostKey
        from paramiko.ssh_exception import SSHException
    except ImportError as exc:  # pragma: no cover - hash-locked runtime dependency
        raise CommandSafetyError("SSH 호스트 키 검증에 필요한 Paramiko를 불러올 수 없습니다.") from exc

    try:
        valid_line_count = 0
        for line_number, raw_line in enumerate(resolved.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            entry = HostKeyEntry.from_line(line, lineno=line_number)
            if entry is None or entry.key is None or not entry.hostnames:
                raise CommandSafetyError(
                    f"승인된 SSH 호스트 키 파일 {line_number}행이 올바른 known_hosts 엔트리가 아닙니다."
                )
            valid_line_count += 1
        host_keys = HostKeys(filename=str(resolved))
    except CommandSafetyError:
        raise
    except (OSError, UnicodeError, ValueError, InvalidHostKey, SSHException) as exc:
        raise CommandSafetyError(f"승인된 SSH 호스트 키 파일을 해석할 수 없습니다: {resolved}") from exc
    if valid_line_count < 1 or not host_keys:
        raise CommandSafetyError(f"승인된 SSH 호스트 키 엔트리가 없습니다: {resolved}")
    return resolved
