from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import CommandSpec, Device


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyYAML is required. Install it with: python -m pip install PyYAML") from exc

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyYAML is required. Install it with: python -m pip install PyYAML") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=False, sort_keys=False)


def load_devices(path: Path) -> list[Device]:
    payload = _load_yaml(path)
    devices = payload.get("devices", [])
    if not isinstance(devices, list):
        raise ValueError("devices must be a list")
    parsed = [Device.from_mapping(item) for item in devices if isinstance(item, dict)]
    return [device for device in parsed if device.name]


def save_devices(path: Path, devices: list[Device]) -> None:
    _write_yaml(path, {"devices": [device.to_safe_dict() for device in devices]})


def load_commands(path: Path) -> list[CommandSpec]:
    payload = _load_yaml(path)
    commands: list[CommandSpec] = []

    setup_items = payload.get("session_setup", [])
    if isinstance(setup_items, list):
        commands.extend(
            CommandSpec.from_mapping(item, default_phase="setup")
            for item in setup_items
            if isinstance(item, dict)
        )

    command_items = payload.get("commands", [])
    if isinstance(command_items, list):
        commands.extend(
            CommandSpec.from_mapping(item, default_phase="check")
            for item in command_items
            if isinstance(item, dict)
        )

    valid = [command for command in commands if command.id and command.command]
    if not valid:
        raise ValueError(f"No valid commands found: {path}")
    return valid

