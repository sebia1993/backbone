from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import _load_yaml
from .paths import resource_root, runtime_root


@dataclass(frozen=True)
class FindingRule:
    key: str
    title: str
    impact_reason: str
    action_hint: str
    priority: int = 50


@dataclass(frozen=True)
class ExpectedChangeRule:
    stage_slugs: tuple[str, ...] = ()
    device_names: tuple[str, ...] = ()
    command_ids: tuple[str, ...] = ()
    summaries: tuple[str, ...] = ()
    title: str = ""
    action_hint: str = ""

    def matches(self, *, stage_slug: str, device_name: str, command_id: str, summary: str) -> bool:
        return (
            _matches_any(stage_slug, self.stage_slugs)
            and _matches_any(device_name, self.device_names)
            and _matches_any(command_id, self.command_ids)
            and _matches_any(summary, self.summaries)
        )


@dataclass(frozen=True)
class AnalysisRules:
    thresholds: dict[str, dict[str, float]] = field(default_factory=dict)
    findings: dict[str, FindingRule] = field(default_factory=dict)
    expected_changes: tuple[ExpectedChangeRule, ...] = ()

    def threshold(self, section: str, key: str, default: float) -> float:
        section_payload = self.thresholds.get(section, {})
        value = section_payload.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def finding(self, key: str) -> FindingRule:
        return self.findings.get(key) or FindingRule(
            key=key,
            title="확인 필요",
            impact_reason="기준과 비교 시점의 상태가 달라졌습니다.",
            action_hint="원본 diff와 관련 상태 명령을 확인하세요.",
            priority=50,
        )

    def expected_change(
        self,
        *,
        stage_slug: str,
        device_name: str,
        command_id: str,
        summary: str,
    ) -> ExpectedChangeRule | None:
        for rule in self.expected_changes:
            if rule.matches(stage_slug=stage_slug, device_name=device_name, command_id=command_id, summary=summary):
                return rule
        return None


def load_analysis_rules(path: Path | None = None) -> AnalysisRules:
    if path is not None:
        rules_path = path
    else:
        rules_path = next(
            (
                candidate
                for candidate in (
                    runtime_root() / "config" / "analysis_rules.yaml",
                    resource_root() / "config" / "analysis_rules.yaml",
                )
                if candidate.exists()
            ),
            runtime_root() / "config" / "analysis_rules.yaml",
        )
    if not rules_path.exists():
        return AnalysisRules()
    return analysis_rules_from_mapping(_load_yaml(rules_path))


def analysis_rules_from_mapping(payload: dict[str, Any]) -> AnalysisRules:
    thresholds = _parse_thresholds(payload.get("thresholds", {}))
    findings = _parse_findings(payload.get("findings", {}))
    expected_changes = tuple(_parse_expected_change(item) for item in _list_of_mappings(payload.get("expected_changes", [])))
    return AnalysisRules(thresholds=thresholds, findings=findings, expected_changes=expected_changes)


def _parse_thresholds(payload: Any) -> dict[str, dict[str, float]]:
    if not isinstance(payload, dict):
        return {}
    thresholds: dict[str, dict[str, float]] = {}
    for section, values in payload.items():
        if not isinstance(values, dict):
            continue
        parsed: dict[str, float] = {}
        for key, value in values.items():
            try:
                parsed[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
        thresholds[str(section)] = parsed
    return thresholds


def _parse_findings(payload: Any) -> dict[str, FindingRule]:
    if not isinstance(payload, dict):
        return {}
    findings: dict[str, FindingRule] = {}
    for key, values in payload.items():
        if not isinstance(values, dict):
            continue
        severity = str(values.get("severity", "")).strip()
        if severity and severity not in {"Critical", "Warning", "Info", "Unchanged"}:
            raise ValueError(f"Invalid finding severity for {key}: {severity}")
        priority = values.get("priority", 50)
        try:
            parsed_priority = int(priority)
        except (TypeError, ValueError):
            parsed_priority = 50
        rule_key = str(key)
        findings[rule_key] = FindingRule(
            key=rule_key,
            title=str(values.get("title", rule_key)).strip() or rule_key,
            impact_reason=str(values.get("impact_reason", "")).strip(),
            action_hint=str(values.get("action_hint", "")).strip(),
            priority=parsed_priority,
        )
    return findings


def _parse_expected_change(payload: dict[str, Any]) -> ExpectedChangeRule:
    return ExpectedChangeRule(
        stage_slugs=_as_tuple(payload.get("stage_slugs")),
        device_names=_as_tuple(payload.get("device_names")),
        command_ids=_as_tuple(payload.get("command_ids")),
        summaries=_as_tuple(payload.get("summaries")),
        title=str(payload.get("title", "")).strip(),
        action_hint=str(payload.get("action_hint", "")).strip(),
    )


def _list_of_mappings(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _matches_any(value: str, candidates: tuple[str, ...]) -> bool:
    if not candidates:
        return True
    normalized_value = value.strip().lower()
    return any(candidate.strip().lower() == normalized_value for candidate in candidates)
