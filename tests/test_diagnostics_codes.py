from __future__ import annotations

import unittest

from backbone_state_tracker.core.diagnostics.codes import explain_code, get_code, list_codes, validate_catalog


class DiagnosticCodeTests(unittest.TestCase):
    def test_catalog_is_valid_and_unique(self) -> None:
        self.assertEqual([], validate_catalog())
        codes = [item.code for item in list_codes()]
        self.assertEqual(len(codes), len(set(codes)))

    def test_explain_known_code_contains_actionable_context(self) -> None:
        text = explain_code("bst-con-301")

        self.assertIn("BST-CON-301 TCP_TIMEOUT", text)
        self.assertIn("심각도: 긴급", text)
        self.assertIn("조치:", text)
        self.assertIn("TCP 연결 시간이 초과됐습니다.", text)

    def test_unknown_code_explains_version_mismatch_possibility(self) -> None:
        text = explain_code("BST-XXX-999")

        self.assertIn("UNKNOWN", text)
        self.assertIn("애플리케이션 버전", text)

    def test_get_code_is_case_insensitive(self) -> None:
        item = get_code("bst-sec-201")

        self.assertIsNotNone(item)
        self.assertEqual("SECRET_REDACTED", item.name)


if __name__ == "__main__":
    unittest.main()
