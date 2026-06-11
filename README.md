# Backbone State Tracker

Version: `v0.2.0`

Small Windows GUI utility for collecting read-only status snapshots from backbone
3 and 4, then comparing snapshots to track operational changes.

## What it does

- Connects to backbone devices over SSH.
- Runs read-only display commands only.
- Saves command outputs as timestamped snapshots.
- Compares two snapshots by device and command.
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

```powershell
cd "D:\Codex Project\Network\backbone_state_tracker"
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

The generated ZIP is written to `dist\`. It excludes `.git`, runtime outputs,
local `config\devices.yaml`, caches, and virtual environments.

## Guides

- `docs\USER_GUIDE.md`
- `docs\USER_GUIDE.html`
- `docs\DEVELOPER_GUIDE_BEGINNER.md`
- `docs\DEVELOPER_GUIDE_BEGINNER.html`
