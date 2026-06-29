from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
from pathlib import Path
from typing import Iterable


CHUNK_SIZE = 1024 * 1024
PACKAGE_IDENTITY = re.compile(r"^.+_v\d+\.\d+\.\d+_(?P<date>\d{8})_(source|windows_exe)\.zip$")


def _version_label(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


def _now_text() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_record(path: Path) -> dict[str, str | int]:
    package = Path(path)
    return {
        "name": package.name,
        "size_bytes": package.stat().st_size,
        "sha256": file_sha256(package),
    }


def package_date_stamp(path: Path) -> str | None:
    match = PACKAGE_IDENTITY.match(Path(path).name)
    if not match:
        return None
    return match.group("date")


def write_package_checksum(
    package_path: Path,
    version: str,
    generated_at: str | None = None,
) -> Path:
    package_path = Path(package_path)
    if not package_path.is_file():
        raise FileNotFoundError(f"Package does not exist: {package_path}")

    record = package_record(package_path)
    sidecar_path = package_path.with_name(f"{package_path.name}.sha256.txt")
    lines = [
        f"SHA256 ({record['name']}) = {record['sha256']}",
        f"Size = {record['size_bytes']} bytes",
        f"Version = {_version_label(version)}",
        f"Date stamp = {package_date_stamp(package_path) or 'unknown'}",
        f"Generated = {generated_at or _now_text()}",
        "",
        "PowerShell 검증:",
        f"Get-FileHash -Algorithm SHA256 .\\{record['name']}",
        "",
    ]
    sidecar_path.write_text("\n".join(lines), encoding="utf-8")
    return sidecar_path


def find_release_packages(project_name: str, version: str, date_stamp: str, dist_dir: Path) -> list[Path]:
    prefix = f"{project_name}_{_version_label(version)}_{date_stamp}_"
    return sorted(path for path in dist_dir.glob(f"{prefix}*.zip") if path.is_file())


def write_release_manifest(
    project_name: str,
    version: str,
    date_stamp: str,
    dist_dir: Path,
    package_paths: Iterable[Path] | None = None,
    generated_at: str | None = None,
) -> Path:
    dist_dir = Path(dist_dir)
    if package_paths is None:
        packages = find_release_packages(project_name, version, date_stamp, dist_dir)
    else:
        packages = sorted(Path(path) for path in package_paths)

    missing = [str(path) for path in packages if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing package files: " + ", ".join(missing))

    manifest_name = f"{project_name}_{_version_label(version)}_{date_stamp}_release_manifest.txt"
    manifest_path = dist_dir / manifest_name
    generated = generated_at or _now_text()

    lines = [
        "백본 상태 추적기 릴리스 매니페스트",
        f"Project = {project_name}",
        f"Version = {_version_label(version)}",
        f"Date stamp = {date_stamp}",
        f"Generated = {generated}",
        "",
        "Packages",
    ]
    if not packages:
        lines.append("- 패키지 ZIP 파일을 찾지 못했습니다.")
    for package in packages:
        record = package_record(package)
        lines.extend(
            [
                f"- Package: {record['name']}",
                f"  Size: {record['size_bytes']} bytes",
                f"  SHA256: {record['sha256']}",
            ]
        )

    lines.extend(
        [
            "",
            "검증 방법",
            "1. 각 ZIP 파일과 같은 이름의 .sha256.txt 파일을 함께 보관하세요.",
            "2. 파일을 옮긴 뒤 ZIP에 대해 Get-FileHash -Algorithm SHA256을 실행하세요.",
            "3. 계산된 해시를 이 매니페스트 또는 sidecar 파일의 값과 비교하세요.",
            "",
        ]
    )
    manifest_path.write_text("\n".join(lines), encoding="utf-8")
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SHA256 sidecar와 릴리스 매니페스트 파일을 생성합니다.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--date-stamp", required=True)
    parser.add_argument("--dist-dir", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args(argv)

    checksum_path = write_package_checksum(args.package, args.version)
    manifest_path = write_release_manifest(
        args.project_name,
        args.version,
        args.date_stamp,
        args.dist_dir,
    )
    print(f"Checksum 파일: {checksum_path}")
    print(f"릴리스 매니페스트: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
