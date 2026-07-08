from __future__ import annotations

from pathlib import Path
import re
import unittest

from backbone_state_tracker.core.config import load_commands
from backbone_state_tracker.core.version import APP_RELEASE_DATE, APP_VERSION


PROJECT_DIR = Path(__file__).resolve().parents[1]


class DocumentationPortabilityTests(unittest.TestCase):
    def _documentation_paths(self) -> list[Path]:
        paths = [PROJECT_DIR / "README.md", PROJECT_DIR / "RELEASE_NOTES.md", PROJECT_DIR / "CHANGELOG.md"]
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

    def test_ui_modernization_closeout_guidance_is_documented(self) -> None:
        developer_md = (PROJECT_DIR / "docs" / "DEVELOPER_GUIDE_BEGINNER.md").read_text(encoding="utf-8")
        developer_html = (PROJECT_DIR / "docs" / "DEVELOPER_GUIDE_BEGINNER.html").read_text(encoding="utf-8")
        release_md = (PROJECT_DIR / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
        release_html = (PROJECT_DIR / "docs" / "RELEASE_CHECKLIST.html").read_text(encoding="utf-8")
        user_md = (PROJECT_DIR / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")
        version_md = (PROJECT_DIR / "docs" / "VERSION_HISTORY.md").read_text(encoding="utf-8")

        for text in (developer_md, developer_html):
            for fragment in (
                "디자인 토큰 빠른 참조",
                "컴포넌트 사용 기준",
                "현대화 전 문제 원인",
                "설계 대응 요약",
                "버튼 우선순위",
                "메뉴 배치",
                "PALETTE",
                "SEVERITY_META",
                "SEVERITY_COLORS",
                "SEVERITY_SOFT_COLORS",
                "_make_status_panel",
            ):
                self.assertIn(fragment, text)

        for text in (release_md, release_html):
            for fragment in (
                "UI 마감 확인",
                "어두운 운영 콘솔 레일",
                "teal 계열 배경",
                "선택 변경 맥락",
                "작업 로그",
            ):
                self.assertIn(fragment, text)

        self.assertIn("샘플 데이터로 캡처", user_md)
        self.assertIn("UI 현대화 마감 단계", version_md)
        self.assertIn("UI 현대화 분석 보강", version_md)

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
                f"버전: `{version}`",
                "backbone_state_tracker_<tag>_windows.zip",
                "backbone_state_tracker_v2026.07.08-104830_windows.zip",
            ),
            "RELEASE_NOTES.md": (
                f"현재 앱 버전: `{version}`",
                "backbone_state_tracker_vYYYY.MM.DD-HHMMSS_windows.zip",
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
                "backbone_state_tracker_vYYYY.MM.DD-HHMMSS_windows.zip",
            ),
            "docs/USER_GUIDE.html": (
                f"사용자 가이드 {version}",
                f"문서 버전: {version}",
            ),
            "docs/RELEASE_CHECKLIST.md": (
                f"문서 버전: {version}",
                "backbone_state_tracker_vYYYY.MM.DD-HHMMSS_windows.zip",
                "README_START_HERE_KO.txt",
            ),
            "docs/RELEASE_CHECKLIST.html": (
                f"릴리스 반입 체크리스트 {version}",
                f"문서 버전: {version}",
                "backbone_state_tracker_vYYYY.MM.DD-HHMMSS_windows.zip",
            ),
            "docs/VERSION_HISTORY.md": (
                f"문서 버전: {version}",
                f"### {version} - {APP_RELEASE_DATE}",
                "backbone_state_tracker_vYYYY.MM.DD-HHMMSS_windows.zip",
            ),
            "docs/VERSION_HISTORY.html": (
                f"버전별 변경내역 {version}",
                f"문서 버전: {version}",
                f"<h3>{version} - {APP_RELEASE_DATE}</h3>",
                "backbone_state_tracker_vYYYY.MM.DD-HHMMSS_windows.zip",
            ),
        }

        missing: list[str] = []
        for relative_path, required_fragments in expectations.items():
            text = (PROJECT_DIR / relative_path).read_text(encoding="utf-8")
            for fragment in required_fragments:
                if fragment not in text:
                    missing.append(f"{relative_path} missing {fragment}")

        self.assertEqual([], missing)

    def test_readme_release_document_update_policy_is_tracked(self) -> None:
        expectations = {
            "AGENTS.md": (
                "After code changes, decide whether `README.md`, `RELEASE_NOTES.md`, or",
                "If features are added, changed, or removed, update `README.md`",
                "Before any push, pull request, or release",
                "The current automatic public Release asset is one Windows",
                "Write README steps for users who are not comfortable with GitHub",
            ),
            "README.md": (
                "README / Release 문서 점검 규칙",
                "Git에 커밋하는 파일과 GitHub Release에 올리는 파일은 다릅니다.",
                "GitHub 자동 `Source code (zip)` / `Source code (tar.gz)`는 실행용 파일이 아닙니다.",
                "macOS에서 바로 Windows EXE가 만들어진다고 설명하지 않습니다.",
            ),
            "RELEASE_NOTES.md": (
                "이 파일은 GitHub Release notes를 수동으로 작성하는 파일이 아닙니다.",
                "자동 GitHub Release notes 형식",
                "Git 커밋 파일과 Release asset 구분",
            ),
            "CHANGELOG.md": (
                "README/Release documentation update rule",
                "RELEASE_NOTES.md",
            ),
            "docs/RELEASE_CHECKLIST.md": (
                "README / Release 문서 최신화 확인",
                "`RELEASE_NOTES.md`의 자동 Release notes 형식",
                "`Source code (zip)` / `Source code (tar.gz)`가 실행용 파일이 아니라고 안내",
                "macOS에서 직접 Windows EXE를 만든다고 설명하지 않습니다.",
            ),
            "docs/RELEASE_CHECKLIST.html": (
                "README / Release 문서 최신화 확인",
                "<code>RELEASE_NOTES.md</code>의 자동 Release notes 형식",
                "<code>Source code (zip)</code> / <code>Source code (tar.gz)</code>가 실행용 파일이 아니라고 안내",
                "macOS에서 직접 Windows EXE를 만든다고 설명하지 않습니다.",
            ),
        }

        missing: list[str] = []
        for relative_path, required_fragments in expectations.items():
            text = (PROJECT_DIR / relative_path).read_text(encoding="utf-8")
            for fragment in required_fragments:
                if fragment not in text:
                    missing.append(f"{relative_path} missing {fragment}")

        self.assertEqual([], missing)

    def test_release_workflow_notes_follow_user_facing_release_format(self) -> None:
        workflow = (PROJECT_DIR / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        required_fragments = [
            "${{ steps.release_meta.outputs.tag }} 릴리스입니다.",
            "변경내용:",
            'git log --pretty=format:"- %s" $commitRange',
            "검증:",
            "- Windows 통합 ZIP 빌드 통과",
            "- Windows 통합 ZIP 구조 verifier 통과",
            "빌드:",
            "첨부파일:",
            "- 통합 Windows ZIP:",
            "실행 방법:",
            "gui\\BackboneStateTracker.exe",
            "web\\start_webapp.cmd",
            "Source code (zip)",
            "Source code (tar.gz)",
            "배포 메타데이터:",
            "- 브랜치명:",
            "- 기준 커밋 SHA:",
            "- 통합 ZIP 파일명:",
            "- SHA256 checksum:",
            "- 변경 커밋 목록 ($rangeLabel):",
            'git log --pretty=format:"- %h %s" $commitRange',
        ]

        missing = [fragment for fragment in required_fragments if fragment not in workflow]

        self.assertEqual([], missing)

    def test_pr_workflow_builds_but_does_not_create_release(self) -> None:
        workflow = (PROJECT_DIR / ".github" / "workflows" / "pr-build.yml").read_text(encoding="utf-8")

        self.assertIn("pull_request:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("--type windows", workflow)
        self.assertIn("build_windows_exe.ps1 -SkipTests -ReleaseTag", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("contents: write", workflow)

    def test_release_workflow_is_main_push_only_and_uploads_one_direct_asset(self) -> None:
        workflow = (PROJECT_DIR / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        self.assertIn("push:", workflow)
        self.assertIn("branches:", workflow)
        self.assertIn("- main", workflow)
        self.assertIn("permissions:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("if: github.ref == 'refs/heads/main'", workflow)
        self.assertIn("gh release create", workflow)
        self.assertEqual(1, workflow.count("#${{ steps.artifact.outputs.artifact_name }}"))
        self.assertNotIn("checksum_path", workflow)
        self.assertNotIn("checksum_name", workflow)
        self.assertNotIn(".sha256", workflow)

    def test_release_docs_do_not_restore_cli_execution_guidance(self) -> None:
        checked_paths = [
            PROJECT_DIR / "README.md",
            PROJECT_DIR / "RELEASE_NOTES.md",
            PROJECT_DIR / "docs" / "RELEASE_CHECKLIST.md",
            PROJECT_DIR / "docs" / "RELEASE_CHECKLIST.html",
        ]
        forbidden = [
            "--diagnose",
            "--mock-server",
            "--explain-code",
            "BackboneStateTracker.exe --",
            "SHA256 sidecar",
            "_windows_exe.zip",
        ]

        offenders: list[str] = []
        for path in checked_paths:
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden:
                if fragment in text:
                    offenders.append(f"{path.relative_to(PROJECT_DIR)} contains {fragment}")

        self.assertEqual([], offenders)
