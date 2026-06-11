from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from backbone_state_tracker.tools.write_release_manifest import (
    write_package_checksum,
    write_release_manifest,
)


class ReleaseManifestTests(unittest.TestCase):
    def test_package_checksum_sidecar_contains_hash_size_version_and_date_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "backbone_state_tracker_v0.8.0_20260611_source.zip"
            payload = b"source package payload"
            package.write_bytes(payload)

            sidecar = write_package_checksum(
                package,
                "0.8.0",
                generated_at="2026-06-11T10:00:00+09:00",
            )

            expected_hash = hashlib.sha256(payload).hexdigest()
            content = sidecar.read_text(encoding="utf-8")
            self.assertIn(f"SHA256 ({package.name}) = {expected_hash}", content)
            self.assertIn(f"Size = {len(payload)} bytes", content)
            self.assertIn("Version = v0.8.0", content)
            self.assertIn("Date stamp = 20260611", content)
            self.assertIn("Get-FileHash -Algorithm SHA256", content)

    def test_release_manifest_lists_only_matching_zip_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            source = dist / "backbone_state_tracker_v0.8.0_20260611_source.zip"
            exe = dist / "backbone_state_tracker_v0.8.0_20260611_windows_exe.zip"
            older = dist / "backbone_state_tracker_v0.7.9_20260611_source.zip"
            sidecar = dist / "backbone_state_tracker_v0.8.0_20260611_source.zip.sha256.txt"

            source.write_bytes(b"source")
            exe.write_bytes(b"exe")
            older.write_bytes(b"old")
            sidecar.write_text("not a package", encoding="utf-8")

            manifest = write_release_manifest(
                "backbone_state_tracker",
                "0.8.0",
                "20260611",
                dist,
                generated_at="2026-06-11T10:05:00+09:00",
            )

            content = manifest.read_text(encoding="utf-8")
            self.assertIn(f"- Package: {source.name}", content)
            self.assertIn(f"- Package: {exe.name}", content)
            self.assertNotIn(f"- Package: {older.name}", content)
            self.assertNotIn(f"- Package: {sidecar.name}", content)
            self.assertIn(hashlib.sha256(b"source").hexdigest(), content)
            self.assertIn(hashlib.sha256(b"exe").hexdigest(), content)


if __name__ == "__main__":
    unittest.main()
