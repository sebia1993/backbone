from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path

from .events import DiagnosticEvent
from ..redaction import redact_payload
from ..version import APP_NAME, APP_VERSION


@dataclass(frozen=True)
class DiagnosticReportPaths:
    html: Path
    json: Path
    ticket: Path


def write_diagnostic_reports(
    events: list[DiagnosticEvent] | tuple[DiagnosticEvent, ...],
    output_dir: Path,
    *,
    title: str = "Backbone State Tracker Diagnostic Report",
) -> DiagnosticReportPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    event_payload = [event.as_dict() for event in events]
    counts = _counts(event_payload)
    payload = redact_payload(
        {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "title": title,
            "raw_log_included": False,
            "counts": counts,
            "events": event_payload,
        }
    )

    json_path = output_dir / "diagnostic_report.json"
    html_path = output_dir / "diagnostic_report.html"
    ticket_path = output_dir / "diagnostic_ticket.txt"

    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    html_path.write_text(_render_html(payload), encoding="utf-8")
    ticket_path.write_text(_render_ticket(payload), encoding="utf-8")

    return DiagnosticReportPaths(html=html_path, json=json_path, ticket=ticket_path)


def _counts(events: list[dict[str, object]]) -> dict[str, int]:
    counts = {"Critical": 0, "Warning": 0, "Info": 0}
    for event in events:
        severity = str(event.get("severity", "Info"))
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _render_html(payload: dict[str, object]) -> str:
    events = list(payload.get("events", []))
    counts = dict(payload.get("counts", {}))
    rows = []
    for item in events:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('stage', '')))}</td>"
            f"<td><code>{escape(str(item.get('code', '')))}</code></td>"
            f"<td>{escape(str(item.get('severity', '')))}</td>"
            f"<td>{escape(str(item.get('status', '')))}</td>"
            f"<td>{escape(str(item.get('device_alias', '')))}</td>"
            f"<td>{escape(str(item.get('summary', '')))}</td>"
            f"<td>{escape(str(item.get('action_hint', '')))}</td>"
            f"<td>{escape(str(item.get('safe_detail', '')))}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{escape(str(payload.get('title', 'Diagnostic Report')))}</title>
  <style>
    body {{ margin: 0; background: #eef3f6; color: #17212b; font-family: "Malgun Gothic", "Segoe UI", Arial, sans-serif; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 22px 48px; }}
    header {{ background: #18232b; color: #fff; border-radius: 10px; padding: 22px 24px; }}
    .meta {{ color: #dde7ee; font-size: 13px; }}
    .cards {{ display: flex; gap: 10px; margin: 18px 0; }}
    .card {{ background: #fff; border: 1px solid #ced9e2; border-radius: 8px; padding: 12px 14px; min-width: 120px; }}
    .card strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #ced9e2; }}
    th, td {{ border-bottom: 1px solid #ced9e2; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #f7fafb; color: #60717e; }}
    code {{ font-family: Consolas, "Cascadia Mono", monospace; }}
    .safe {{ background: #ddf5f0; border-left: 4px solid #007a63; padding: 12px 14px; margin: 18px 0; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>{escape(str(payload.get('title', 'Diagnostic Report')))}</h1>
    <div class="meta">App: {escape(str(payload.get('app_name', APP_NAME)))} v{escape(str(payload.get('app_version', APP_VERSION)))} | raw_log_included=false</div>
  </header>
  <div class="safe">This report intentionally excludes raw command output, real IP addresses, hostnames, device names, and credentials.</div>
  <div class="cards">
    <div class="card">Critical<strong>{int(counts.get('Critical', 0))}</strong></div>
    <div class="card">Warning<strong>{int(counts.get('Warning', 0))}</strong></div>
    <div class="card">Info<strong>{int(counts.get('Info', 0))}</strong></div>
  </div>
  <table>
    <thead><tr><th>Stage</th><th>Code</th><th>Severity</th><th>Status</th><th>Device Alias</th><th>Summary</th><th>Action</th><th>Safe Detail</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</main>
</body>
</html>
"""


def _render_ticket(payload: dict[str, object]) -> str:
    lines = [
        f"{payload.get('app_name', APP_NAME)} v{payload.get('app_version', APP_VERSION)} diagnostic ticket",
        "raw_log_included=false",
        "",
        "Events:",
    ]
    for item in payload.get("events", []):
        if not isinstance(item, dict):
            continue
        device = f" device={item.get('device_alias')}" if item.get("device_alias") else ""
        lines.append(
            f"- {item.get('code')} {item.get('severity')} stage={item.get('stage')} "
            f"status={item.get('status')}{device} summary={item.get('summary')}"
        )
    return "\n".join(lines) + "\n"
