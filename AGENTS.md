# Backbone State Tracker Codex Instructions

## Scope

This file applies to the `backbone_state_tracker` repository.

Keep this `AGENTS.md` tracked in Git. It is part of the source handoff so the
same project rules follow GitHub clones, MacBook work, GitHub Actions, and
future Windows workstations.

## Project Summary

This repository is a Windows-focused network diagnostics tool for collecting,
comparing, and reporting backbone device state. It uses local configuration,
mockable SSH/Telnet boundaries, diagnostic event codes, redaction helpers, and
release packaging scripts.

## Default Workflow

- Inspect `git status --short --branch` before editing or committing.
- Keep changes scoped to this repository.
- Use deterministic tests, fixtures, and mock servers before any real device
  validation.
- Do not use real company logs, credentials, device captures, IP lists, host
  names, or customer data in tests, docs, commits, or final responses.
- Keep generated folders and release outputs out of Git.

## Important Areas

- `app.py`: application entry point.
- `core/`: workflow, collection, diagnostics, redaction, reporting, and GUI code.
- `core/mockserver/`: local mock SSH/Telnet server support.
- `config/`: example commands, devices, and mock profiles.
- `tests/`: deterministic unit and integration tests.
- `tools/`: Windows release and package verification scripts.
- `docs/`: user, developer, diagnostic, and release documentation.

## Validation Commands

Use the narrowest relevant check while developing, then run the full baseline
before calling work complete.

```powershell
python -m pytest
powershell -ExecutionPolicy Bypass -File .\tools\verify_release_package.ps1
```

## Safety Rules

- Prefer read-only collection, dry-run behavior, and simulated devices.
- Keep field diagnostics shareable through sanitized stages, timings, counts,
  and stable error codes.
- Mask secrets and operational identifiers unless the user explicitly requests a
  local-only raw export.
- Do not make live network changes unless the user clearly asks for that exact
  operation.
