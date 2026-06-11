# Backbone State Tracker

Version: `v0.8.0`

Windows GUI utility for collecting read-only status snapshots from backbone 3
and 4, then comparing snapshots to track operational changes during maintenance.

## What It Does

- Connects to backbone devices over SSH.
- Runs read-only display/check commands from `config/commands.yaml`.
- Runs a local preflight check for device and command configuration before collection.
- Saves command outputs as timestamped snapshots.
- Keeps repeated snapshots separate even when the same stage is collected twice in the same second.
- Compares snapshots by device and command.
- Tracks per-device connectivity so an unreachable backbone is reported as a single Critical comparison item.
- Generates offline sample validation snapshots and reports without connecting to real devices.
- Masks obvious secret strings in GUI logs, snapshot metadata, and comparison reports while preserving per-command raw output files.
- Automatically compares `백본3 OFF 중`, `복구 후`, and custom snapshots against the latest `작업 전` snapshot.
- Writes HTML, XLSX, and JSON comparison reports.
- Creates a shared report ZIP with redacted reports and guides, excluding snapshot raw output folders.
- Writes SHA256 checksum sidecars, a release manifest, and `PACKAGE_INFO.txt` for source and Windows EXE release ZIP verification.
- Provides a Korean bright-console UI with left navigation, dashboard metrics, collection, compare, settings, and log screens.
- Shows line-level snapshot differences so operators can see the exact before/after output that changed.
- Filters and searches GUI comparison detail rows by severity, device, command, judgment, line, and changed values.
- Highlights GUI comparison rows with impact, line location, before/after values, and severity-specific follow-up guidance.
- Shows HTML comparison details in one-line inline form, such as `old value → new value`, with horizontal scrolling for long command output.
- Guides the operator through a dashboard workflow wizard: device check, pre-work collection, BB3 OFF collection, OFF review, restore collection, and final review.

## Quick Start

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
python -m pip install -r requirements.txt
python app.py
```

Use the GUI to enter backbone 3/4 device IPs, SSH username, password, and the
maintenance stage. Passwords are never saved to configuration or report files.

## Important Files

- `config/devices.example.yaml`: sample device definitions.
- `config/commands.yaml`: read-only command set.
- `outputs/snapshots/`: generated snapshot and comparison outputs.
- `docs/USER_GUIDE.md`: operator guide.
- `docs/DEVELOPER_GUIDE_BEGINNER.md`: beginner developer guide.
- `docs/VERSION_HISTORY.md`: version-by-version change history.

## Test

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
python app.py --smoke-check
```

## Source ZIP

Source ZIP only. This does not include a Windows `.exe`.

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

The generated ZIP is written to `dist\`. It excludes `.git`, runtime outputs,
local `config\devices.yaml`, caches, build folders, and virtual environments.
The ZIP also includes `PACKAGE_INFO.txt`. A matching `.sha256.txt` sidecar and
version-level `release_manifest.txt` are written to `dist\` for transfer checks.

## Windows Executable ZIP

This package includes `BackboneStateTracker.exe` plus config examples and guides.

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

The generated ZIP is written to `dist\` as:

```text
backbone_state_tracker_v0.8.0_YYYYMMDD_windows_exe.zip
```

The ZIP also includes `PACKAGE_INFO.txt` and `RUN_FIRST.txt`. A matching
`.sha256.txt` sidecar and version-level `release_manifest.txt` are written to
`dist\`. After moving a ZIP into the internal environment, verify it with:

```powershell
Get-FileHash -Algorithm SHA256 .\backbone_state_tracker_v0.8.0_YYYYMMDD_windows_exe.zip
```

Corporate mail systems may block ZIP files containing `.exe`, `.py`, or `.ps1`
files. If upload is blocked, use the approved internal file transfer process.
