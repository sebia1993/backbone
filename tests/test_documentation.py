from __future__ import annotations

from pathlib import Path
import unittest


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
