from __future__ import annotations

import re
import unittest
from pathlib import Path

from backbone_state_tracker.core.diagnostics.codes import (
    explain_code,
    get_code,
    list_codes,
    validate_catalog,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]


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

    def test_collection_boundary_and_host_key_codes_are_explainable(self) -> None:
        self.assertIn("COLLECTION_BOUNDARY_BLOCKED", explain_code("BST-SEC-001"))
        self.assertIn("SSH_HOST_KEY_REJECTED", explain_code("BST-SEC-002"))

    def test_markdown_and_html_catalogs_match_runtime_registry(self) -> None:
        expected = [item.code for item in list_codes()]
        markdown = (PROJECT_DIR / "docs" / "ERROR_CODE_CATALOG.md").read_text(encoding="utf-8")
        html = (PROJECT_DIR / "docs" / "ERROR_CODE_CATALOG.html").read_text(encoding="utf-8")
        markdown_codes = re.findall(r"^\| `(BST-[A-Z]{3,4}-\d{3})` \|", markdown, re.MULTILINE)
        html_codes = re.findall(r"<tr><td><code>(BST-[A-Z]{3,4}-\d{3})</code></td>", html)

        self.assertEqual(expected, markdown_codes)
        self.assertEqual(expected, html_codes)


if __name__ == "__main__":
    unittest.main()
