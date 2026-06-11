from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from backbone_state_tracker.tools.verify_release_package import verify_release_package
from backbone_state_tracker.tools.write_release_manifest import (
    write_package_checksum,
    write_release_manifest,
)


def _write_zip(path: Path, entries: dict[str, str | bytes]) -> None:
    with ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _common_entries() -> dict[str, str]:
    return {
        "backbone_state_tracker/PACKAGE_INFO.txt": "package",
        "backbone_state_tracker/README.md": "readme",
        "backbone_state_tracker/CHANGELOG.md": "changelog",
        "backbone_state_tracker/config/commands.yaml": "commands",
        "backbone_state_tracker/config/devices.example.yaml": "devices example",
        "backbone_state_tracker/docs/USER_GUIDE.md": "user md",
        "backbone_state_tracker/docs/USER_GUIDE.html": "user html",
        "backbone_state_tracker/docs/DEVELOPER_GUIDE_BEGINNER.md": "dev md",
        "backbone_state_tracker/docs/DEVELOPER_GUIDE_BEGINNER.html": "dev html",
        "backbone_state_tracker/docs/VERSION_HISTORY.md": "history md",
        "backbone_state_tracker/docs/VERSION_HISTORY.html": "history html",
    }


def _source_entries() -> dict[str, str]:
    entries = _common_entries()
    entries.update(
        {
            "backbone_state_tracker/app.py": "app",
            "backbone_state_tracker/core/version.py": "version",
            "backbone_state_tracker/tools/build_release.ps1": "source build",
            "backbone_state_tracker/tools/build_windows_exe.ps1": "exe build",
            "backbone_state_tracker/tools/write_release_manifest.py": "manifest tool",
            "backbone_state_tracker/tools/verify_release_package.py": "verifier",
            "backbone_state_tracker/tests/test_release_manifest.py": "manifest tests",
            "backbone_state_tracker/tests/test_release_package_verifier.py": "verifier tests",
        }
    )
    return entries


class ReleasePackageVerifierTests(unittest.TestCase):
    def test_valid_source_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.1_20260611_source.zip"
            _write_zip(package, _source_entries())
            write_package_checksum(package, "0.8.1", generated_at="2026-06-11T10:00:00+09:00")
            write_release_manifest(
                "backbone_state_tracker",
                "0.8.1",
                "20260611",
                dist,
                generated_at="2026-06-11T10:01:00+09:00",
            )

            result = verify_release_package(package, require_manifest=True)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.package_type, "source")

    def test_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.1_20260611_source.zip"
            _write_zip(package, _source_entries())
            write_package_checksum(package, "0.8.1", generated_at="2026-06-11T10:00:00+09:00")
            _write_zip(package, _source_entries() | {"backbone_state_tracker/extra.txt": "changed"})

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(any("SHA256 mismatch" in error for error in result.errors))
            self.assertTrue(any("Size mismatch" in error for error in result.errors))

    def test_forbidden_local_devices_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.1_20260611_source.zip"
            entries = _source_entries()
            entries["backbone_state_tracker/config/devices.yaml"] = "secret host data"
            _write_zip(package, entries)
            write_package_checksum(package, "0.8.1", generated_at="2026-06-11T10:00:00+09:00")

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(any("Forbidden ZIP entry" in error for error in result.errors))

    def test_requires_matching_version_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.1_20260611_source.zip"
            _write_zip(package, _source_entries())
            write_package_checksum(package, "0.8.1", generated_at="2026-06-11T10:00:00+09:00")
            (dist / "backbone_state_tracker_v0.8.0_20260611_release_manifest.txt").write_text(
                "Backbone State Tracker Release Manifest\n",
                encoding="utf-8",
            )

            result = verify_release_package(package, require_manifest=True)

            self.assertFalse(result.ok)
            self.assertTrue(
                any("backbone_state_tracker_v0.8.1_20260611_release_manifest.txt" in error for error in result.errors)
            )


if __name__ == "__main__":
    unittest.main()
