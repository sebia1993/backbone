# Changelog

## v0.3.0 - 2026-06-11

- Added Windows executable ZIP packaging with `tools/build_windows_exe.ps1`.
- Added frozen-runtime path handling so the executable uses `config/` and `outputs/` next to the EXE.
- Added `app.py --smoke-check` for source and EXE validation.
- Updated documentation to distinguish source ZIP from Windows EXE ZIP.
- Added mail/security notes for environments that block ZIP files containing scripts or executable files.

## v0.2.1 - 2026-06-11

- Added Markdown and HTML version history documents for operator-friendly release notes.
- Updated README guide links to include version history.
- Updated application version metadata to v0.2.1.

## v0.2.0 - 2026-06-11

- Added independent local Git tracking and release packaging workflow.
- Centralized application version metadata in `core/version.py`.
- Added Markdown and HTML user guide.
- Added Markdown and HTML beginner developer guide.
- Added `tools/build_release.ps1` to run validation and create a source ZIP.
- Updated GUI, snapshot metadata, and report output to display the application version.

## v0.1.0 - 2026-06-11

- Initial Backbone State Tracker implementation.
- Added read-only SSH snapshot collection for backbone devices.
- Added snapshot storage and raw command output preservation.
- Added snapshot comparison with Critical, Warning, Info, and Unchanged classification.
- Added HTML, XLSX, and JSON comparison reports.
- Added basic unit tests for snapshots and diff classification.

