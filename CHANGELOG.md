# Changelog

## v0.5.0 - 2026-06-11

- Redesigned the GUI into a bright Korean operations console inspired by HPE/Aruba-style network dashboards.
- Added left navigation for dashboard, status collection, comparison results, device settings, and logs.
- Added top status summary, dashboard metric cards, recent snapshot/report indicators, and clearer comparison state labels.
- Preserved the existing read-only collection, automatic comparison, report generation, and Korean workflow behavior.
- Updated README, user guide, beginner developer guide, and version history in Markdown and HTML.

## v0.4.0 - 2026-06-11

- Redesigned the GUI as a Korean three-step workflow.
- Added work-stage snapshot names: `작업 전`, `백본3 OFF 중`, `복구 후`, and `사용자 지정`.
- Added automatic comparison against the latest `작업 전` snapshot after non-baseline collection.
- Added Korean GUI labels, menu bar, log messages, and comparison report labels.
- Added workflow unit tests for stage resolution and baseline snapshot selection.

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
