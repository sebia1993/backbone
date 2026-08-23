from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path

REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
APPLICATION_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
RELEASE_TAG = re.compile(r"^v\d+\.\d+\.\d+(?:-rc\.\d+)?$")
SOURCE_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def expected_sbom_serial_number(
    repository: str,
    application: str,
    version: str,
    source_commit: str,
) -> str:
    """Return a deterministic RFC 4122 UUIDv5 URN for one release source identity."""

    normalized_repository = repository.strip().lower()
    normalized_application = application.strip().lower()
    normalized_version = version.strip()
    if not normalized_version.startswith("v"):
        normalized_version = f"v{normalized_version}"
    normalized_commit = source_commit.strip().lower()
    if REPOSITORY_NAME.fullmatch(normalized_repository) is None:
        raise ValueError("repository must be an owner/name pair")
    if APPLICATION_NAME.fullmatch(normalized_application) is None:
        raise ValueError("application must be a simple identifier")
    if RELEASE_TAG.fullmatch(normalized_version) is None:
        raise ValueError("version must be a SemVer release tag")
    if SOURCE_COMMIT.fullmatch(normalized_commit) is None:
        raise ValueError("source commit must be a 40-character SHA-1")

    release_identity = (
        f"https://github.com/{normalized_repository}/applications/{normalized_application}"
        f"/releases/tag/{normalized_version}"
        f"?source-commit={normalized_commit}"
    )
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, release_identity)}"


def is_rfc4122_uuid5_urn(value: object) -> bool:
    if not isinstance(value, str) or not value.lower().startswith("urn:uuid:"):
        return False
    try:
        parsed = uuid.UUID(value[len("urn:uuid:") :])
    except ValueError:
        return False
    return (
        parsed.version == 5
        and parsed.variant == uuid.RFC_4122
        and value.lower() == f"urn:uuid:{parsed}"
    )


def stamp_sbom_identity(
    sbom_path: Path,
    *,
    repository: str,
    application: str,
    version: str,
    source_commit: str,
) -> str:
    """Add the expected deterministic serialNumber to a reproducible CycloneDX JSON file."""

    path = Path(sbom_path)
    if not path.is_file():
        raise FileNotFoundError(f"missing SBOM: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("SBOM root must be a JSON object")
    if payload.get("bomFormat") != "CycloneDX" or payload.get("specVersion") != "1.6":
        raise ValueError("SBOM must be CycloneDX 1.6 JSON")

    expected = expected_sbom_serial_number(repository, application, version, source_commit)
    existing = payload.get("serialNumber")
    if existing is not None and existing != expected:
        raise ValueError("SBOM already contains a different serialNumber")
    payload["serialNumber"] = expected
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CycloneDX SBOM에 결정적 릴리스 식별자를 기록합니다.")
    parser.add_argument("--sbom", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--application", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    serial_number = stamp_sbom_identity(
        args.sbom,
        repository=args.repository,
        application=args.application,
        version=args.version,
        source_commit=args.source_commit,
    )
    print(f"serialNumber={serial_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
