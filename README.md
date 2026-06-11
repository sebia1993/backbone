# Backbone State Tracker

Version: `v0.4.0`

Small Windows GUI utility for collecting read-only status snapshots from backbone
3 and 4, then comparing snapshots to track operational changes.

## What it does

- Connects to backbone devices over SSH.
- Runs read-only display commands only.
- Saves command outputs as timestamped snapshots.
- Compares two snapshots by device and command.
- Automatically compares `백본3 OFF 중`, `복구 후`, and custom snapshots against the latest `작업 전` snapshot.
- Writes HTML, XLSX, and JSON comparison reports.

## Quick start

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
python -m pip install -r requirements.txt
python app.py
```

Use the GUI to enter device IPs, SSH username, password, and a snapshot label such
as `pre`, `bb3_off`, or `post_restore`.

Passwords are never saved to configuration or report files.

## Important files

- `config/devices.example.yaml`: sample device definitions.
- `config/commands.yaml`: read-only command set.
- `outputs/snapshots/`: generated snapshot and comparison outputs.

## Test

```powershell
cd "D:\Codex Project\Network"
python -m unittest discover -s backbone_state_tracker\tests
```

## Release ZIP

Source ZIP only. This does not include a Windows `.exe`.

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

The generated ZIP is written to `dist\`. It excludes `.git`, runtime outputs,
local `config\devices.yaml`, caches, and virtual environments.

## Windows executable ZIP

This package includes `BackboneStateTracker.exe` plus config examples and guides.

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_exe.ps1
```

The generated ZIP is written to `dist\` as:

```text
backbone_state_tracker_v0.4.0_YYYYMMDD_windows_exe.zip
```

Corporate mail systems may block ZIP files containing `.exe`, `.py`, or `.ps1`
files. If upload is blocked, use the approved internal file transfer process.

## Guides

- `docs\USER_GUIDE.md`
- `docs\USER_GUIDE.html`
- `docs\DEVELOPER_GUIDE_BEGINNER.md`
- `docs\DEVELOPER_GUIDE_BEGINNER.html`
- `docs\VERSION_HISTORY.md`
- `docs\VERSION_HISTORY.html`
