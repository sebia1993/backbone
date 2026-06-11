from __future__ import annotations

import difflib
import re
from datetime import datetime
from pathlib import Path

from .models import CommandResult, DiffItem, DiffSummary
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


class DiffEngine:
    def compare(self, base_dir: Path, target_dir: Path) -> DiffSummary:
        base = SnapshotStore.load_snapshot(base_dir)
        target = SnapshotStore.load_snapshot(target_dir)
        base_results = self._index_results(base.results)
        target_results = self._index_results(target.results)
        keys = sorted(set(base_results) | set(target_results))
        items: list[DiffItem] = []

        for key in keys:
            base_result = base_results.get(key)
            target_result = target_results.get(key)

            if base_result and base_result.phase == "setup":
                continue
            if target_result and target_result.phase == "setup":
                continue

            if base_result is None or target_result is None:
                items.append(self._missing_item(base_dir, target_dir, key, base_result, target_result))
                continue

            base_text = self._read_result_output(base_dir, base_result)
            target_text = self._read_result_output(target_dir, target_result)
            base_normalized = normalize_output(base_text, command_id=base_result.command_id)
            target_normalized = normalize_output(target_text, command_id=target_result.command_id)

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
            return ""
        raw_path = snapshot_dir / result.raw_file
        if not raw_path.exists():
            return ""
        return read_text_lossless(raw_path)

    @staticmethod
    def _missing_item(
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
        )


def normalize_output(text: str, command_id: str = "") -> str:
    if command_id == "system_clock":
        return ""
    normalized_lines: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.rstrip()
        if should_ignore_line(stripped):
            continue
        normalized_lines.append(stripped)
    return "\n".join(normalized_lines).strip()


def should_ignore_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in VOLATILE_PATTERNS)


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

