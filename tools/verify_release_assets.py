from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from backbone_state_tracker.tools.verify_release_package import (
        verify_release_package,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from verify_release_package import verify_release_package


SOURCE_COMMIT_LINE = re.compile(r"^Source commit = (?P<commit>[0-9a-f]{40})$", re.MULTILINE)
LOCKED_REQUIREMENT_LINE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^\s;\\]+)"
)
APP_RELEASE_DATE_LINE = re.compile(
    r'^APP_RELEASE_DATE\s*=\s*"(?P<date>\d{4}-\d{2}-\d{2})"$',
    re.MULTILINE,
)


def normalize_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def locked_runtime_components(lock_path: Path) -> dict[str, str]:
    if not lock_path.is_file():
        raise FileNotFoundError(f"missing runtime lock: {lock_path}")
    components: dict[str, str] = {}
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        match = LOCKED_REQUIREMENT_LINE.match(line)
        if match is None:
            continue
        name = normalize_distribution_name(match.group("name"))
        version = match.group("version")
        if name in components:
            raise ValueError(f"duplicate runtime lock component: {name}")
        components[name] = version
    if not components:
        raise ValueError("runtime lock does not contain pinned components")
    return components


def release_date_stamp(release_date: str | None, version_file_path: Path) -> str:
    value = release_date
    if value is None:
        if not version_file_path.is_file():
            raise FileNotFoundError(f"missing version metadata: {version_file_path}")
        match = APP_RELEASE_DATE_LINE.search(version_file_path.read_text(encoding="utf-8"))
        if match is None:
            raise ValueError("core/version.py does not contain APP_RELEASE_DATE")
        value = match.group("date")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value.replace("-", "")
    if re.fullmatch(r"\d{8}", value):
        return value
    raise ValueError("release date must be YYYY-MM-DD or YYYYMMDD")


def verify_release_assets(
    zip_path: Path,
    checksum_path: Path,
    manifest_path: Path,
    sbom_path: Path,
    *,
    version: str,
    source_commit: str,
    runtime_lock_path: Path | None = None,
    release_date: str | None = None,
    version_file_path: Path | None = None,
) -> dict[str, object]:
    expected_tag = version if version.startswith("v") else f"v{version}"
    expected_zip = zip_path.with_name(f"backbone_state_tracker_{expected_tag}_windows.zip")
    expected_checksum = zip_path.with_name(f"{zip_path.name}.sha256.txt")
    expected_manifest = zip_path.with_name(f"backbone_state_tracker_{expected_tag}_release_manifest.txt")
    expected_sbom = zip_path.with_name(f"backbone_state_tracker_{expected_tag}_sbom.cdx.json")
    if zip_path.resolve() != expected_zip.resolve():
        raise ValueError(f"ZIP path mismatch: {zip_path.name}")
    if checksum_path.resolve() != expected_checksum.resolve():
        raise ValueError(f"checksum path mismatch: {checksum_path.name}")
    if manifest_path.resolve() != expected_manifest.resolve():
        raise ValueError(f"manifest path mismatch: {manifest_path.name}")
    if sbom_path.resolve() != expected_sbom.resolve():
        raise ValueError(f"SBOM path mismatch: {sbom_path.name}")
    for path in (zip_path, checksum_path, manifest_path, sbom_path):
        if not path.is_file():
            raise FileNotFoundError(f"missing release asset: {path}")

    project_root = Path(__file__).resolve().parents[1]
    expected_date = release_date_stamp(
        release_date,
        version_file_path or project_root / "core" / "version.py",
    )
    for label, path in (("checksum", checksum_path), ("manifest", manifest_path)):
        date_match = re.search(r"^Date stamp = (?P<date>\d{8})$", path.read_text(encoding="utf-8"), re.MULTILINE)
        if date_match is None or date_match.group("date") != expected_date:
            raise ValueError(f"{label} release date does not match APP_RELEASE_DATE {expected_date}")

    package = verify_release_package(zip_path, package_type="windows", require_manifest=True)
    if not package.ok:
        raise ValueError("; ".join(package.errors))

    manifest_text = manifest_path.read_text(encoding="utf-8")
    commit_match = SOURCE_COMMIT_LINE.search(manifest_text)
    if commit_match is None or commit_match.group("commit") != source_commit:
        raise ValueError("release manifest source commit mismatch")

    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    if not isinstance(sbom, dict):
        raise ValueError("SBOM root must be a JSON object")
    if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.6":
        raise ValueError("SBOM must be CycloneDX 1.6 JSON")
    bom_version = sbom.get("version")
    if isinstance(bom_version, bool) or not isinstance(bom_version, int) or bom_version < 1:
        raise ValueError("SBOM top-level version must be a positive integer")
    components = sbom.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("SBOM components must be a non-empty list")
    sbom_versions: dict[str, str] = {}
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("each SBOM component must be an object")
        name = component.get("name")
        component_version = component.get("version")
        component_type = component.get("type")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("each SBOM component must have a name")
        if not isinstance(component_version, str) or not component_version.strip():
            raise ValueError(f"SBOM component {name!r} must have a version")
        if component_type != "library":
            raise ValueError(f"SBOM component {name!r} must be type library")
        normalized_name = normalize_distribution_name(name)
        if normalized_name in sbom_versions:
            raise ValueError(f"duplicate SBOM component: {normalized_name}")
        sbom_versions[normalized_name] = component_version

    lock_path = runtime_lock_path or project_root / "requirements-runtime.lock"
    locked_versions = locked_runtime_components(lock_path)
    if sbom_versions != locked_versions:
        missing = sorted(set(locked_versions) - set(sbom_versions))
        unexpected = sorted(set(sbom_versions) - set(locked_versions))
        mismatched = sorted(
            name
            for name in set(sbom_versions) & set(locked_versions)
            if sbom_versions[name] != locked_versions[name]
        )
        raise ValueError(
            "SBOM component set does not match requirements-runtime.lock: "
            f"missing={missing}, unexpected={unexpected}, version_mismatch={mismatched}"
        )

    return {
        "version": expected_tag,
        "source_commit": source_commit,
        "release_date": expected_date,
        "sbom_components": len(components),
        "package_warnings": list(package.warnings),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Windows 릴리스 자산 묶음을 독립 검증합니다.")
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--checksum", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--sbom", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--release-date")
    parser.add_argument(
        "--runtime-lock",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "requirements-runtime.lock",
    )
    args = parser.parse_args(argv)
    summary = verify_release_assets(
        args.zip,
        args.checksum,
        args.manifest,
        args.sbom,
        version=args.version,
        source_commit=args.source_commit,
        runtime_lock_path=args.runtime_lock,
        release_date=args.release_date,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
