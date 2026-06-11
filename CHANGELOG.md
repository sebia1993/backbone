# Changelog

## v0.8.2 - 2026-06-11

- Added standalone PowerShell release ZIP verification with `tools/verify_release_package.ps1`.
- Build scripts now copy a versioned `*_verify_release_package.ps1` helper into `dist\` for environments that only receive release ZIP files.
- Source ZIP verification now requires the PowerShell verifier script to be present in the source package.
- Updated release guides with the Python verifier and standalone PowerShell verifier options.

## v0.8.1 - 2026-06-11

- Added `tools/verify_release_package.py` to validate release ZIP checksum sidecars, manifest entries, required contents, and forbidden sensitive/build paths.
- Wired source and Windows EXE build scripts to run the package verifier after ZIP creation.
- Added regression tests for valid source packages, checksum/size mismatch detection, and blocked local `config/devices.yaml` inclusion.
- Updated release documentation with the post-transfer verification command.

## v0.8.0 - 2026-06-11

- Added SHA256 sidecar files for source and Windows EXE ZIP release packages.
- Added a version-level release manifest that lists package names, byte sizes, and SHA256 values.
- Added `PACKAGE_INFO.txt` inside each release ZIP so operators can identify package type, contents, exclusions, and verification steps after transfer.
- Ensures Windows EXE ZIP staging removes local `config/devices.yaml` if that file exists.
- Added `tools/write_release_manifest.py` and unit tests for release checksum and manifest generation.
- Updated release scripts and documentation for offline/internal transfer verification.

## v0.7.9 - 2026-06-11

- Added a local preflight configuration check before collection.
- Validates enabled devices, duplicate device names, host/port values, command IDs, check commands, and likely write/destructive command patterns.
- Adds a `설정 점검` button and status summary on the collection screen.
- Blocks collection when preflight errors are found, while allowing warning-only results.
- Added unit tests for valid configs, duplicate names, dangerous commands, documentation IP warnings, and duplicate command IDs.

## v0.7.8 - 2026-06-11

- Added severity filtering and free-text search to the GUI comparison detail list.
- Search covers device, command, category, judgment, line location, and before/after changed values.
- Keeps search on redacted display values so masked secrets are not exposed through filtering.
- Added visible filtered-row counts and a filter reset action.
- Added GUI formatting tests for severity filtering, multi-term search, and redacted search behavior.

## v0.7.7 - 2026-06-11

- Added an automatically generated shared report ZIP for each snapshot comparison.
- The shared ZIP includes redacted report files and operator/version guides, while excluding snapshot raw output folders.
- Added dashboard and comparison-screen buttons to open the latest shared ZIP.
- Extended offline sample validation so sample comparisons also produce shared ZIP bundles.
- Added regression tests for shared ZIP contents and excluded raw/device/executable files.

## v0.7.6 - 2026-06-11

- Added shared sensitive-string redaction for GUI logs, snapshot metadata, and comparison report exports.
- Masks common password, secret, token, authorization header, URL credential, Cisco typed secret, and SNMP community string patterns.
- Preserves per-command raw output files for operational evidence while redacting human-facing report artifacts.
- Added regression tests for redaction helpers, connection error sanitizing, and report output masking.

## v0.7.5 - 2026-06-11

- Added offline sample validation generation from the dashboard and comparison screens.
- Creates `[샘플] 작업 전`, `[샘플] 백본3 OFF 중`, and `[샘플] 복구 후` snapshots without using SSH or credentials.
- Generates comparison reports for pre-work vs BB3 OFF, pre-work vs restored, and BB3 OFF vs restored scenarios.
- Added tests that verify sample snapshots, reports, unreachable-device Critical items, and restored-device Info items.

## v0.7.4 - 2026-06-11

- Improved the GUI comparison detail list with an operational impact column and compact `base → target` line location display.
- Added severity-colored comparison rows so Critical, Warning, Info, and Unchanged results are easier to scan.
- Redesigned the selected change detail panel to lead with core judgment, exact before/after values, raw file pointers, and severity-specific follow-up guidance.
- Added GUI formatting tests for inline line mapping and selected change detail content.

## v0.7.3 - 2026-06-11

- Added unique snapshot folder allocation when the same stage is collected more than once in the same second.
- Preserves the original timestamped folder name for the first snapshot and appends `_001`, `_002`, and later suffixes only when needed.
- Added a regression test to verify same-label same-second snapshots do not overwrite or merge previous outputs.
- Updated source and Windows EXE release documents for the v0.7.3 package.

## v0.7.2 - 2026-06-11

- Added per-device `device_connectivity` snapshot records for SSH connection success and failure.
- Reports unreachable devices as a single Critical comparison item instead of many missing command rows.
- Suppresses normal command added/removed noise when one side of the comparison is unreachable.
- Preserves compatibility with older snapshots by inferring connectivity from existing command results or legacy connection failures.
- Added tests for device unreachable, device restored, and still-unreachable comparison scenarios.

## v0.7.1 - 2026-06-11

- Redesigned HTML comparison detail rows into a compact inline format: change type, line mapping, and `before → after` content.
- Added colored inline value chips for changed, added, and removed lines.
- Added horizontal scrolling for long command output lines in HTML reports.
- Preserved raw unified diff, XLSX `diff_detail`, JSON manifest, GUI behavior, and collection workflow.
- Updated tests and release documents for the HTML readability patch.

## v0.7.0 - 2026-06-11

- Added a dashboard workflow wizard for the maintenance sequence.
- Added step cards for device setup, pre-work collection, BB3 OFF collection, OFF review, restore collection, and final review.
- Added a single next-step action button that advances only after the operator confirms the previous result.
- Locked restore collection in the wizard until the BB3 OFF comparison review is opened.
- Preserved the existing left navigation, manual collection, manual comparison, and report behavior.
- Added workflow wizard unit tests.

## v0.6.0 - 2026-06-11

- Added structured line-level diff details for snapshot comparisons.
- Added before/after changed line display to the GUI comparison screen.
- Added `change_count`, `change_preview`, and `changed_lines` to comparison manifest data.
- Updated HTML reports with a changed-line detail table and collapsible raw unified diff.
- Added `diff_detail` worksheet to XLSX reports for device, command, line number, before value, and after value tracking.
- Added tests for changed, added, removed, HTML, and XLSX line-level comparison output.

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
