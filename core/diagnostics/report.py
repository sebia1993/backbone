from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path

from .codes import SEVERITY_LABELS
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
    title: str = "백본 상태 추적기 진단 리포트",
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

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
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
            f"<td>{escape(_stage_label(item.get('stage', '')))}</td>"
            f"<td><code>{escape(str(item.get('code', '')))}</code></td>"
            f"<td>{escape(_severity_label(item.get('severity', '')))}</td>"
            f"<td>{escape(_status_label(item.get('status', '')))}</td>"
            f"<td>{escape(str(item.get('device_alias', '')))}</td>"
            f"<td>{escape(str(item.get('summary', '')))}</td>"
            f"<td>{escape(str(item.get('action_hint', '')))}</td>"
            f"<td>{escape(_safe_detail_label(item.get('safe_detail', '')))}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{escape(str(payload.get('title', '진단 리포트')))}</title>
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
    <h1>{escape(str(payload.get('title', '진단 리포트')))}</h1>
    <div class="meta">앱: {escape(str(payload.get('app_name', APP_NAME)))} v{escape(str(payload.get('app_version', APP_VERSION)))} | 원본 로그 포함=false</div>
  </header>
  <div class="safe">이 리포트는 원본 명령 출력, 실제 IP 주소, 호스트명, 장비명, 인증 정보를 의도적으로 포함하지 않습니다.</div>
  <div class="cards">
    <div class="card">긴급<strong>{int(counts.get('Critical', 0))}</strong></div>
    <div class="card">주의<strong>{int(counts.get('Warning', 0))}</strong></div>
    <div class="card">정보<strong>{int(counts.get('Info', 0))}</strong></div>
  </div>
  <table>
    <thead><tr><th>단계</th><th>코드</th><th>심각도</th><th>상태</th><th>장비 alias</th><th>요약</th><th>조치</th><th>안전 상세</th></tr></thead>
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
        f"{payload.get('app_name', APP_NAME)} v{payload.get('app_version', APP_VERSION)} 진단 티켓",
        "원본 로그 포함=false",
        "",
        "이벤트:",
    ]
    for item in payload.get("events", []):
        if not isinstance(item, dict):
            continue
        device = f" 장비={item.get('device_alias')}" if item.get("device_alias") else ""
        lines.append(
            f"- {item.get('code')} {_severity_label(item.get('severity', ''))} 단계={_stage_label(item.get('stage', ''))} "
            f"상태={_status_label(item.get('status', ''))}{device} 요약={item.get('summary')}"
        )
    return "\n".join(lines) + "\n"


def _severity_label(value: object) -> str:
    severity = str(value)
    return SEVERITY_LABELS.get(severity, severity)


def _stage_label(value: object) -> str:
    stage = str(value)
    return {
        "startup": "시작",
        "config": "설정",
        "security": "보안",
        "mock": "모의 서버",
        "package": "패키지",
        "report": "리포트",
        "network": "네트워크",
        "system": "시스템",
    }.get(stage, stage)


def _status_label(value: object) -> str:
    status = str(value)
    return {
        "started": "시작됨",
        "passed": "통과",
        "failed": "실패",
        "warning": "주의",
    }.get(status, status)


def _safe_detail_label(value: object) -> str:
    detail = str(value)
    replacements = (
        ("mode=self-check", "모드=자체 점검"),
        ("commands_config=loaded", "명령 설정=로드됨"),
        ("command_count=", "명령 수="),
        ("preflight_errors=", "설정 점검 오류="),
        ("preflight_warnings=", "설정 점검 경고="),
        ("mock_profiles=loaded", "모의 장비 프로파일=로드됨"),
        ("profile=", "프로파일="),
        ("docs=present", "문서=포함됨"),
        ("required_docs=", "필수 문서 수="),
        ("device_alias_policy=enabled", "장비 alias 정책=사용"),
        ("host=", "호스트="),
        ("ip=", "IP="),
        ("raw_log_included=false", "원본 로그 포함=false"),
        ("output_path_denied=true", "출력 경로 쓰기 실패=true"),
    )
    for old, new in replacements:
        detail = detail.replace(old, new)
    return detail
