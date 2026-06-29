from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class MockProfileError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class MockProfile:
    name: str
    username: str = "operator"
    password: str = "mock-password"
    prompt: str = "<MOCK-BST> "
    banner: str = "백본 상태 추적기 모의 장비"
    commands: dict[str, str] = field(default_factory=dict)
    command_delays: dict[str, float] = field(default_factory=dict)
    auth_failure: bool = False

    def response_for(self, command: str) -> str:
        normalized = " ".join(str(command or "").strip().split())
        return self.commands.get(normalized, self.commands.get("*", f"Mock response: {normalized}"))

    def delay_for(self, command: str) -> float:
        normalized = " ".join(str(command or "").strip().split())
        return float(self.command_delays.get(normalized, 0.0))

    def accepts_login(self, username: str, password: str) -> bool:
        if self.auth_failure:
            return False
        return username == self.username and password == self.password


def load_mock_profiles(path: Path) -> dict[str, MockProfile]:
    payload = _load_yaml(path)
    raw_profiles = payload.get("profiles", {})
    if not isinstance(raw_profiles, dict):
        raise MockProfileError("BST-MOCK-801", "프로파일 목록은 매핑 형식이어야 합니다.")
    return {name: _build_profile(name, raw_profiles, []) for name in sorted(raw_profiles)}


def load_mock_profile(path: Path, profile_name: str) -> MockProfile:
    profiles = load_mock_profiles(path)
    try:
        return profiles[profile_name]
    except KeyError as exc:
        raise MockProfileError("BST-MOCK-801", f"모의 장비 프로파일을 찾을 수 없습니다: {profile_name}") from exc


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MockProfileError("BST-MOCK-801", f"모의 장비 프로파일 파일을 찾을 수 없습니다: {path}")
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyYAML이 필요합니다. 다음 명령으로 설치하세요: python -m pip install PyYAML") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise MockProfileError("BST-MOCK-801", f"모의 장비 프로파일 루트는 매핑 형식이어야 합니다: {path}")
    return data


def _build_profile(name: str, raw_profiles: dict[str, Any], stack: list[str]) -> MockProfile:
    if name in stack:
        raise MockProfileError("BST-MOCK-801", f"모의 장비 프로파일 상속 순환: {' -> '.join(stack + [name])}")
    raw = raw_profiles.get(name)
    if not isinstance(raw, dict):
        raise MockProfileError("BST-MOCK-801", f"모의 장비 프로파일을 찾을 수 없습니다: {name}")

    parent_name = str(raw.get("inherit", "") or "").strip()
    parent = _build_profile(parent_name, raw_profiles, stack + [name]) if parent_name else None

    base_commands = dict(parent.commands) if parent else {}
    base_delays = dict(parent.command_delays) if parent else {}
    raw_commands = raw.get("commands", {})
    raw_delays = raw.get("command_delays", {})
    if raw_commands and not isinstance(raw_commands, dict):
        raise MockProfileError("BST-MOCK-801", f"프로파일 commands는 매핑 형식이어야 합니다: {name}")
    if raw_delays and not isinstance(raw_delays, dict):
        raise MockProfileError("BST-MOCK-801", f"프로파일 command_delays는 매핑 형식이어야 합니다: {name}")
    base_commands.update({str(key): str(value) for key, value in dict(raw_commands).items()})
    base_delays.update({str(key): float(value) for key, value in dict(raw_delays).items()})

    return MockProfile(
        name=name,
        username=str(raw.get("username", parent.username if parent else "operator")),
        password=str(raw.get("password", parent.password if parent else "mock-password")),
        prompt=str(raw.get("prompt", parent.prompt if parent else "<MOCK-BST> ")),
        banner=str(raw.get("banner", parent.banner if parent else "백본 상태 추적기 모의 장비")),
        commands=base_commands,
        command_delays=base_delays,
        auth_failure=bool(raw.get("auth_failure", parent.auth_failure if parent else False)),
    )
