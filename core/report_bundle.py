from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .paths import resource_root, runtime_root
from .snapshot import sanitize_filename
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
    "VERSION_HISTORY.md",
    "VERSION_HISTORY.html",
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
    with ZipFile(bundle_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("README_SHARED_REPORT.txt", build_bundle_readme(report_dir))
        for path in report_files:
            archive.write(path, f"reports/{path.name}")
        if resolved_docs_dir is not None:
            for name in GUIDE_FILE_NAMES:
                path = resolved_docs_dir / name
                if path.exists():
                    archive.write(path, f"docs/{name}")
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
        "- docs/: operator, command, and version guides when available\n\n"
        "Safety notes:\n"
        "- This bundle intentionally excludes snapshot raw output folders.\n"
        "- Report files mask obvious password, secret, token, authorization, and SNMP community values.\n"
        "- Device names, IP addresses, interfaces, VLANs, and routing values are retained for operational traceability.\n"
        "- Review the files before external submission if your environment treats topology data as sensitive.\n"
    )
