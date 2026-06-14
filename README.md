# Backbone State Tracker

Version: `v0.8.52`

Windows GUI utility for collecting read-only status snapshots from backbone 3
and 4, then comparing snapshots to track operational changes during maintenance.

## What It Does

- Connects to backbone devices over SSH.
- Runs read-only display/check commands from `config/commands.yaml`.
- Adds `vrrp_status` with `show vrrp` to capture VRRP master/backup and virtual router state.
- Verifies the bundled command set remains preflight-safe and read-only without warnings.
- Keeps command guide MD/HTML entries aligned with the bundled command set.
- Applies an AirWave-inspired operations-console theme with a dark navigation rail, Aruba teal action color, quieter cards, and denser tables.
- Starts on `장비 설정`.
- Combines access account, target devices, and status collection in the settings screen.
- Keeps two default target device rows and lets operators add more rows when extra backbone targets need the same check.
- Keeps the settings screen scrollable and shows a live target device count summary when rows are added.
- Uses a single optional collection stage-name field. Empty input is saved as `점검시간_YYYYMMDD_HHMM`.
- Saves the first collection as the baseline snapshot and automatically compares later collections against the latest baseline.
- Moves to `작업 로그` automatically when collection starts or input/preflight validation fails.
- Blocks preflight and snapshot-list refresh actions while another collection or comparison workflow is already running.
- Tracks per-device connectivity so an unreachable backbone is reported as one Critical `device_connectivity` comparison item.
- Classifies `cpu_usage` and `memory_usage` by the current target snapshot thresholds only: Critical/Warning at the configured limits and Info when values are normal.
- Shows clickable `긴급`, `주의`, `정보`, `변경없음` summary cards in the GUI and HTML report.
- Keeps HTML report detail content hidden until an operator selects `긴급`, `주의`, `정보`, or `변경없음`, with enforced hidden rendering in the generated HTML.
- Adds HTML report status shortcut buttons for the selected status only, then jumps directly to the matching device/command detail block.
- Shows visible type, line, and change-content labels inside HTML report detail rows so isolated rows remain understandable.
- Keeps unchanged HTML summary cards and detail blocks collapsed until an operator manually expands them.
- Validates generated HTML report filter markup with parser-based regression tests.
- Validates current-version alignment across README, CHANGELOG, and release guide MD/HTML documents.
- Verifies source release ZIPs include the full regression test suite, not only packaging tests.
- Checks the source ZIP verifier's required test-file lists stay aligned with the real `tests/test_*.py` files.
- Verifies source release ZIPs include all `core/*.py` runtime modules and `requirements.txt` for internal rebuilds.
- Checks release tool script requirements stay aligned with the real `tools/*.py` and `tools/*.ps1` files.
- Checks packaged guide documents and guide images stay aligned with the real `docs/` files.
- Checks packaged shareable config files stay aligned with the real `config/` files while keeping local `config/devices.yaml` excluded.
- Verifies Windows EXE ZIPs cannot omit `BackboneStateTracker.exe` or `RUN_FIRST.txt`.
- Rejects runtime outputs, build artifacts, virtual environments, and test caches in release ZIP verification.
- Guards Korean user/developer guides against encoding corruption and missing core workflow terms.
- Generates HTML, XLSX, and JSON comparison reports.
- Keeps sample validation snapshots out of real pre-work baseline selection.
- Labels sample snapshots as `샘플:` in the top runtime summary.
- Labels sample snapshots as `샘플:` in HTML comparison report header metadata.
- Creates a shared report ZIP with redacted reports, guides, and guide images while excluding snapshot raw output folders.
- Includes operator, command, developer, version-history, and release-checklist guides in shared report ZIPs.
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
and password. Use `장비 추가` only when more target devices need to be included.
Passwords are never saved to configuration or report files.

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
backbone_state_tracker_v0.8.52_YYYYMMDD_windows_exe.zip
```

After moving a ZIP into the internal environment, verify it with:

```powershell
Get-FileHash -Algorithm SHA256 .\backbone_state_tracker_v0.8.52_YYYYMMDD_windows_exe.zip
python .\tools\verify_release_package.py .\dist\backbone_state_tracker_v0.8.52_YYYYMMDD_windows_exe.zip --require-manifest
powershell -ExecutionPolicy Bypass -File .\backbone_state_tracker_v0.8.52_YYYYMMDD_verify_release_package.ps1 -Package .\backbone_state_tracker_v0.8.52_YYYYMMDD_windows_exe.zip -RequireManifest
```

Corporate mail systems may block ZIP files containing `.exe`, `.py`, or `.ps1`
files. If upload is blocked, use the approved internal file transfer process.
