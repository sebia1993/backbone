from __future__ import annotations

import argparse
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

try:
    from backbone_state_tracker.tools.write_release_manifest import file_sha256
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution.
    from write_release_manifest import file_sha256


SHA256_LINE = re.compile(r"^SHA256 \((?P<name>.+)\) = (?P<sha256>[0-9a-f]{64})$", re.MULTILINE)
SIZE_LINE = re.compile(r"^Size = (?P<size>\d+) bytes$", re.MULTILINE)
VERSION_LINE = re.compile(r"^Version = (?P<version>v?\d+\.\d+\.\d+)$", re.MULTILINE)
DATE_STAMP_LINE = re.compile(r"^Date stamp = (?P<date>\d{8})$", re.MULTILINE)
MANIFEST_PACKAGE_LINE = re.compile(r"^- Package: (?P<name>.+)$")
MANIFEST_SIZE_LINE = re.compile(r"^  Size: (?P<size>\d+) bytes$")
MANIFEST_SHA_LINE = re.compile(r"^  SHA256: (?P<sha256>[0-9a-f]{64})$")
PACKAGE_PREFIX = re.compile(
    r"^(?P<prefix>.+_v(?P<version>\d+\.\d+\.\d+)_(?P<date>\d{8}))_(source|windows_exe)\.zip$"
)
PACKAGE_ROOT = "backbone_state_tracker/"
PACKAGE_ROOT_NAME = "backbone_state_tracker"
WINDOWS_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:/")

COMMON_REQUIRED = {
    "backbone_state_tracker/PACKAGE_INFO.txt",
    "backbone_state_tracker/README.md",
    "backbone_state_tracker/CHANGELOG.md",
    "backbone_state_tracker/config/commands.yaml",
    "backbone_state_tracker/config/devices.example.yaml",
    "backbone_state_tracker/docs/USER_GUIDE.md",
    "backbone_state_tracker/docs/USER_GUIDE.html",
    "backbone_state_tracker/docs/COMMAND_GUIDE.md",
    "backbone_state_tracker/docs/COMMAND_GUIDE.html",
    "backbone_state_tracker/docs/DEVELOPER_GUIDE_BEGINNER.md",
    "backbone_state_tracker/docs/DEVELOPER_GUIDE_BEGINNER.html",
    "backbone_state_tracker/docs/VERSION_HISTORY.md",
    "backbone_state_tracker/docs/VERSION_HISTORY.html",
    "backbone_state_tracker/docs/RELEASE_CHECKLIST.md",
    "backbone_state_tracker/docs/RELEASE_CHECKLIST.html",
    "backbone_state_tracker/docs/images/settings-collection.png",
    "backbone_state_tracker/docs/images/compare-results.png",
    "backbone_state_tracker/docs/images/work-log.png",
}

SOURCE_REQUIRED = COMMON_REQUIRED | {
    "backbone_state_tracker/app.py",
    "backbone_state_tracker/core/version.py",
    "backbone_state_tracker/tools/build_release.ps1",
    "backbone_state_tracker/tools/build_windows_exe.ps1",
    "backbone_state_tracker/tools/write_release_manifest.py",
    "backbone_state_tracker/tools/verify_release_package.py",
    "backbone_state_tracker/tools/verify_release_package.ps1",
    "backbone_state_tracker/tests/test_diff_engine.py",
    "backbone_state_tracker/tests/test_documentation.py",
    "backbone_state_tracker/tests/test_gui_formatting.py",
    "backbone_state_tracker/tests/test_mock_validation.py",
    "backbone_state_tracker/tests/test_preflight.py",
    "backbone_state_tracker/tests/test_redaction.py",
    "backbone_state_tracker/tests/test_release_manifest.py",
    "backbone_state_tracker/tests/test_release_package_verifier.py",
    "backbone_state_tracker/tests/test_reporter.py",
    "backbone_state_tracker/tests/test_snapshot.py",
    "backbone_state_tracker/tests/test_workflow.py",
}

WINDOWS_EXE_REQUIRED = COMMON_REQUIRED | {
    "backbone_state_tracker/BackboneStateTracker.exe",
    "backbone_state_tracker/RUN_FIRST.txt",
}

FORBIDDEN_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"/\.git/",
        r"/outputs/",
        r"/dist/",
        r"/build/",
        r"/raw/",
        r"/config/devices\.yaml$",
        r"__pycache__",
        r"\.pyc$",
        r"\.spec$",
    )
]


@dataclass(frozen=True)
class VerificationResult:
    package_path: Path
    package_type: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def infer_package_type(package_path: Path) -> str:
    name = package_path.name.lower()
    if name.endswith("_source.zip"):
        return "source"
    if name.endswith("_windows_exe.zip"):
        return "windows_exe"
    return "unknown"


def version_label(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


def package_identity(package_path: Path) -> tuple[str, str] | None:
    match = PACKAGE_PREFIX.match(package_path.name)
    if not match:
        return None
    return version_label(match.group("version")), match.group("date")


def parse_checksum_sidecar(
    sidecar_path: Path,
) -> tuple[str | None, str | None, int | None, str | None, str | None, list[str]]:
    errors: list[str] = []
    if not sidecar_path.is_file():
        return None, None, None, None, None, [f"Missing checksum sidecar: {sidecar_path.name}"]

    text = sidecar_path.read_text(encoding="utf-8")
    sha_match = SHA256_LINE.search(text)
    size_match = SIZE_LINE.search(text)
    version_match = VERSION_LINE.search(text)
    date_match = DATE_STAMP_LINE.search(text)
    sidecar_package_name = sha_match.group("name") if sha_match else None
    expected_sha = sha_match.group("sha256") if sha_match else None
    expected_size = int(size_match.group("size")) if size_match else None
    expected_version = version_label(version_match.group("version")) if version_match else None
    expected_date = date_match.group("date") if date_match else None
    if expected_sha is None:
        errors.append(f"Checksum sidecar does not contain a SHA256 line: {sidecar_path.name}")
    if expected_size is None:
        errors.append(f"Checksum sidecar does not contain a Size line: {sidecar_path.name}")
    if expected_version is None:
        errors.append(f"Checksum sidecar does not contain a Version line: {sidecar_path.name}")
    if expected_date is None:
        errors.append(f"Checksum sidecar does not contain a Date stamp line: {sidecar_path.name}")
    return sidecar_package_name, expected_sha, expected_size, expected_version, expected_date, errors


def parse_manifest_package_records(manifest_text: str) -> dict[str, dict[str, str | int]]:
    records: dict[str, dict[str, str | int]] = {}
    current_name: str | None = None
    for line in manifest_text.splitlines():
        package_match = MANIFEST_PACKAGE_LINE.match(line)
        if package_match:
            current_name = package_match.group("name")
            records[current_name] = {}
            continue
        if current_name is None:
            continue
        size_match = MANIFEST_SIZE_LINE.match(line)
        if size_match:
            records[current_name]["size_bytes"] = int(size_match.group("size"))
            continue
        sha_match = MANIFEST_SHA_LINE.match(line)
        if sha_match:
            records[current_name]["sha256"] = sha_match.group("sha256")
    return records


def duplicate_manifest_package_record_errors(manifest_text: str) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for line in manifest_text.splitlines():
        package_match = MANIFEST_PACKAGE_LINE.match(line)
        if not package_match:
            continue
        package_name = package_match.group("name")
        if package_name in seen:
            errors.append(f"Duplicate release manifest package record found: {package_name}")
        else:
            seen.add(package_name)
    return errors


def normalized_zip_names(package_path: Path) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    names: set[str] = set()
    try:
        with zipfile.ZipFile(package_path) as archive:
            for info in archive.infolist():
                name = info.filename.replace("\\", "/")
                if name in names:
                    errors.append(f"Duplicate ZIP entry found: {name}")
                else:
                    names.add(name)
    except zipfile.BadZipFile:
        errors.append(f"Not a readable ZIP file: {package_path.name}")
    return names, errors


def zip_entry_safety_errors(names: set[str]) -> list[str]:
    errors: list[str] = []
    for name in sorted(names):
        normalized = name.replace("\\", "/")
        stripped = normalized.rstrip("/")
        parts = stripped.split("/") if stripped else []
        unsafe = (
            normalized.startswith("/")
            or WINDOWS_DRIVE_PREFIX.match(normalized) is not None
            or not stripped
            or any(part in ("", ".", "..") for part in parts)
        )
        if unsafe:
            errors.append(f"Unsafe ZIP entry found: {name}")
            continue
        if stripped != PACKAGE_ROOT_NAME and not normalized.startswith(PACKAGE_ROOT):
            errors.append(f"Unexpected ZIP root entry found: {name}")
    return errors


def required_entries_for(package_type: str) -> set[str]:
    if package_type == "source":
        return SOURCE_REQUIRED
    if package_type == "windows_exe":
        return WINDOWS_EXE_REQUIRED
    return COMMON_REQUIRED


def expected_manifest_path(package_path: Path) -> Path | None:
    match = PACKAGE_PREFIX.match(package_path.name)
    if not match:
        return None
    return package_path.with_name(f"{match.group('prefix')}_release_manifest.txt")


def verify_release_package(
    package_path: Path,
    package_type: str | None = None,
    require_manifest: bool = False,
) -> VerificationResult:
    package_path = Path(package_path)
    resolved_type = package_type or infer_package_type(package_path)
    errors: list[str] = []
    warnings: list[str] = []

    if not package_path.is_file():
        return VerificationResult(
            package_path=package_path,
            package_type=resolved_type,
            errors=(f"Package does not exist: {package_path}",),
            warnings=(),
        )

    identity = package_identity(package_path)
    expected_version = identity[0] if identity else None
    expected_date = identity[1] if identity else None

    sidecar_path = package_path.with_name(f"{package_path.name}.sha256.txt")
    sidecar_package_name, expected_sha, expected_size, sidecar_version, sidecar_date, sidecar_errors = parse_checksum_sidecar(
        sidecar_path
    )
    errors.extend(sidecar_errors)
    if sidecar_package_name is not None and sidecar_package_name != package_path.name:
        errors.append(
            f"Checksum sidecar package mismatch: expected {package_path.name}, sidecar {sidecar_package_name}"
        )
    if expected_version is not None and sidecar_version is not None and sidecar_version != expected_version:
        errors.append(
            f"Checksum sidecar version mismatch for {package_path.name}: "
            f"expected {expected_version}, sidecar {sidecar_version}"
        )
    if expected_date is not None and sidecar_date is not None and sidecar_date != expected_date:
        errors.append(
            f"Checksum sidecar date mismatch for {package_path.name}: "
            f"expected {expected_date}, sidecar {sidecar_date}"
        )

    actual_sha = file_sha256(package_path)
    actual_size = package_path.stat().st_size
    if expected_sha is not None and actual_sha != expected_sha:
        errors.append(f"SHA256 mismatch for {package_path.name}: expected {expected_sha}, actual {actual_sha}")
    if expected_size is not None and actual_size != expected_size:
        errors.append(f"Size mismatch for {package_path.name}: expected {expected_size}, actual {actual_size}")

    names, zip_errors = normalized_zip_names(package_path)
    errors.extend(zip_errors)
    if names:
        errors.extend(zip_entry_safety_errors(names))

        required_entries = required_entries_for(resolved_type)
        missing = sorted(required_entries - names)
        errors.extend(f"Missing required ZIP entry: {entry}" for entry in missing)

        for name in sorted(names):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(name):
                    errors.append(f"Forbidden ZIP entry found: {name}")
                    break

    manifest_path = expected_manifest_path(package_path)
    if manifest_path is None:
        message = "Release manifest was not found next to the package."
        if require_manifest:
            errors.append(message)
        else:
            warnings.append(message)
    elif not manifest_path.is_file():
        message = f"Release manifest was not found next to the package: {manifest_path.name}"
        if require_manifest:
            errors.append(message)
        else:
            warnings.append(message)
    else:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        errors.extend(duplicate_manifest_package_record_errors(manifest_text))
        if expected_version is not None:
            manifest_version_match = VERSION_LINE.search(manifest_text)
            manifest_version = (
                version_label(manifest_version_match.group("version")) if manifest_version_match else None
            )
            if manifest_version is None:
                errors.append(f"Release manifest does not contain a Version line: {manifest_path.name}")
            elif manifest_version != expected_version:
                errors.append(
                    f"Release manifest version mismatch for {package_path.name}: "
                    f"expected {expected_version}, manifest {manifest_version}"
                )
        if expected_date is not None:
            manifest_date_match = DATE_STAMP_LINE.search(manifest_text)
            manifest_date = manifest_date_match.group("date") if manifest_date_match else None
            if manifest_date is None:
                errors.append(f"Release manifest does not contain a Date stamp line: {manifest_path.name}")
            elif manifest_date != expected_date:
                errors.append(
                    f"Release manifest date mismatch for {package_path.name}: "
                    f"expected {expected_date}, manifest {manifest_date}"
                )
        package_records = parse_manifest_package_records(manifest_text)
        package_record = package_records.get(package_path.name)
        if package_record is None:
            errors.append(f"Release manifest does not list package record: {package_path.name}")
        else:
            manifest_size = package_record.get("size_bytes")
            manifest_sha = package_record.get("sha256")
            if manifest_size is None:
                errors.append(f"Release manifest package record does not list size: {package_path.name}")
            elif manifest_size != actual_size:
                errors.append(
                    f"Release manifest package size mismatch for {package_path.name}: "
                    f"expected {actual_size}, manifest {manifest_size}"
                )
            if manifest_sha is None:
                errors.append(f"Release manifest package record does not list SHA256: {package_path.name}")
            elif manifest_sha != actual_sha:
                errors.append(
                    f"Release manifest package SHA256 mismatch for {package_path.name}: "
                    f"expected {actual_sha}, manifest {manifest_sha}"
                )

    return VerificationResult(
        package_path=package_path,
        package_type=resolved_type,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a Backbone State Tracker release ZIP.")
    parser.add_argument("package", type=Path)
    parser.add_argument("--type", choices=("source", "windows_exe", "unknown"), default=None)
    parser.add_argument("--require-manifest", action="store_true")
    args = parser.parse_args(argv)

    result = verify_release_package(
        args.package,
        package_type=args.type,
        require_manifest=args.require_manifest,
    )
    print(f"Package: {result.package_path}")
    print(f"Type: {result.package_type}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")
    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"- {error}")
        return 1
    print("Verification OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
