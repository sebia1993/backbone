from __future__ import annotations

import tempfile
import unittest
import warnings
from pathlib import Path
from zipfile import ZipFile

from backbone_state_tracker.tools.verify_release_package import verify_release_package
from backbone_state_tracker.tools.write_release_manifest import (
    file_sha256,
    write_package_checksum,
    write_release_manifest,
)


def _write_zip(path: Path, entries: dict[str, str | bytes]) -> None:
    with ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _write_zip_items(path: Path, entries: list[tuple[str, str | bytes]]) -> None:
    with ZipFile(path, "w") as archive:
        for name, content in entries:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
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
        "backbone_state_tracker/docs/COMMAND_GUIDE.md": "command md",
        "backbone_state_tracker/docs/COMMAND_GUIDE.html": "command html",
        "backbone_state_tracker/docs/DEVELOPER_GUIDE_BEGINNER.md": "dev md",
        "backbone_state_tracker/docs/DEVELOPER_GUIDE_BEGINNER.html": "dev html",
        "backbone_state_tracker/docs/VERSION_HISTORY.md": "history md",
        "backbone_state_tracker/docs/VERSION_HISTORY.html": "history html",
        "backbone_state_tracker/docs/RELEASE_CHECKLIST.md": "release checklist md",
        "backbone_state_tracker/docs/RELEASE_CHECKLIST.html": "release checklist html",
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
            "backbone_state_tracker/tools/verify_release_package.ps1": "powershell verifier",
            "backbone_state_tracker/tests/test_documentation.py": "documentation tests",
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

    def test_unexpected_top_level_zip_entry_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.11_20260612_source.zip"
            entries = _source_entries()
            entries["unexpected.txt"] = "unexpected top-level file"
            _write_zip(package, entries)
            write_package_checksum(package, "0.8.11", generated_at="2026-06-12T10:00:00+09:00")

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(
                any("Unexpected ZIP root entry found: unexpected.txt" in error for error in result.errors)
            )

    def test_zip_entry_path_traversal_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.11_20260612_source.zip"
            entries = _source_entries()
            entries["backbone_state_tracker/../unexpected.txt"] = "path traversal"
            _write_zip(package, entries)
            write_package_checksum(package, "0.8.11", generated_at="2026-06-12T10:00:00+09:00")

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(
                any(
                    "Unsafe ZIP entry found: backbone_state_tracker/../unexpected.txt" in error
                    for error in result.errors
                )
            )

    def test_absolute_zip_entries_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.11_20260612_source.zip"
            entries = _source_entries()
            entries["/tmp/unexpected.txt"] = "absolute path"
            entries["C:/temp/unexpected.txt"] = "windows drive path"
            _write_zip(package, entries)
            write_package_checksum(package, "0.8.11", generated_at="2026-06-12T10:00:00+09:00")

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(any("Unsafe ZIP entry found: /tmp/unexpected.txt" in error for error in result.errors))
            self.assertTrue(
                any("Unsafe ZIP entry found: C:/temp/unexpected.txt" in error for error in result.errors)
            )

    def test_duplicate_zip_entry_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.12_20260612_source.zip"
            duplicate_name = "backbone_state_tracker/docs/USER_GUIDE.md"
            entries = list(_source_entries().items())
            entries.append((duplicate_name, "duplicate user guide"))
            _write_zip_items(package, entries)
            write_package_checksum(package, "0.8.12", generated_at="2026-06-12T10:00:00+09:00")

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(
                any(f"Duplicate ZIP entry found: {duplicate_name}" in error for error in result.errors)
            )

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

    def test_missing_release_checklist_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.8_20260612_source.zip"
            entries = _source_entries()
            del entries["backbone_state_tracker/docs/RELEASE_CHECKLIST.md"]
            _write_zip(package, entries)
            write_package_checksum(package, "0.8.8", generated_at="2026-06-12T10:00:00+09:00")

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(
                any("backbone_state_tracker/docs/RELEASE_CHECKLIST.md" in error for error in result.errors)
            )

    def test_sidecar_version_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.9_20260612_source.zip"
            _write_zip(package, _source_entries())
            write_package_checksum(package, "0.8.8", generated_at="2026-06-12T10:00:00+09:00")

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(any("Checksum sidecar version mismatch" in error for error in result.errors))

    def test_sidecar_package_name_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.10_20260612_source.zip"
            _write_zip(package, _source_entries())
            sidecar = write_package_checksum(package, "0.8.10", generated_at="2026-06-12T10:00:00+09:00")
            sidecar.write_text(
                sidecar.read_text(encoding="utf-8").replace(
                    f"SHA256 ({package.name})",
                    "SHA256 (backbone_state_tracker_v0.8.10_20260612_windows_exe.zip)",
                ),
                encoding="utf-8",
            )

            result = verify_release_package(package)

            self.assertFalse(result.ok)
            self.assertTrue(any("Checksum sidecar package mismatch" in error for error in result.errors))

    def test_manifest_version_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.9_20260612_source.zip"
            _write_zip(package, _source_entries())
            write_package_checksum(package, "0.8.9", generated_at="2026-06-12T10:00:00+09:00")
            (dist / "backbone_state_tracker_v0.8.9_20260612_release_manifest.txt").write_text(
                "\n".join(
                    [
                        "Backbone State Tracker Release Manifest",
                        "Project = backbone_state_tracker",
                        "Version = v0.8.8",
                        "Date stamp = 20260612",
                        "Generated = 2026-06-12T10:01:00+09:00",
                        "",
                        "Packages",
                        f"- Package: {package.name}",
                        f"  Size: {package.stat().st_size} bytes",
                        f"  SHA256: {file_sha256(package)}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = verify_release_package(package, require_manifest=True)

            self.assertFalse(result.ok)
            self.assertTrue(any("Release manifest version mismatch" in error for error in result.errors))

    def test_manifest_date_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.9_20260612_source.zip"
            _write_zip(package, _source_entries())
            write_package_checksum(package, "0.8.9", generated_at="2026-06-12T10:00:00+09:00")
            (dist / "backbone_state_tracker_v0.8.9_20260612_release_manifest.txt").write_text(
                "\n".join(
                    [
                        "Backbone State Tracker Release Manifest",
                        "Project = backbone_state_tracker",
                        "Version = v0.8.9",
                        "Date stamp = 20260611",
                        "Generated = 2026-06-12T10:01:00+09:00",
                        "",
                        "Packages",
                        f"- Package: {package.name}",
                        f"  Size: {package.stat().st_size} bytes",
                        f"  SHA256: {file_sha256(package)}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = verify_release_package(package, require_manifest=True)

            self.assertFalse(result.ok)
            self.assertTrue(any("Release manifest date mismatch" in error for error in result.errors))

    def test_manifest_package_record_sha_mismatch_fails_even_if_hash_exists_elsewhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.10_20260612_source.zip"
            _write_zip(package, _source_entries())
            write_package_checksum(package, "0.8.10", generated_at="2026-06-12T10:00:00+09:00")
            actual_sha = file_sha256(package)
            wrong_sha = "0" * 64
            (dist / "backbone_state_tracker_v0.8.10_20260612_release_manifest.txt").write_text(
                "\n".join(
                    [
                        "Backbone State Tracker Release Manifest",
                        "Project = backbone_state_tracker",
                        "Version = v0.8.10",
                        "Date stamp = 20260612",
                        "Generated = 2026-06-12T10:01:00+09:00",
                        "",
                        "Packages",
                        f"- Package: {package.name}",
                        f"  Size: {package.stat().st_size} bytes",
                        f"  SHA256: {wrong_sha}",
                        "- Package: unrelated.zip",
                        "  Size: 1 bytes",
                        f"  SHA256: {actual_sha}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = verify_release_package(package, require_manifest=True)

            self.assertFalse(result.ok)
            self.assertTrue(any("Release manifest package SHA256 mismatch" in error for error in result.errors))

    def test_manifest_package_record_size_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            package = dist / "backbone_state_tracker_v0.8.10_20260612_source.zip"
            _write_zip(package, _source_entries())
            write_package_checksum(package, "0.8.10", generated_at="2026-06-12T10:00:00+09:00")
            (dist / "backbone_state_tracker_v0.8.10_20260612_release_manifest.txt").write_text(
                "\n".join(
                    [
                        "Backbone State Tracker Release Manifest",
                        "Project = backbone_state_tracker",
                        "Version = v0.8.10",
                        "Date stamp = 20260612",
                        "Generated = 2026-06-12T10:01:00+09:00",
                        "",
                        "Packages",
                        f"- Package: {package.name}",
                        f"  Size: {package.stat().st_size + 1} bytes",
                        f"  SHA256: {file_sha256(package)}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = verify_release_package(package, require_manifest=True)

            self.assertFalse(result.ok)
            self.assertTrue(any("Release manifest package size mismatch" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
