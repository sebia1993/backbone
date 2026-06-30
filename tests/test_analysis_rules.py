from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.core.analysis_rules import analysis_rules_from_mapping, load_analysis_rules


class AnalysisRulesTests(unittest.TestCase):
    def test_parses_thresholds_findings_and_expected_changes(self) -> None:
        rules = analysis_rules_from_mapping(
            {
                "thresholds": {"cpu_usage": {"warning_percent": 45, "critical_percent": 75}},
                "findings": {
                    "interface_down": {
                        "title": "인터페이스 Down",
                        "impact_reason": "링크 영향",
                        "action_hint": "포트 확인",
                        "priority": 20,
                    }
                },
                "expected_changes": [
                    {
                        "stage_slugs": ["bb3_off"],
                        "device_names": ["backbone3"],
                        "command_ids": ["device_connectivity"],
                        "summaries": ["Target device connection failed."],
                        "title": "계획된 백본3 OFF",
                        "action_hint": "백본4 경로 확인",
                    }
                ],
            }
        )

        self.assertEqual(rules.threshold("cpu_usage", "warning_percent", 50), 45.0)
        finding = rules.finding("interface_down")
        self.assertEqual(finding.title, "인터페이스 Down")
        self.assertEqual(finding.priority, 20)
        expected = rules.expected_change(
            stage_slug="bb3_off",
            device_name="backbone3",
            command_id="device_connectivity",
            summary="Target device connection failed.",
        )
        self.assertIsNotNone(expected)
        self.assertEqual(expected.title, "계획된 백본3 OFF")

    def test_invalid_finding_severity_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            analysis_rules_from_mapping({"findings": {"bad": {"severity": "Severe"}}})

    def test_load_missing_file_returns_empty_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules = load_analysis_rules(Path(tmp) / "missing.yaml")

        self.assertEqual(rules.threshold("cpu_usage", "warning_percent", 50), 50.0)
        self.assertEqual(rules.finding("unknown").title, "확인 필요")


if __name__ == "__main__":
    unittest.main()
