from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .connectivity import make_connectivity_result_for_device
from .diff_engine import DiffEngine
from .models import CommandResult, Device, DiffSummary
from .reporter import ReportWriter
from .snapshot import SnapshotStore


SAMPLE_PREFIX = "[샘플]"


@dataclass(frozen=True)
class MockValidationResult:
    pre_snapshot: Path
    off_snapshot: Path
    restore_snapshot: Path
    off_summary: DiffSummary
    restore_summary: DiffSummary
    restore_from_off_summary: DiffSummary
    off_report: Path
    restore_report: Path
    restore_from_off_report: Path
    off_share_zip: Path
    restore_share_zip: Path
    restore_from_off_share_zip: Path


def create_mock_validation_artifacts(snapshot_store: SnapshotStore) -> MockValidationResult:
    devices = [
        Device(name="backbone3", host="192.0.2.3"),
        Device(name="backbone4", host="192.0.2.4"),
    ]
    pre_snapshot = snapshot_store.write_snapshot(
        f"{SAMPLE_PREFIX} 작업 전",
        devices,
        _pre_work_results(devices),
        folder_label="sample_pre_work",
        stage_name=f"{SAMPLE_PREFIX} 작업 전",
        stage_slug="sample_pre_work",
    )
    off_snapshot = snapshot_store.write_snapshot(
        f"{SAMPLE_PREFIX} 백본3 OFF 중",
        devices,
        _bb3_off_results(devices),
        folder_label="sample_bb3_off",
        stage_name=f"{SAMPLE_PREFIX} 백본3 OFF 중",
        stage_slug="sample_bb3_off",
    )
    restore_snapshot = snapshot_store.write_snapshot(
        f"{SAMPLE_PREFIX} 복구 후",
        devices,
        _restored_results(devices),
        folder_label="sample_restored",
        stage_name=f"{SAMPLE_PREFIX} 복구 후",
        stage_slug="sample_restored",
    )

    off_summary, off_paths = _write_comparison(pre_snapshot, off_snapshot)
    restore_summary, restore_paths = _write_comparison(pre_snapshot, restore_snapshot)
    restore_from_off_summary, restore_from_off_paths = _write_comparison(off_snapshot, restore_snapshot)

    return MockValidationResult(
        pre_snapshot=pre_snapshot,
        off_snapshot=off_snapshot,
        restore_snapshot=restore_snapshot,
        off_summary=off_summary,
        restore_summary=restore_summary,
        restore_from_off_summary=restore_from_off_summary,
        off_report=off_paths["html"],
        restore_report=restore_paths["html"],
        restore_from_off_report=restore_from_off_paths["html"],
        off_share_zip=off_paths["share_zip"],
        restore_share_zip=restore_paths["share_zip"],
        restore_from_off_share_zip=restore_from_off_paths["share_zip"],
    )


def _write_comparison(base_snapshot: Path, target_snapshot: Path) -> tuple[DiffSummary, dict[str, Path]]:
    summary = DiffEngine().compare(base_snapshot, target_snapshot)
    return summary, ReportWriter().write_reports(summary)


def _pre_work_results(devices: list[Device]) -> dict[str, list[CommandResult]]:
    return {
        devices[0].name: [
            _connectivity(devices[0], True, "2026-06-11T09:00:00"),
            _interface(devices[0], "BAGG10 UP\nGE1/0/1 UP\nGE1/0/2 UP", "2026-06-11T09:00:01"),
            _lacp(devices[0], "BAGG10 Selected ports: 2/2\nPeer backbone4 synchronized", "2026-06-11T09:00:02"),
            _routing(devices[0], "OSPF peer backbone4 Full\nDefault route active", "2026-06-11T09:00:03"),
            _hardware(devices[0], "Slot 1 Normal\nPower 1 Normal\nFan 1 Normal", "2026-06-11T09:00:04"),
        ],
        devices[1].name: [
            _connectivity(devices[1], True, "2026-06-11T09:00:00"),
            _interface(devices[1], "BAGG10 UP\nGE1/0/1 UP\nGE1/0/2 UP", "2026-06-11T09:00:01"),
            _lacp(devices[1], "BAGG10 Selected ports: 2/2\nPeer backbone3 synchronized", "2026-06-11T09:00:02"),
            _routing(devices[1], "OSPF peer backbone3 Full\nDefault route active", "2026-06-11T09:00:03"),
            _hardware(devices[1], "Slot 1 Normal\nPower 1 Normal\nFan 1 Normal", "2026-06-11T09:00:04"),
        ],
    }


def _bb3_off_results(devices: list[Device]) -> dict[str, list[CommandResult]]:
    return {
        devices[0].name: [
            _connectivity(devices[0], False, "2026-06-11T10:00:00", reason="timeout"),
        ],
        devices[1].name: [
            _connectivity(devices[1], True, "2026-06-11T10:00:00"),
            _interface(devices[1], "BAGG10 DOWN\nGE1/0/1 DOWN\nGE1/0/2 UP", "2026-06-11T10:00:01"),
            _lacp(devices[1], "BAGG10 Selected ports: 1/2\nPeer backbone3 not selected", "2026-06-11T10:00:02"),
            _routing(devices[1], "OSPF peer backbone3 Loading\nDefault route active", "2026-06-11T10:00:03"),
            _hardware(devices[1], "Slot 1 Normal\nPower 1 Normal\nFan 1 Normal", "2026-06-11T10:00:04"),
        ],
    }


def _restored_results(devices: list[Device]) -> dict[str, list[CommandResult]]:
    return {
        devices[0].name: [
            _connectivity(devices[0], True, "2026-06-11T11:00:00"),
            _interface(devices[0], "BAGG10 UP\nGE1/0/1 UP\nGE1/0/2 UP", "2026-06-11T11:00:01"),
            _lacp(devices[0], "BAGG10 Selected ports: 2/2\nPeer backbone4 synchronized", "2026-06-11T11:00:02"),
            _routing(devices[0], "OSPF peer backbone4 Full\nDefault route active", "2026-06-11T11:00:03"),
            _hardware(devices[0], "Slot 1 Normal\nPower 1 Normal\nFan 1 Normal", "2026-06-11T11:00:04"),
        ],
        devices[1].name: [
            _connectivity(devices[1], True, "2026-06-11T11:00:00"),
            _interface(devices[1], "BAGG10 UP\nGE1/0/1 UP\nGE1/0/2 UP", "2026-06-11T11:00:01"),
            _lacp(devices[1], "BAGG10 Selected ports: 2/2\nPeer backbone3 synchronized", "2026-06-11T11:00:02"),
            _routing(devices[1], "OSPF peer backbone3 Full\nDefault route active", "2026-06-11T11:00:03"),
            _hardware(devices[1], "Slot 1 Normal\nPower 1 Normal\nFan 1 Normal", "2026-06-11T11:00:04"),
        ],
    }


def _connectivity(device: Device, success: bool, when: str, reason: str = "") -> CommandResult:
    return make_connectivity_result_for_device(
        device_name=device.name,
        host=device.host,
        success=success,
        reason=reason,
        started_at=when,
        ended_at=when,
    )


def _interface(device: Device, output: str, when: str) -> CommandResult:
    return _result(
        device,
        command_id="interface_brief",
        command="display interface brief",
        category="interface",
        output=output,
        when=when,
    )


def _lacp(device: Device, output: str, when: str) -> CommandResult:
    return _result(
        device,
        command_id="lacp_summary",
        command="display link-aggregation summary",
        category="switching",
        output=output,
        when=when,
    )


def _routing(device: Device, output: str, when: str) -> CommandResult:
    return _result(
        device,
        command_id="routing_neighbor",
        command="display ospf peer brief",
        category="routing",
        output=output,
        when=when,
    )


def _hardware(device: Device, output: str, when: str) -> CommandResult:
    return _result(
        device,
        command_id="device_status",
        command="display device",
        category="hardware",
        output=output,
        when=when,
    )


def _result(
    device: Device,
    command_id: str,
    command: str,
    category: str,
    output: str,
    when: str,
) -> CommandResult:
    return CommandResult(
        device_name=device.name,
        host=device.host,
        command_id=command_id,
        command=command,
        category=category,
        phase="check",
        success=True,
        output=output,
        started_at=when,
        ended_at=when,
    )
