from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from backbone_state_tracker.tests.test_release_package_verifier import _windows_entries
from backbone_state_tracker.tools.verify_release_assets import verify_release_assets
from backbone_state_tracker.tools.write_release_manifest import (
    write_package_checksum,
    write_release_manifest,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]
LOCKED_COMPONENTS = {
    "bcrypt": "5.0.0",
    "cffi": "2.1.1",
    "cryptography": "50.0.0",
    "et-xmlfile": "2.0.0",
    "invoke": "3.0.3",
    "markdown-it-py": "4.2.0",
    "mdurl": "0.1.2",
    "netmiko": "4.7.0",
    "ntc-templates": "9.2.0",
    "openpyxl": "3.1.5",
    "paramiko": "4.0.0",
    "pycparser": "3.0",
    "pygments": "2.21.0",
    "pynacl": "1.6.2",
    "pyserial": "3.5",
    "pyyaml": "6.0.3",
    "rich": "15.0.0",
    "ruamel-yaml": "0.19.1",
    "scp": "0.16.1",
    "textfsm": "2.1.0",
}


def _sbom_payload(components: dict[str, str] | None = None) -> dict[str, object]:
    versions = components if components is not None else LOCKED_COMPONENTS
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "components": [
            {"type": "library", "name": name, "version": version}
            for name, version in sorted(versions.items())
        ],
    }


class ReleaseAssetTests(unittest.TestCase):
    def test_semver_windows_assets_and_sbom_verify_together(self) -> None:
        source_commit = "1" * 40
        with tempfile.TemporaryDirectory() as temp_dir:
            dist = Path(temp_dir)
            package = dist / "backbone_state_tracker_v0.9.0_windows.zip"
            with ZipFile(package, "w") as archive:
                for name, content in _windows_entries().items():
                    archive.writestr(name, content)
            checksum = write_package_checksum(package, "0.9.0", date_stamp="20260824")
            manifest = write_release_manifest(
                "backbone_state_tracker",
                "0.9.0",
                "20260824",
                dist,
                release_tag="v0.9.0",
                source_commit=source_commit,
            )
            sbom = dist / "backbone_state_tracker_v0.9.0_sbom.cdx.json"
            sbom.write_text(
                json.dumps(_sbom_payload()),
                encoding="utf-8",
            )

            summary = verify_release_assets(
                package,
                checksum,
                manifest,
                sbom,
                version="0.9.0",
                source_commit=source_commit,
                runtime_lock_path=PROJECT_DIR / "requirements-runtime.lock",
            )

        self.assertEqual(summary["version"], "v0.9.0")
        self.assertEqual(summary["sbom_components"], 20)

    def test_incomplete_sbom_component_set_fails_closed(self) -> None:
        payload = _sbom_payload({"netmiko": "4.7.0", "paramiko": "4.0.0"})
        self._assert_invalid_sbom(payload, "component set does not match")

    def test_sbom_requires_positive_top_level_version(self) -> None:
        payload = _sbom_payload()
        del payload["version"]
        self._assert_invalid_sbom(payload, "top-level version")

    def test_asset_date_must_match_app_release_date(self) -> None:
        source_commit = "3" * 40
        with tempfile.TemporaryDirectory() as temp_dir:
            dist = Path(temp_dir)
            package = dist / "backbone_state_tracker_v0.9.0_windows.zip"
            with ZipFile(package, "w") as archive:
                for name, content in _windows_entries().items():
                    archive.writestr(name, content)
            checksum = write_package_checksum(package, "0.9.0", date_stamp="20260823")
            manifest = write_release_manifest(
                "backbone_state_tracker",
                "0.9.0",
                "20260823",
                dist,
                release_tag="v0.9.0",
                source_commit=source_commit,
            )
            sbom = dist / "backbone_state_tracker_v0.9.0_sbom.cdx.json"
            sbom.write_text(json.dumps(_sbom_payload()), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "APP_RELEASE_DATE 20260824"):
                verify_release_assets(
                    package,
                    checksum,
                    manifest,
                    sbom,
                    version="v0.9.0",
                    source_commit=source_commit,
                    runtime_lock_path=PROJECT_DIR / "requirements-runtime.lock",
                )

    def _assert_invalid_sbom(self, payload: dict[str, object], message: str) -> None:
        source_commit = "2" * 40
        with tempfile.TemporaryDirectory() as temp_dir:
            dist = Path(temp_dir)
            package = dist / "backbone_state_tracker_v0.9.0_windows.zip"
            with ZipFile(package, "w") as archive:
                for name, content in _windows_entries().items():
                    archive.writestr(name, content)
            checksum = write_package_checksum(package, "0.9.0", date_stamp="20260824")
            manifest = write_release_manifest(
                "backbone_state_tracker",
                "0.9.0",
                "20260824",
                dist,
                release_tag="v0.9.0",
                source_commit=source_commit,
            )
            sbom = dist / "backbone_state_tracker_v0.9.0_sbom.cdx.json"
            sbom.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, message):
                verify_release_assets(
                    package,
                    checksum,
                    manifest,
                    sbom,
                    version="v0.9.0",
                    source_commit=source_commit,
                    runtime_lock_path=PROJECT_DIR / "requirements-runtime.lock",
                )


if __name__ == "__main__":
    unittest.main()
