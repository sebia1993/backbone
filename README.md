# Backbone State Tracker

Version: `v0.8.19`

Windows GUI utility for collecting read-only status snapshots from backbone 3
and 4, then comparing snapshots to track operational changes during maintenance.

## What It Does

- Connects to backbone devices over SSH.
- Runs read-only display/check commands from `config/commands.yaml`.
- Starts on `장비 설정`.
- Combines access account, target devices, and status collection in the settings screen.
- Uses a single optional collection stage-name field. Empty input is saved as `점검시간_YYYYMMDD_HHMM`.
- Saves the first collection as the baseline snapshot and automatically compares later collections against the latest baseline.
- Moves to `작업 로그` automatically when collection starts or input/preflight validation fails.
- Tracks per-device connectivity so an unreachable backbone is reported as one Critical `device_connectivity` comparison item.
- Shows clickable `긴급`, `주의`, `정보`, `변경없음` summary cards in the GUI and HTML report.
- Keeps HTML severity summary cards visible while filtering detail blocks.
- Collapses unchanged HTML detail blocks by default.
- Generates HTML, XLSX, and JSON comparison reports.
- Creates a shared report ZIP with redacted reports, guides, and guide images while excluding snapshot raw output folders.
- Includes Korean MD/HTML user, command, developer, version-history, and release-checklist documents.
- Includes user-guide screenshots under `docs/images/`.
- Writes SHA256 sidecars, a release manifest, `PACKAGE_INFO.txt`, and Python/PowerShell release ZIP verification helpers.

## Quick Start

```powershell
cd "<folder-that-contains-backbone_state_tracker>\backbone_state_tracker"
python -m pip install -r requirements.txt
python app.py
```

Use the first `장비 설정` screen to enter backbone 3/4 device IPs, SSH username,
and password. Passwords are never saved to configuration or report files.

## Important Files

- `config/devices.example.yaml`: sample device definitions.
- `config/commands.yaml`: read-only command set.
- `outputs/snapshots/`: generated snapshot and comparison outputs.
- `docs/USER_GUIDE.md`: operator guide.
- `docs/COMMAND_GUIDE.md`: command meaning and check-point guide.
- `docs/DEVELOPER_GUIDE_BEGINNER.md`: beginner developer guide.
- `docs/VERSION_HISTORY.md`: version-by-version change history.
- `docs/RELEASE_CHECKLIST.md`: release import and verification checklist.
- `docs/images/`: user-guide screenshots.

## Test

```powershell
cd "<folder-that-contains-backbone_state_tracker>\backbone_state_tracker"
$env:PYTHONPATH=(Split-Path (Get-Location) -Parent)
python -m unittest discover -s tests
python app.py --smoke-check
```

## Source ZIP

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

The source ZIP is written to `dist\`. It excludes `.git`, runtime outputs,
local `config\devices.yaml`, caches, build folders, and virtual environments.

## Windows Executable ZIP

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

The generated ZIP is written to `dist\` as:

```text
backbone_state_tracker_v0.8.19_YYYYMMDD_windows_exe.zip
```

After moving a ZIP into the internal environment, verify it with:

```powershell
Get-FileHash -Algorithm SHA256 .\backbone_state_tracker_v0.8.19_YYYYMMDD_windows_exe.zip
python .\tools\verify_release_package.py .\dist\backbone_state_tracker_v0.8.19_YYYYMMDD_windows_exe.zip --require-manifest
powershell -ExecutionPolicy Bypass -File .\backbone_state_tracker_v0.8.19_YYYYMMDD_verify_release_package.ps1 -Package .\backbone_state_tracker_v0.8.19_YYYYMMDD_windows_exe.zip -RequireManifest
```

Corporate mail systems may block ZIP files containing `.exe`, `.py`, or `.ps1`
files. If upload is blocked, use the approved internal file transfer process.
