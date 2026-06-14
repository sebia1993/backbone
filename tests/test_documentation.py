from __future__ import annotations

from pathlib import Path
import re
import unittest

from backbone_state_tracker.core.config import load_commands
from backbone_state_tracker.core.version import APP_RELEASE_DATE, APP_VERSION


PROJECT_DIR = Path(__file__).resolve().parents[1]


class DocumentationPortabilityTests(unittest.TestCase):
    def _documentation_paths(self) -> list[Path]:
        paths = [PROJECT_DIR / "README.md", PROJECT_DIR / "CHANGELOG.md"]
        paths.extend(sorted((PROJECT_DIR / "docs").glob("*.md")))
        paths.extend(sorted((PROJECT_DIR / "docs").glob("*.html")))
        return paths

    def test_guides_do_not_embed_developer_workspace_paths(self) -> None:
        forbidden_fragments = [
            r"D:\Codex Project",
            r"D:\Project\Network",
            r"C:\Users\sebia",
        ]

        offenders: list[str] = []
        for path in self._documentation_paths():
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                if fragment in text:
                    offenders.append(f"{path.relative_to(PROJECT_DIR)} contains {fragment}")

        self.assertEqual([], offenders)

    def test_guides_do_not_contain_mojibake_or_replacement_characters(self) -> None:
        forbidden_fragments = ["�", "臾", "踰", "媛", "珥", "由", "諛", "蹂"]

        offenders: list[str] = []
        for path in self._documentation_paths():
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                if fragment in text:
                    offenders.append(f"{path.relative_to(PROJECT_DIR)} contains {fragment}")

        self.assertEqual([], offenders)

    def test_user_facing_guides_keep_required_korean_workflow_terms(self) -> None:
        required_terms = [
            "장비 설정",
            "비교 결과",
            "작업 로그",
            "긴급",
            "주의",
            "정보",
            "변경없음",
        ]
        guide_paths = [
            PROJECT_DIR / "docs" / "USER_GUIDE.md",
            PROJECT_DIR / "docs" / "USER_GUIDE.html",
            PROJECT_DIR / "docs" / "DEVELOPER_GUIDE_BEGINNER.md",
            PROJECT_DIR / "docs" / "DEVELOPER_GUIDE_BEGINNER.html",
        ]

        missing: list[str] = []
        for path in guide_paths:
            text = path.read_text(encoding="utf-8")
            for term in required_terms:
                if term not in text:
                    missing.append(f"{path.relative_to(PROJECT_DIR)} missing {term}")

        self.assertEqual([], missing)

    def test_user_guide_images_exist_and_are_referenced(self) -> None:
        image_names = [
            "settings-collection.png",
            "compare-results.png",
            "work-log.png",
        ]
        user_md = (PROJECT_DIR / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")
        user_html = (PROJECT_DIR / "docs" / "USER_GUIDE.html").read_text(encoding="utf-8")

        for image_name in image_names:
            image_path = PROJECT_DIR / "docs" / "images" / image_name
            self.assertTrue(image_path.exists(), f"missing {image_path}")
            self.assertGreater(image_path.stat().st_size, 1000)
            self.assertIn(f"images/{image_name}", user_md)
            self.assertIn(f"images/{image_name}", user_html)

    def test_command_guide_md_and_html_match_bundled_command_ids(self) -> None:
        expected_ids = [command.id for command in load_commands(PROJECT_DIR / "config" / "commands.yaml")]
        command_md = (PROJECT_DIR / "docs" / "COMMAND_GUIDE.md").read_text(encoding="utf-8")
        command_html = (PROJECT_DIR / "docs" / "COMMAND_GUIDE.html").read_text(encoding="utf-8")

        md_ids = re.findall(r"\| `([^`]+)` \|", command_md)
        html_ids = re.findall(r"<tr><td><code>([^<]+)</code></td><td><code>[^<]+</code></td>", command_html)

        self.assertEqual(expected_ids, md_ids)
        self.assertEqual(expected_ids, html_ids)

    def test_current_version_is_reflected_in_release_documents(self) -> None:
        version = f"v{APP_VERSION}"
        date_stamp = APP_RELEASE_DATE.replace("-", "")
        expectations = {
            "README.md": (
                f"Version: `{version}`",
                f"backbone_state_tracker_{version}_YYYYMMDD_windows_exe.zip",
            ),
            "CHANGELOG.md": (f"## {version} - {APP_RELEASE_DATE}",),
            "docs/COMMAND_GUIDE.md": (f"문서 버전: {version}",),
            "docs/COMMAND_GUIDE.html": (
                f"점검 명령어 가이드 {version}",
                f"문서 버전: {version}",
            ),
            "docs/DEVELOPER_GUIDE_BEGINNER.md": (f"문서 버전: {version}",),
            "docs/DEVELOPER_GUIDE_BEGINNER.html": (
                f"초급 개발자 가이드 {version}",
                f"문서 버전: {version}",
            ),
            "docs/USER_GUIDE.md": (
                f"문서 버전: {version}",
                f"backbone_state_tracker_{version}_YYYYMMDD_windows_exe.zip",
            ),
            "docs/USER_GUIDE.html": (
                f"사용자 가이드 {version}",
                f"문서 버전: {version}",
            ),
            "docs/RELEASE_CHECKLIST.md": (
                f"문서 버전: {version}",
                f"backbone_state_tracker_{version}_YYYYMMDD_source.zip",
                f"backbone_state_tracker_{version}_YYYYMMDD_windows_exe.zip",
            ),
            "docs/RELEASE_CHECKLIST.html": (
                f"릴리스 반입 체크리스트 {version}",
                f"문서 버전: {version}",
                f"backbone_state_tracker_{version}_YYYYMMDD_source.zip",
            ),
            "docs/VERSION_HISTORY.md": (
                f"문서 버전: {version}",
                f"### {version} - {APP_RELEASE_DATE}",
                f"dist\\backbone_state_tracker_{version}_{date_stamp}_source.zip",
                f"dist\\backbone_state_tracker_{version}_{date_stamp}_windows_exe.zip",
            ),
            "docs/VERSION_HISTORY.html": (
                f"버전별 변경내역 {version}",
                f"문서 버전: {version}",
                f"<h3>{version} - {APP_RELEASE_DATE}</h3>",
                f"dist\\backbone_state_tracker_{version}_{date_stamp}_source.zip",
            ),
        }

        missing: list[str] = []
        for relative_path, required_fragments in expectations.items():
            text = (PROJECT_DIR / relative_path).read_text(encoding="utf-8")
            for fragment in required_fragments:
                if fragment not in text:
                    missing.append(f"{relative_path} missing {fragment}")

        self.assertEqual([], missing)
