from __future__ import annotations

import difflib
import re
from datetime import datetime
from pathlib import Path

from .connectivity import (
    DEVICE_CONNECTIVITY_COMMAND_ID,
    is_connectivity_result,
    is_legacy_connection_failure,
    legacy_failure_reason,
    make_connectivity_result_for_device,
)
from .models import CommandResult, DiffItem, DiffLine, DiffSummary, Snapshot
from .snapshot import SnapshotStore, read_text_lossless


VOLATILE_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^\s*<[^>]+>\s*$"),
    re.compile(r"^\s*\[[^\]]+\]\s*$"),
    re.compile(r"\b(current\s+)?time\b", re.IGNORECASE),
    re.compile(r"\bclock\b", re.IGNORECASE),
    re.compile(r"\buptime\b", re.IGNORECASE),
    re.compile(r"\bup\s+time\b", re.IGNORECASE),
    re.compile(r"\bboot\b.*\btime\b", re.IGNORECASE),
    re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"),
    re.compile(r"\b\d{1,2}:\d{2}:\d{2}\b"),
]

CRITICAL_PATTERNS = [
    re.compile(r"\bdown\b", re.IGNORECASE),
    re.compile(r"\bfail(?:ed|ure)?\b", re.IGNORECASE),
    re.compile(r"\bfault\b", re.IGNORECASE),
    re.compile(r"\babnormal\b", re.IGNORECASE),
    re.compile(r"\bunselected\b", re.IGNORECASE),
    re.compile(r"\bnot\s+selected\b", re.IGNORECASE),
    re.compile(r"\binit\b|\bexstart\b|\bexchange\b|\bloading\b", re.IGNORECASE),
]

WARNING_PATTERNS = [
    re.compile(r"\bwarn(?:ing)?\b", re.IGNORECASE),
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"\bmajor\b|\bminor\b|\balarm\b", re.IGNORECASE),
    re.compile(r"\bchange(?:d)?\b", re.IGNORECASE),
]

MAX_CHANGED_LINES = 500


class DiffEngine:
    def compare(self, base_dir: Path, target_dir: Path) -> DiffSummary:
        base = SnapshotStore.load_snapshot(base_dir)
        target = SnapshotStore.load_snapshot(target_dir)
        base_results = self._index_results(self._results_with_connectivity(base))
        target_results = self._index_results(self._results_with_connectivity(target))
        base_unreachable_devices = self._unreachable_devices(base_results)
        target_unreachable_devices = self._unreachable_devices(target_results)
        keys = sorted(set(base_results) | set(target_results))
        items: list[DiffItem] = []

        for key in keys:
            device_name, command_id = key
            base_result = base_results.get(key)
            target_result = target_results.get(key)

            if self._should_suppress_missing_due_to_unreachable(
                device_name,
                command_id,
                base_result,
                target_result,
                base_unreachable_devices,
                target_unreachable_devices,
            ):
                continue

            if base_result and base_result.phase == "setup":
                continue
            if target_result and target_result.phase == "setup":
                continue

            if base_result is None or target_result is None:
                items.append(self._missing_item(base_dir, target_dir, key, base_result, target_result))
                continue

            if command_id == DEVICE_CONNECTIVITY_COMMAND_ID:
                items.append(self._connectivity_item(base_dir, target_dir, base_result, target_result))
                continue

            base_text = self._read_result_output(base_dir, base_result)
            target_text = self._read_result_output(target_dir, target_result)
            base_lines = normalize_output_lines(base_text, command_id=base_result.command_id)
            target_lines = normalize_output_lines(target_text, command_id=target_result.command_id)
            base_normalized = "\n".join(line for _, line in base_lines).strip()
            target_normalized = "\n".join(line for _, line in target_lines).strip()

            if base_normalized == target_normalized and base_result.success == target_result.success:
                items.append(
                    DiffItem(
                        device_name=target_result.device_name,
                        command_id=target_result.command_id,
                        command=target_result.command,
                        category=target_result.category,
                        severity="Unchanged",
                        status="unchanged",
                        summary="No meaningful change detected.",
                        base_raw_file=base_result.raw_file,
                        target_raw_file=target_result.raw_file,
                    )
                )
                continue

            diff_text = "\n".join(
                difflib.unified_diff(
                    base_normalized.splitlines(),
                    target_normalized.splitlines(),
                    fromfile=f"base/{base_result.device_name}/{base_result.command_id}",
                    tofile=f"target/{target_result.device_name}/{target_result.command_id}",
                    lineterm="",
                )
            )
            added_lines = [line[1:] for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")]
            severity, summary = classify_change(target_result, added_lines, diff_text)
            changed_lines = build_changed_lines(base_lines, target_lines)
            change_count, changed_lines, change_preview = summarize_changed_lines(changed_lines)
            items.append(
                DiffItem(
                    device_name=target_result.device_name,
                    command_id=target_result.command_id,
                    command=target_result.command,
                    category=target_result.category,
                    severity=severity,
                    status="changed",
                    summary=summary,
                    diff=diff_text,
                    base_raw_file=base_result.raw_file,
                    target_raw_file=target_result.raw_file,
                    changed_lines=changed_lines,
                    change_count=change_count,
                    change_preview=change_preview,
                )
            )

        return DiffSummary(
            base_snapshot=str(base_dir),
            target_snapshot=str(target_dir),
            generated_at=datetime.now().isoformat(timespec="seconds"),
            items=items,
        )

    @staticmethod
    def _index_results(results: list[CommandResult]) -> dict[tuple[str, str], CommandResult]:
        return {(result.device_name, result.command_id): result for result in results}

    @staticmethod
    def _read_result_output(snapshot_dir: Path, result: CommandResult) -> str:
        if not result.raw_file:
            return result.output
        raw_path = snapshot_dir / result.raw_file
        if not raw_path.exists():
            return result.output
        return read_text_lossless(raw_path)

    def _results_with_connectivity(self, snapshot: Snapshot) -> list[CommandResult]:
        results = [result for result in snapshot.results if not is_legacy_connection_failure(result)]
        devices = self._enabled_device_map(snapshot)
        existing_connectivity = {result.device_name for result in results if is_connectivity_result(result)}

        for device_name, host in devices.items():
            if device_name in existing_connectivity:
                continue

            legacy_failure = next(
                (
                    result
                    for result in snapshot.results
                    if result.device_name == device_name and is_legacy_connection_failure(result)
                ),
                None,
            )
            if legacy_failure is not None:
                results.append(
                    make_connectivity_result_for_device(
                        device_name=device_name,
                        host=legacy_failure.host or host,
                        success=False,
                        reason=legacy_failure_reason(legacy_failure),
                        error_message=legacy_failure.error_message,
                        started_at=legacy_failure.started_at,
                        ended_at=legacy_failure.ended_at,
                    )
                )
                continue

            reachable_result = next(
                (
                    result
                    for result in snapshot.results
                    if result.device_name == device_name and self._is_reachable_command_result(result)
                ),
                None,
            )
            if reachable_result is not None:
                results.append(
                    make_connectivity_result_for_device(
                        device_name=device_name,
                        host=reachable_result.host or host,
                        success=True,
                        started_at=reachable_result.started_at,
                        ended_at=reachable_result.ended_at,
                    )
                )

        return results

    @staticmethod
    def _enabled_device_map(snapshot: Snapshot) -> dict[str, str]:
        devices: dict[str, str] = {}
        for payload in snapshot.devices:
            if not bool(payload.get("enabled", True)):
                continue
            name = str(payload.get("name") or payload.get("host") or "").strip()
            if name:
                devices[name] = str(payload.get("host") or "").strip()

        for result in snapshot.results:
            if result.device_name and result.device_name not in devices:
                devices[result.device_name] = result.host
        return devices

    @staticmethod
    def _is_reachable_command_result(result: CommandResult) -> bool:
        return (
            result.phase != "setup"
            and not is_connectivity_result(result)
            and not is_legacy_connection_failure(result)
        )

    @staticmethod
    def _unreachable_devices(results: dict[tuple[str, str], CommandResult]) -> set[str]:
        return {
            device_name
            for (device_name, command_id), result in results.items()
            if command_id == DEVICE_CONNECTIVITY_COMMAND_ID and not result.success
        }

    @staticmethod
    def _should_suppress_missing_due_to_unreachable(
        device_name: str,
        command_id: str,
        base_result: CommandResult | None,
        target_result: CommandResult | None,
        base_unreachable_devices: set[str],
        target_unreachable_devices: set[str],
    ) -> bool:
        if command_id == DEVICE_CONNECTIVITY_COMMAND_ID:
            return False
        if target_result is None and device_name in target_unreachable_devices:
            return True
        if base_result is None and device_name in base_unreachable_devices:
            return True
        return False

    def _connectivity_item(
        self,
        base_dir: Path,
        target_dir: Path,
        base_result: CommandResult,
        target_result: CommandResult,
    ) -> DiffItem:
        base_text = self._read_result_output(base_dir, base_result)
        target_text = self._read_result_output(target_dir, target_result)
        base_lines = normalize_output_lines(base_text, command_id=base_result.command_id)
        target_lines = normalize_output_lines(target_text, command_id=target_result.command_id)
        base_normalized = "\n".join(line for _, line in base_lines).strip()
        target_normalized = "\n".join(line for _, line in target_lines).strip()

        if base_result.success and target_result.success and base_normalized == target_normalized:
            return DiffItem(
                device_name=target_result.device_name,
                command_id=target_result.command_id,
                command=target_result.command,
                category=target_result.category,
                severity="Unchanged",
                status="unchanged",
                summary="No meaningful change detected.",
                base_raw_file=base_result.raw_file,
                target_raw_file=target_result.raw_file,
            )

        diff_text = "\n".join(
            difflib.unified_diff(
                base_normalized.splitlines(),
                target_normalized.splitlines(),
                fromfile=f"base/{base_result.device_name}/{base_result.command_id}",
                tofile=f"target/{target_result.device_name}/{target_result.command_id}",
                lineterm="",
            )
        )
        changed_lines = build_changed_lines(base_lines, target_lines)
        if not changed_lines:
            changed_lines = [
                DiffLine(
                    kind="changed",
                    base_line_no=1,
                    target_line_no=1,
                    base_text=base_normalized or "-",
                    target_text=target_normalized or "-",
                )
            ]
        change_count, changed_lines, change_preview = summarize_changed_lines(changed_lines)
        severity, summary = classify_connectivity_change(base_result, target_result)
        return DiffItem(
            device_name=target_result.device_name,
            command_id=target_result.command_id,
            command=target_result.command,
            category=target_result.category,
            severity=severity,
            status="changed",
            summary=summary,
            diff=diff_text,
            base_raw_file=base_result.raw_file,
            target_raw_file=target_result.raw_file,
            changed_lines=changed_lines,
            change_count=change_count,
            change_preview=change_preview,
        )

    def _missing_item(
        self,
        base_dir: Path,
        target_dir: Path,
        key: tuple[str, str],
        base_result: CommandResult | None,
        target_result: CommandResult | None,
    ) -> DiffItem:
        result = target_result or base_result
        device_name, command_id = key
        status = "added" if base_result is None else "removed"
        raw_file = result.raw_file if result else ""
        changed_lines: list[DiffLine] = []
        if target_result is not None:
            output = self._read_result_output(target_dir, target_result)
            changed_lines = [
                DiffLine(kind="added", target_line_no=line_no, target_text=line)
                for line_no, line in normalize_output_lines(output, command_id=target_result.command_id)
            ]
        elif base_result is not None:
            output = self._read_result_output(base_dir, base_result)
            changed_lines = [
                DiffLine(kind="removed", base_line_no=line_no, base_text=line)
                for line_no, line in normalize_output_lines(output, command_id=base_result.command_id)
            ]
        change_count, changed_lines, change_preview = summarize_changed_lines(changed_lines)
        return DiffItem(
            device_name=device_name,
            command_id=command_id,
            command=result.command if result else "",
            category=result.category if result else "unknown",
            severity="Warning",
            status=status,
            summary=f"Command result was {status} between snapshots.",
            base_raw_file=raw_file if base_result else "",
            target_raw_file=raw_file if target_result else "",
            changed_lines=changed_lines,
            change_count=change_count,
            change_preview=change_preview,
        )


def normalize_output(text: str, command_id: str = "") -> str:
    return "\n".join(line for _, line in normalize_output_lines(text, command_id=command_id)).strip()


def normalize_output_lines(text: str, command_id: str = "") -> list[tuple[int, str]]:
    if command_id == "system_clock":
        return []
    normalized_lines: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), start=1):
        stripped = line.rstrip()
        if should_ignore_line(stripped):
            continue
        normalized_lines.append((line_no, stripped))
    return normalized_lines


def should_ignore_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in VOLATILE_PATTERNS)


def build_changed_lines(
    base_lines: list[tuple[int, str]],
    target_lines: list[tuple[int, str]],
    context: int = 1,
) -> list[DiffLine]:
    base_values = [line for _, line in base_lines]
    target_values = [line for _, line in target_lines]
    matcher = difflib.SequenceMatcher(None, base_values, target_values, autojunk=False)
    details: list[DiffLine] = []
    seen: set[tuple[str, int | None, int | None, str, str]] = set()

    def add_line(line: DiffLine) -> None:
        key = (line.kind, line.base_line_no, line.target_line_no, line.base_text, line.target_text)
        if key in seen:
            return
        seen.add(key)
        details.append(line)

    def add_context(base_index: int, target_index: int) -> None:
        if base_index < 0 or target_index < 0:
            return
        if base_index >= len(base_lines) or target_index >= len(target_lines):
            return
        base_line_no, base_text = base_lines[base_index]
        target_line_no, target_text = target_lines[target_index]
        add_line(
            DiffLine(
                kind="context",
                base_line_no=base_line_no,
                target_line_no=target_line_no,
                base_text=base_text,
                target_text=target_text,
            )
        )

    for tag, base_start, base_end, target_start, target_end in matcher.get_opcodes():
        if tag == "equal":
            continue

        for offset in range(context, 0, -1):
            add_context(base_start - offset, target_start - offset)

        if tag == "replace":
            base_count = base_end - base_start
            target_count = target_end - target_start
            for offset in range(max(base_count, target_count)):
                base_line = base_lines[base_start + offset] if offset < base_count else None
                target_line = target_lines[target_start + offset] if offset < target_count else None
                if base_line is not None and target_line is not None:
                    add_line(
                        DiffLine(
                            kind="changed",
                            base_line_no=base_line[0],
                            target_line_no=target_line[0],
                            base_text=base_line[1],
                            target_text=target_line[1],
                        )
                    )
                elif base_line is not None:
                    add_line(DiffLine(kind="removed", base_line_no=base_line[0], base_text=base_line[1]))
                elif target_line is not None:
                    add_line(DiffLine(kind="added", target_line_no=target_line[0], target_text=target_line[1]))
        elif tag == "delete":
            for base_index in range(base_start, base_end):
                line_no, line = base_lines[base_index]
                add_line(DiffLine(kind="removed", base_line_no=line_no, base_text=line))
        elif tag == "insert":
            for target_index in range(target_start, target_end):
                line_no, line = target_lines[target_index]
                add_line(DiffLine(kind="added", target_line_no=line_no, target_text=line))

        for offset in range(context):
            add_context(base_end + offset, target_end + offset)

    return details


def summarize_changed_lines(lines: list[DiffLine]) -> tuple[int, list[DiffLine], str]:
    change_lines = [line for line in lines if line.kind != "context"]
    preview = ""
    if change_lines:
        preview = format_diff_line_preview(change_lines[0])
    return len(change_lines), lines[:MAX_CHANGED_LINES], preview


def format_diff_line_preview(line: DiffLine) -> str:
    if line.kind == "changed":
        return f"{line.base_text} -> {line.target_text}"
    if line.kind == "added":
        return f"추가: {line.target_text}"
    if line.kind == "removed":
        return f"삭제: {line.base_text}"
    return line.target_text or line.base_text


def classify_connectivity_change(base_result: CommandResult, target_result: CommandResult) -> tuple[str, str]:
    if not target_result.success:
        return "Critical", "Target device connection failed."
    if not base_result.success and target_result.success:
        return "Info", "Target device connection restored."
    return "Info", "Output changed."


def classify_change(result: CommandResult, added_lines: list[str], diff_text: str) -> tuple[str, str]:
    if not result.success:
        return "Critical", "Target snapshot command failed."

    haystack = "\n".join(added_lines) or diff_text
    critical_categories = {"interface", "routing", "hardware", "connection"}
    if result.category in critical_categories and any(pattern.search(haystack) for pattern in CRITICAL_PATTERNS):
        return "Critical", "Critical state keyword detected in changed output."

    if result.category == "log" and any(pattern.search(haystack) for pattern in CRITICAL_PATTERNS):
        return "Critical", "New critical-looking log line detected."

    if result.category in {"log", "routing", "resource", "switching"}:
        if any(pattern.search(haystack) for pattern in WARNING_PATTERNS):
            return "Warning", "Warning keyword detected in changed output."
        return "Warning", "Operational state changed."

    return "Info", "Output changed."
