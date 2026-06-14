from __future__ import annotations

from pathlib import Path
import re
import unittest

from backbone_state_tracker.core.config import load_commands


PROJECT_DIR = Path(__file__).resolve().parents[1]


class DocumentationPortabilityTests(unittest.TestCase):
    def test_guides_do_not_embed_developer_workspace_paths(self) -> None:
        paths = [PROJECT_DIR / "README.md"]
        paths.extend(sorted((PROJECT_DIR / "docs").glob("*.md")))
        paths.extend(sorted((PROJECT_DIR / "docs").glob("*.html")))
        forbidden_fragments = [
            r"D:\Codex Project",
            r"D:\Project\Network",
            r"C:\Users\sebia",
        ]

        offenders: list[str] = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                if fragment in text:
                    offenders.append(f"{path.relative_to(PROJECT_DIR)} contains {fragment}")

        self.assertEqual([], offenders)

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
