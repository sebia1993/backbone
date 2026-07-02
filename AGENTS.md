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
- After code changes, decide whether `README.md`, `RELEASE_NOTES.md`, or
  `CHANGELOG.md` must change. State the decision in the final report even when
  no document edit is needed.
- Before any push, pull request, or release, re-check that `README.md` matches
  the current install, run, build, usage, release asset, folder, and limitation
  details.
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
- `RELEASE_NOTES.md`: release-note policy and checklist. GitHub Actions creates
  the public release body automatically, but this tracked file defines what must
  be checked before publishing.

## Validation Commands

Use the narrowest relevant check while developing, then run the full baseline
before calling work complete.

```powershell
python -m unittest discover -s tests
python app.py --smoke-check
python app.py --diagnose --self-check
```

Run the PowerShell release verifiers on Windows or in GitHub Actions. This Mac
does not prove Windows EXE packaging by itself.

## README / Release Document Rules

- If behavior, install/run/build commands, release filenames, executable names,
  folder structure, requirements, or troubleshooting steps change, update
  `README.md` in the same change.
- If a change is release-facing, check `README.md`, `RELEASE_NOTES.md`, and
  `CHANGELOG.md` together.
- Do not document features that are not implemented. If a feature is planned but
  not implemented, label it as not implemented.
- Use sample values only. Never place internal IPs, real device names, accounts,
  passwords, customer data, or raw operational logs in README, release notes, or
  changelog entries.
- Separate files that must be committed to Git from files uploaded as GitHub
  Release assets. The current automatic public Release assets are the Windows
  EXE ZIP and its `.sha256` sidecar.
- Do not say macOS creates a Windows EXE directly. Windows EXE packaging is
  validated by the Windows runner or a Windows workstation.

## Safety Rules

- Prefer read-only collection, dry-run behavior, and simulated devices.
- Keep field diagnostics shareable through sanitized stages, timings, counts,
  and stable error codes.
- Mask secrets and operational identifiers unless the user explicitly requests a
  local-only raw export.
- Do not make live network changes unless the user clearly asks for that exact
  operation.
