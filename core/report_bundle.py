from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .paths import resource_root, runtime_root
from .snapshot import atomic_replace_file, sanitize_filename
from .version import APP_NAME, APP_VERSION


REPORT_FILE_NAMES = (
    "diff_report.html",
    "diff_summary.xlsx",
    "diff_summary.csv",
    "diff_manifest.json",
)
GUIDE_FILE_NAMES = (
    "USER_GUIDE.md",
    "USER_GUIDE.html",
    "COMMAND_GUIDE.md",
    "COMMAND_GUIDE.html",
    "DEVELOPER_GUIDE_BEGINNER.md",
    "DEVELOPER_GUIDE_BEGINNER.html",
    "VERSION_HISTORY.md",
    "VERSION_HISTORY.html",
    "RELEASE_CHECKLIST.md",
    "RELEASE_CHECKLIST.html",
    "DIAGNOSTIC_MODE_GUIDE.md",
    "DIAGNOSTIC_MODE_GUIDE.html",
    "ERROR_CODE_CATALOG.md",
    "ERROR_CODE_CATALOG.html",
)


def create_share_report_bundle(
    report_dir: Path,
    docs_dir: Path | None = None,
    created_at: datetime | None = None,
) -> Path:
    report_dir = Path(report_dir)
    if not report_dir.exists():
        raise FileNotFoundError(f"Report directory does not exist: {report_dir}")

    stamp = (created_at or datetime.now()).strftime("%Y%m%d_%H%M%S")
    bundle_name = f"{sanitize_filename(report_dir.name, 'comparison')}_share_v{APP_VERSION}_{stamp}.zip"
    bundle_path = report_dir / bundle_name

    report_files = [report_dir / name for name in REPORT_FILE_NAMES if (report_dir / name).exists()]
    if not report_files:
        raise FileNotFoundError(f"No comparison report files found in: {report_dir}")

    resolved_docs_dir = docs_dir or resolve_docs_dir()
    fd, temp_name = tempfile.mkstemp(prefix=f".{bundle_path.name}.", suffix=".tmp", dir=report_dir)
    os.close(fd)
    temp_bundle_path = Path(temp_name)
    try:
        with ZipFile(temp_bundle_path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("README_SHARED_REPORT.txt", build_bundle_readme(report_dir))
            for path in report_files:
                archive.write(path, f"reports/{path.name}")
            if resolved_docs_dir is not None:
                for name in GUIDE_FILE_NAMES:
                    path = resolved_docs_dir / name
                    if path.exists():
                        archive.write(path, f"docs/{name}")
                images_dir = resolved_docs_dir / "images"
                if images_dir.exists():
                    for path in sorted(images_dir.rglob("*")):
                        if path.is_file():
                            archive.write(path, f"docs/images/{path.relative_to(images_dir).as_posix()}")
        atomic_replace_file(temp_bundle_path, bundle_path)
    except Exception:
        try:
            temp_bundle_path.unlink()
        except OSError:
            pass
        raise
    return bundle_path


def resolve_docs_dir() -> Path | None:
    candidates = [
        runtime_root() / "docs",
        resource_root() / "docs",
        Path(__file__).resolve().parents[1] / "docs",
    ]
    for candidate in candidates:
        if (candidate / "USER_GUIDE.md").exists():
            return candidate
    return None


def build_bundle_readme(report_dir: Path) -> str:
    return (
        f"{APP_NAME} v{APP_VERSION} shared report bundle\n"
        f"Generated from: {report_dir.name}\n\n"
        "Contents:\n"
        "- reports/: redacted HTML/XLSX/CSV/JSON comparison outputs when available\n"
        "- docs/: operator, command, developer, diagnostic, error-code, version, and release checklist guides when available\n\n"
        "Safety notes:\n"
        "- This bundle intentionally excludes snapshot raw output folders.\n"
        "- Report files mask obvious password, secret, token, authorization, and SNMP community values.\n"
        "- Device names, IP addresses, interfaces, VLANs, and routing values are retained for operational traceability.\n"
        "- Review the files before external submission if your environment treats topology data as sensitive.\n"
    )
