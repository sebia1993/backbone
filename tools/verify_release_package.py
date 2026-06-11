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
PACKAGE_PREFIX = re.compile(r"^(?P<prefix>.+_v\d+\.\d+\.\d+_\d{8})_(source|windows_exe)\.zip$")

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
}

SOURCE_REQUIRED = COMMON_REQUIRED | {
    "backbone_state_tracker/app.py",
    "backbone_state_tracker/core/version.py",
    "backbone_state_tracker/tools/build_release.ps1",
    "backbone_state_tracker/tools/build_windows_exe.ps1",
    "backbone_state_tracker/tools/write_release_manifest.py",
    "backbone_state_tracker/tools/verify_release_package.py",
    "backbone_state_tracker/tools/verify_release_package.ps1",
    "backbone_state_tracker/tests/test_release_manifest.py",
    "backbone_state_tracker/tests/test_release_package_verifier.py",
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


def parse_checksum_sidecar(sidecar_path: Path) -> tuple[str | None, int | None, list[str]]:
    errors: list[str] = []
    if not sidecar_path.is_file():
        return None, None, [f"Missing checksum sidecar: {sidecar_path.name}"]

    text = sidecar_path.read_text(encoding="utf-8")
    sha_match = SHA256_LINE.search(text)
    size_match = SIZE_LINE.search(text)
    expected_sha = sha_match.group("sha256") if sha_match else None
    expected_size = int(size_match.group("size")) if size_match else None
    if expected_sha is None:
        errors.append(f"Checksum sidecar does not contain a SHA256 line: {sidecar_path.name}")
    if expected_size is None:
        errors.append(f"Checksum sidecar does not contain a Size line: {sidecar_path.name}")
    return expected_sha, expected_size, errors


def normalized_zip_names(package_path: Path) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    names: set[str] = set()
    try:
        with zipfile.ZipFile(package_path) as archive:
            for info in archive.infolist():
                names.add(info.filename.replace("\\", "/"))
    except zipfile.BadZipFile:
        errors.append(f"Not a readable ZIP file: {package_path.name}")
    return names, errors


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
    package_path = package_path.resolve()
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

    sidecar_path = package_path.with_name(f"{package_path.name}.sha256.txt")
    expected_sha, expected_size, sidecar_errors = parse_checksum_sidecar(sidecar_path)
    errors.extend(sidecar_errors)

    actual_sha = file_sha256(package_path)
    actual_size = package_path.stat().st_size
    if expected_sha is not None and actual_sha != expected_sha:
        errors.append(f"SHA256 mismatch for {package_path.name}: expected {expected_sha}, actual {actual_sha}")
    if expected_size is not None and actual_size != expected_size:
        errors.append(f"Size mismatch for {package_path.name}: expected {expected_size}, actual {actual_size}")

    names, zip_errors = normalized_zip_names(package_path)
    errors.extend(zip_errors)
    if names:
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
    elif expected_sha is not None:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        if package_path.name not in manifest_text:
            errors.append(f"Release manifest does not list package: {package_path.name}")
        if expected_sha not in manifest_text:
            errors.append(f"Release manifest does not list package SHA256: {expected_sha}")

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
