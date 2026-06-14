# Changelog

## v0.8.52 - 2026-06-15

- Applied a calmer AirWave-inspired common console theme to the Tkinter GUI, including the sidebar, buttons, form controls, section headers, Treeview tables, and log/detail panels.
- Updated generated HTML comparison report CSS to use the same neutral surface, Aruba teal accent, compact cards, and readable table treatment.
- No collection, SSH, comparison, or severity-classification behavior changed.

## v0.8.51 - 2026-06-15

- Added developer guide and release checklist MD/HTML documents to shared report ZIP bundles.
- Added regression coverage for the full shared-report guide set and all GUI Help menu document targets.
- No collection, SSH, comparison, or severity-classification behavior changed.

## v0.8.50 - 2026-06-15

- Added documentation regression coverage that rejects common mojibake fragments and Unicode replacement characters in release guides.
- Added checks that Korean user/developer guides keep the core workflow terms `장비 설정`, `비교 결과`, `작업 로그`, `긴급`, `주의`, `정보`, and `변경없음`.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.49 - 2026-06-15

- Strengthened Python and PowerShell release package verification to reject `.venv`, `venv`, and `.pytest_cache` entries.
- Added regression coverage for forbidden runtime output, raw output, build, dist, virtual environment, and test cache folders in release ZIPs.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.48 - 2026-06-15

- Added Windows EXE ZIP fixture coverage for the release package verifier.
- Added regression tests so missing `BackboneStateTracker.exe` or `RUN_FIRST.txt` fails Windows EXE ZIP verification.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.47 - 2026-06-15

- Added regression coverage that keeps packaged shareable `config/*` files aligned with the real project config files while excluding local `config/devices.yaml`.
- Added missing-package coverage for `config/commands.yaml` so release ZIPs cannot omit the bundled read-only command set.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.46 - 2026-06-15

- Added regression coverage that keeps release package documentation entries aligned with the real `docs/*.md`, `docs/*.html`, and `docs/images/*` files.
- Added missing-package coverage for user-guide screenshots so release ZIPs cannot omit visual guide assets.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.45 - 2026-06-15

- Added regression coverage that keeps the source ZIP verifier's required release tool script list aligned with the real `tools/*.py` and `tools/*.ps1` files.
- Added missing-package coverage for release build scripts so source ZIPs cannot omit the scripts needed for internal rebuild and verification.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.44 - 2026-06-15

- Strengthened source ZIP verification so every current `core/*.py` runtime module, package initializer, and `requirements.txt` must be included.
- Added regression coverage that keeps the verifier's required core module lists aligned with the real `core/*.py` files.
- Added missing-package tests for runtime core modules and dependency requirements.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.43 - 2026-06-15

- Added regression coverage that compares the real `tests/test_*.py` files with the source ZIP verifier's Python, PowerShell, and test-fixture required lists.
- Guarded future test additions from being missed by release package verification.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.42 - 2026-06-14

- Strengthened source ZIP verification so every current regression test file must be included in the release package.
- Kept the Python and PowerShell release package verifiers aligned for internal transfer checks.
- Added regression coverage for missing runtime test files in source release ZIPs.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.41 - 2026-06-14

- Improved generated HTML comparison report change-detail rows with visible cell labels for type, line, and change content.
- Added regression coverage for changed, added, and removed HTML detail rows so each row remains understandable even when viewed in isolation.
- No collection, SSH, or comparison severity logic changed.

## v0.8.40 - 2026-06-14

- Added regression coverage that loads the real bundled `config/commands.yaml` and verifies every configured command passes preflight without errors or warnings.
- Strengthened the read-only command safety guard so future command additions must remain within the approved display/show/session command set.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.39 - 2026-06-14

- Added regression coverage that checks the current app version is reflected in README, CHANGELOG, and every release guide MD/HTML document.
- Verified release artifact examples in the operator and release checklist documents stay aligned with the current version.
- No collection, SSH, comparison, or report runtime behavior changed.

## v0.8.38 - 2026-06-14

- Added parser-based regression coverage for generated HTML report filter regions.
- Verified status cards, status shortcut buttons, summary sections, unchanged summaries, and detail blocks expose structured `data-*`, `hidden`, and `aria-hidden` attributes.
- No collection, SSH, or report runtime behavior changed.

## v0.8.37 - 2026-06-14

- Kept the generated HTML report's `Unchanged` summary group collapsed after selecting the `변경없음` status card.
- Preserved manual expand behavior and `상세 보기` navigation for unchanged detail blocks.
- Updated reporter regression coverage for the collapsed unchanged-summary behavior.

## v0.8.36 - 2026-06-14

- Synchronized `docs/COMMAND_GUIDE.html` with the full command list in `config/commands.yaml` and `docs/COMMAND_GUIDE.md`.
- Added documentation regression coverage so the command guide MD/HTML command IDs stay aligned with the bundled command config.
- No collection, SSH, or diff-classification behavior changed.

## v0.8.35 - 2026-06-14

- Added `vrrp_status` with the read-only `show vrrp` command to collect VRRP master/backup and virtual router state.
- Documented the VRRP command in the command guide and release/version history.
- Added regression coverage for VRRP config loading, preflight safety, and routing comparison severity.

## v0.8.33 - 2026-06-12

- Changed `cpu_usage` and `memory_usage` classification so numeric snapshot differences do not create resource warnings by themselves.
- Classified normal CPU usage below 50% and memory FreeRatio above 40% as Info, even when the compared output is unchanged.
- Kept Critical and Warning threshold behavior for CPU and memory based on the target snapshot's current value.
- Added regression coverage for normal-range CPU/memory values and unparsed CPU/memory output changes.

## v0.8.32 - 2026-06-12

- Fixed generated HTML report filtering so selected severity views hide non-selected shortcut, summary, and detail items reliably.
- Added a strong `[hidden]` CSS rule to prevent component display styles from overriding hidden state.
- Synchronized `hidden` and `aria-hidden` attributes when HTML severity filters change.
- Updated reporter regression coverage and release documents for v0.8.32.

## v0.8.31 - 2026-06-12

- Changed the HTML report default view so status shortcuts, summary cards, and detail blocks stay hidden until an operator selects a severity card.
- Updated severity card filtering so only the selected `긴급`, `주의`, `정보`, or `변경없음` items appear.
- Kept jump buttons scoped to the selected status and preserved direct navigation to the matching device/command detail block.
- Updated reporter regression coverage and release documents for v0.8.31.

## v0.8.30 - 2026-06-12

- Added `cpu_usage` threshold checks for parsed 5 seconds, 1 minute, and 5 minutes values.
- Marked CPU usage of 70% or higher as Critical and 50% through 69% as Warning.
- Applied CPU checks to the current target snapshot value even when the compared output did not change.
- Added diff-engine regression coverage for CPU boundary values, label variants, critical priority, and value-before-label parsing.
- Updated README, operator, command, developer, release checklist, and version history documents for v0.8.30.

## v0.8.29 - 2026-06-12

- Added `memory_usage` FreeRatio threshold checks: 30% or lower is Critical, and 31% through 40% is Warning.
- Added `power_status` State checks so any parsed State value other than Normal is Critical.
- Applied these checks to the current target snapshot value even when the compared output did not change.
- Added diff-engine regression coverage for FreeRatio boundaries, table parsing, non-normal power states, and unchanged-but-risky outputs.
- Updated README, operator, command, developer, release checklist, and version history documents for v0.8.29.

## v0.8.28 - 2026-06-12

- Replaced the HTML report `변경 항목 바로가기` section with `상태별 바로가기` buttons for Critical, Warning, Info, and Unchanged items.
- Made HTML status cards filter the shortcut buttons, summary cards, and detail blocks together.
- Kept the default HTML report view focused on Critical and Warning; Info and Unchanged stay hidden until their status card is selected.
- Added reporter regression coverage for all-severity status shortcuts and hidden-by-default Info/Unchanged behavior.
- Updated README, operator, command, developer, release checklist, and version history documents for v0.8.28.

## v0.8.27 - 2026-06-12

- Blocked `설정 점검` while collection, comparison, or sample validation work is already running.
- Disabled the preflight and snapshot refresh buttons during busy workflows to reduce accidental overlapping actions.
- Added GUI regression coverage for the preflight busy guard and busy-state button locking.
- Updated README, operator, command, developer, release checklist, and version history documents for v0.8.27.

## v0.8.26 - 2026-06-12

- Made the `장비 설정` screen vertically scrollable so added target device rows do not push collection controls out of reach.
- Added a live target device summary showing enabled, configured, and total input row counts.
- Added GUI regression coverage for the scrollable settings page and dynamic device summary updates.
- Updated README, operator, command, developer, release checklist, and version history documents for v0.8.26.

## v0.8.25 - 2026-06-12

- Added a `장비 추가` button to the target device settings section so operators can add more device rows when needed.
- Expanded device YAML loading so three or more configured devices are shown in the GUI instead of being truncated to the first two rows.
- Cleared stale extra rows when a shorter device list is loaded and kept blank rows out of collection/save targets.
- Added GUI regression coverage for dynamic target device rows and shorter-list reload behavior.
- Updated README, operator, developer, release checklist, and version history documents for v0.8.25.

## v0.8.24 - 2026-06-12

- Added `변경 항목 바로가기` buttons to HTML comparison reports for changed Critical, Warning, and Info items only.
- Each jump button shows severity, device name, command ID, and change count, then moves directly to the matching command detail block.
- Added JavaScript focus highlighting so the destination block is easier to identify after jumping.
- Added reporter regression coverage for changed-item jump buttons and the no-change fallback state.
- Updated README, operator, developer, release checklist, and version history documents for v0.8.24.

## v0.8.23 - 2026-06-12

- Collapsed `변경없음` summary cards in HTML comparison reports by default, not only the lower detail blocks.
- Opened the collapsed `변경없음` summary section automatically when the `변경없음` severity filter or matching detail links are used.
- Added reporter regression coverage for collapsed unchanged summary sections.
- Updated README, operator, developer, release checklist, and version history documents for v0.8.23.

## v0.8.22 - 2026-06-12

- Labeled sample snapshots as `샘플:` in the HTML comparison report header metadata so shared sample validation reports are easier to distinguish from real maintenance evidence.
- Added reporter regression coverage for sample snapshot display names in generated HTML.
- Updated README, operator, developer, release checklist, and version history documents for v0.8.22.

## v0.8.21 - 2026-06-12

- Labeled sample snapshots as `샘플:` in the top runtime summary so sample validation comparisons are easier to distinguish from real maintenance baselines.
- Added GUI regression coverage for sample snapshot display names.
- Updated README, operator, developer, release checklist, and version history documents for v0.8.21.

## v0.8.20 - 2026-06-12

- Prevented sample validation snapshots such as `sample_pre_work` from being selected as real pre-work baselines.
- Kept first real collection in `작업 전` mode even when only sample validation snapshots already exist.
- Added workflow and GUI regression tests for sample baseline exclusion.
- Updated README, operator, developer, release checklist, and version history documents for v0.8.20.

## v0.8.19 - 2026-06-12

- Improved HTML comparison report filtering so the severity summary cards remain visible while details are filtered.
- Updated summary-card `상세 보기` links to reveal the matching detail block even when another severity filter is active.
- Switched the generated HTML report font stack to prefer `Malgun Gothic` for Korean readability.
- Added regression coverage for the HTML severity-filter behavior.
- Updated README, operator, developer, release checklist, and version history documents for v0.8.19.

## v0.8.18 - 2026-06-12

- Integrated status collection into the `장비 설정` screen and removed the separate collection menu and workflow wizard.
- Replaced collection-stage selection controls with one optional custom stage-name field. Empty input is saved as `점검시간_YYYYMMDD_HHMM`.
- Made first collection become the baseline snapshot and later collections auto-compare against the latest baseline.
- Added clickable severity summary cards in the GUI and HTML report for `긴급`, `주의`, `정보`, and `변경없음`.
- Collapsed unchanged HTML detail blocks by default.
- Reworked Critical/Warning criteria for connectivity failures, LACP selected-count decreases, major/minor alarms, and operational state changes.
- Added actual app screenshots to the user guide and included `docs/images/` in shared/report release packaging.
- Updated README, operator, command, developer, release checklist, and version history documents for v0.8.18.

## v0.8.17 - 2026-06-12

- Reordered the GUI workflow so the app opens on `장비 설정` and the left navigation follows `장비 설정 → 상태 수집 → 비교 결과 → 작업 로그`.
- Added a `상태 수집으로 이동` button on the settings page so operators can move directly to collection after confirming credentials and device targets.
- Updated GUI regression tests for the settings-first startup flow and workflow navigation order.
- Updated README, operator, developer, release checklist, command, and version history documents for v0.8.17.

## v0.8.16 - 2026-06-12

- Changed the HTML comparison report summary from a wide table to labeled summary cards so each value remains understandable when viewed by itself.
- Reduced the GUI comparison metrics from a large standalone section to a compact summary bar above recent change details.
- Simplified status collection stage input to a single custom stage name field, with empty values saved as `점검시간_YYYYMMDD_HHMM`.
- Improved Help menu document lookup so packaged EXE runs can open user, command, and version-history guides from runtime or bundled docs.
- Added regression tests for the new report summary, comparison layout, stage-label defaults, and document lookup.

## v0.8.15 - 2026-06-12

- Removed the dashboard from the main navigation and made status collection the first screen.
- Moved the workflow wizard into the status collection screen.
- Automatically switches to the work log when collection starts, is blocked by a busy workflow, or fails input/preflight validation.
- Added GUI regression tests for the no-dashboard navigation and log-first collection flow.
- Updated README, operator, developer, release checklist, command, and version history documents for v0.8.15.

## v0.8.14 - 2026-06-12

- Added `Date stamp` to checksum sidecar files so sidecars carry the same release date identity as ZIP filenames and manifests.
- Extended Python and PowerShell release package verification to reject sidecar date mismatches.
- Added regression tests for sidecar date output and date mismatch detection.
- Updated README, operator, developer, release checklist, command, and version history documents for v0.8.14.
- No runtime collection, comparison, report, or GUI workflow behavior changed.

## v0.8.13 - 2026-06-12

- Extended Python and PowerShell release package verification to reject duplicate package records inside `release_manifest.txt`.
- Added a regression test for duplicate release manifest `Package` records.
- Updated README, operator, developer, release checklist, command, and version history documents for v0.8.13.
- No runtime collection, comparison, report, or GUI workflow behavior changed.

## v0.8.12 - 2026-06-12

- Extended Python and PowerShell release package verification to reject duplicate normalized ZIP entries.
- Added a regression test that creates a real duplicate ZIP member and verifies the `Duplicate ZIP entry found` failure.
- Updated README, operator, developer, release checklist, command, and version history documents for v0.8.12.
- No runtime collection, comparison, report, or GUI workflow behavior changed.

## v0.8.11 - 2026-06-12

- Extended Python and PowerShell release package verification to reject unsafe ZIP entries, including absolute paths, Windows drive paths, empty path segments, and `..` traversal segments.
- Added a release package root check so ZIP contents must stay under `backbone_state_tracker/`.
- Added regression tests for unexpected top-level ZIP entries, traversal entries, and absolute ZIP entries.
- Updated README, operator, developer, release checklist, command, and version history documents for v0.8.11.
- No runtime collection, comparison, report, or GUI workflow behavior changed.

## v0.8.10 - 2026-06-12

- Extended Python and PowerShell release package verification to check that the checksum sidecar `SHA256 (...)` package name matches the ZIP filename.
- Replaced loose release manifest package/SHA checks with package-record checks for the selected ZIP's exact `Package`, `Size`, and `SHA256` values.
- Added regression tests for sidecar package-name mismatch, manifest package-record SHA mismatch, and manifest package-record size mismatch.
- Updated README, operator, developer, release checklist, command, and version history documents for v0.8.10.
- No runtime collection, comparison, report, or GUI workflow behavior changed.

## v0.8.9 - 2026-06-12

- Extended Python and PowerShell release package verification to compare the ZIP filename version with the checksum sidecar `Version` line.
- Extended release manifest verification to compare manifest `Version` and `Date stamp` values with the ZIP filename version and date.
- Added regression tests for sidecar version mismatch, manifest version mismatch, and manifest date mismatch.
- Updated README, operator, developer, release checklist, command, and version history documents for v0.8.9.
- No runtime collection, comparison, report, or GUI workflow behavior changed.

## v0.8.8 - 2026-06-12

- Added `docs/RELEASE_CHECKLIST.md` and `docs/RELEASE_CHECKLIST.html` for Korean internal-transfer and release verification handoff.
- Promoted the release checklist to a required source and Windows EXE ZIP document in both Python and PowerShell package verifiers.
- Added a verifier regression test so packages missing the release checklist fail before handoff.
- Updated README, operator, developer, command, and version history documents for the new release checklist and v0.8.8 package names.
- No runtime collection, comparison, report, or GUI workflow behavior changed.

## v0.8.7 - 2026-06-11

- Replaced hardcoded local developer paths in README and beginner developer guide with portable `<folder-that-contains-backbone_state_tracker>` examples.
- Documented that local workspace paths should not be written into operator/developer guides.
- Updated release manifest and package verifier tools so build output keeps the invoked workspace path instead of resolving junctions to a developer-only canonical path.
- Added a documentation regression test to block developer-specific absolute workspace paths from README and packaged guides.
- No runtime collection, comparison, or report behavior changed.

## v0.8.6 - 2026-06-11

- Added comparison-detail actions to open the selected row's base raw output and target raw output directly from the GUI.
- Added a button to copy the selected comparison detail text to the clipboard using the existing redacted display text.
- Added a regression test for resolving selected raw output paths from the comparison summary.
- Updated operator, developer, and version history guides for the new evidence-tracing buttons.

## v0.8.5 - 2026-06-11

- Added a Help menu entry that opens the Korean command guide directly from the app.
- Added a command guide button on the status collection screen next to the command-set summary.
- Updated operator, developer, and version history guides to document the in-app command guide access path.
- No device collection commands, comparison logic, or report formats were changed.

## v0.8.4 - 2026-06-11

- Added `docs/COMMAND_GUIDE.md` and `docs/COMMAND_GUIDE.html` with Korean explanations for each bundled HPE/Comware read-only check command.
- Documented normal criteria and follow-up points for hardware, interface, LACP, VLAN, STP, OSPF, resource, and log checks.
- Added the command guide files to Python and PowerShell release package verification requirements.
- Updated user, developer, and version history guides to reference the command guide.

## v0.8.3 - 2026-06-11

- Added an operation busy guard so collection, manual comparison, and sample validation cannot be started again while a collection or comparison is already running.
- Disabled collection/comparison/sample action buttons during active operations to reduce accidental duplicate SSH sessions and duplicate reports.
- Build scripts now refresh `dist\latest\` and `dist\CURRENT_RELEASE.txt` so operators can identify the latest transfer-ready release files when older ZIPs remain in `dist\`.
- Added a GUI regression test for the busy guard.

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
