from __future__ import annotations

import csv
import json
from dataclasses import asdict
from html import escape
from pathlib import Path

from .models import DiffItem, DiffLine, DiffSummary
from .redaction import redact_payload, redact_sensitive_text
from .report_bundle import create_share_report_bundle
from .snapshot import sanitize_filename
from .version import APP_NAME, APP_VERSION
from .workflow import severity_to_korean, status_to_korean


SUMMARY_LABELS_KO = {
    "No meaningful change detected.": "의미 있는 변경 없음",
    "Target snapshot command failed.": "비교 스냅샷에서 명령 실행 실패",
    "Critical state keyword detected in changed output.": "변경 출력에서 긴급 상태 키워드 감지",
    "New critical-looking log line detected.": "신규 긴급 의심 로그 감지",
    "Warning keyword detected in changed output.": "변경 출력에서 주의 키워드 감지",
    "Operational state changed.": "운영 상태 변경 감지",
    "Output changed.": "출력 변경 감지",
    "Target device connection failed.": "비교 시점 장비 접속 실패",
    "Target device connection restored.": "비교 시점 장비 접속 복구",
}

CHANGE_TYPE_LABELS_KO = {
    "changed": "변경",
    "added": "추가",
    "removed": "삭제",
    "context": "문맥",
}


class ReportWriter:
    def write_reports(self, summary: DiffSummary) -> dict[str, Path]:
        base_name = sanitize_filename(Path(summary.base_snapshot).name)
        target_dir = Path(summary.target_snapshot)
        report_dir = target_dir / "comparisons" / f"vs_{base_name}"
        report_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = report_dir / "diff_manifest.json"
        html_path = report_dir / "diff_report.html"
        xlsx_path = report_dir / "diff_summary.xlsx"
        csv_path = report_dir / "diff_summary.csv"

        manifest_path.write_text(
            json.dumps(redact_payload(asdict(summary)), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        self._write_html(html_path, summary)
        written_xlsx = self._write_xlsx(xlsx_path, summary)
        if not written_xlsx:
            self._write_csv(csv_path, summary)
        share_zip_path = create_share_report_bundle(report_dir)

        paths = {"html": html_path, "json": manifest_path}
        if written_xlsx:
            paths["xlsx"] = xlsx_path
        else:
            paths["csv"] = csv_path
        paths["share_zip"] = share_zip_path
        return paths

    @staticmethod
    def _rows(summary: DiffSummary) -> list[dict[str, str]]:
        return [
            {
                "severity": item.severity,
                "status": item.status,
                "device": item.device_name,
                "command_id": item.command_id,
                "command": redact_sensitive_text(item.command),
                "category": item.category,
                "summary": summary_label(item),
                "change_count": str(item.change_count),
                "change_preview": redact_sensitive_text(item.change_preview),
                "base_raw_file": item.base_raw_file,
                "target_raw_file": item.target_raw_file,
            }
            for item in summary.items
        ]

    @staticmethod
    def _detail_rows(summary: DiffSummary) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for item in summary.items:
            for line in item.changed_lines:
                if line.kind == "context":
                    continue
                rows.append(
                    {
                        "severity": item.severity,
                        "status": item.status,
                        "device": item.device_name,
                        "command_id": item.command_id,
                        "command": redact_sensitive_text(item.command),
                        "category": item.category,
                        "change_type": change_type_label(line.kind),
                        "base_line_no": str(line.base_line_no or ""),
                        "target_line_no": str(line.target_line_no or ""),
                        "base_text": redact_sensitive_text(line.base_text),
                        "target_text": redact_sensitive_text(line.target_text),
                    }
                )
        return rows

    def _write_csv(self, path: Path, summary: DiffSummary) -> None:
        rows = self._rows(summary)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["severity"])
            writer.writeheader()
            writer.writerows(rows)

    def _write_xlsx(self, path: Path, summary: DiffSummary) -> bool:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
        except ImportError:  # pragma: no cover
            return False

        summary_rows = self._rows(summary)
        summary_headers = (
            list(summary_rows[0].keys())
            if summary_rows
            else ["severity", "status", "device", "command_id", "summary", "change_count", "change_preview"]
        )
        workbook = Workbook()
        summary_sheet = workbook.active
        summary_sheet.title = "diff_summary"
        summary_sheet.append(summary_headers)
        for row in summary_rows:
            summary_sheet.append([row.get(header, "") for header in summary_headers])

        header_fill = PatternFill("solid", fgColor="D9EAF7")
        severity_fill = {
            "Critical": PatternFill("solid", fgColor="F4CCCC"),
            "Warning": PatternFill("solid", fgColor="FCE5CD"),
            "Info": PatternFill("solid", fgColor="D9EAD3"),
            "Unchanged": PatternFill("solid", fgColor="EFEFEF"),
        }
        style_worksheet(summary_sheet, summary_headers, header_fill, severity_fill, max_width=70)

        detail_rows = self._detail_rows(summary)
        detail_headers = (
            list(detail_rows[0].keys())
            if detail_rows
            else [
                "severity",
                "status",
                "device",
                "command_id",
                "command",
                "category",
                "change_type",
                "base_line_no",
                "target_line_no",
                "base_text",
                "target_text",
            ]
        )
        detail_sheet = workbook.create_sheet("diff_detail")
        detail_sheet.append(detail_headers)
        for row in detail_rows:
            detail_sheet.append([row.get(header, "") for header in detail_headers])
        style_worksheet(detail_sheet, detail_headers, header_fill, severity_fill, max_width=90)

        for sheet in (summary_sheet, detail_sheet):
            for row in sheet.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)

        workbook.save(path)
        return True

    @staticmethod
    def _write_html(path: Path, summary: DiffSummary) -> None:
        counts = summary.counts
        rows_html = []
        details_html = []
        colors = {
            "Critical": "#b42318",
            "Warning": "#b54708",
            "Info": "#027a48",
            "Unchanged": "#667085",
        }
        for index, item in enumerate(summary.items, start=1):
            detail_id = f"diff-{index}"
            severity_label = severity_to_korean(item.severity)
            status_label = status_to_korean(item.status)
            item_summary = redact_sensitive_text(summary_label(item))
            change_preview = redact_sensitive_text(item.change_preview or "-")
            rows_html.append(
                "<tr>"
                f"<td><span class='badge' style='background:{colors.get(item.severity, '#667085')}'>{escape(severity_label)}</span></td>"
                f"<td>{escape(status_label)}</td>"
                f"<td>{escape(item.device_name)}</td>"
                f"<td>{escape(item.command_id)}</td>"
                f"<td>{escape(item.category)}</td>"
                f"<td>{item.change_count}</td>"
                f"<td>{escape(change_preview)}</td>"
                f"<td>{escape(item_summary)}</td>"
                f"<td><a href='#{detail_id}'>상세</a></td>"
                "</tr>"
            )
            details_html.append(
                f"<section class='diff-block' id='{detail_id}'>"
                f"<h2>{escape(item.device_name)} / {escape(item.command_id)}</h2>"
                f"<p>{escape(item_summary)}</p>"
                f"{render_change_table(item)}"
                "<details class='raw-diff'>"
                "<summary>원본 unified diff 보기</summary>"
                f"<pre>{escape(redact_sensitive_text(item.diff or '상세 diff 없음'))}</pre>"
                "</details>"
                "</section>"
            )

        html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(APP_NAME)} v{escape(APP_VERSION)} 스냅샷 비교 리포트</title>
  <style>
    :root {{
      --bg: #f4f6f8;
      --panel: #ffffff;
      --line: #d0d7de;
      --text: #1f2328;
      --muted: #59636e;
      --added: #e7f7f2;
      --removed: #fdeceb;
      --changed: #fff4e5;
      --context: #f7f9fb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    .wrap {{ max-width: 1360px; margin: 0 auto; padding: 24px; }}
    header {{ margin-bottom: 18px; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .counts {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 18px 0;
    }}
    .count {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .count strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    .table-panel, .diff-block {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      margin-bottom: 16px;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #eaeef2; text-align: left; font-size: 13px; vertical-align: top; }}
    th {{ background: #eef3f8; }}
    .badge {{ color: #fff; border-radius: 999px; padding: 3px 8px; font-size: 12px; font-weight: 700; }}
    .diff-block {{ padding: 14px; }}
    .diff-block h2 {{ margin: 0 0 6px; font-size: 17px; }}
    .change-table-wrap {{
      overflow-x: auto;
      margin: 12px 0;
      border: 1px solid #eaeef2;
      border-radius: 6px;
    }}
    .change-table {{ width: max-content; min-width: 100%; border-collapse: collapse; margin: 0; }}
    .change-table th:nth-child(1) {{ width: 82px; }}
    .change-table th:nth-child(2) {{ width: 110px; }}
    .change-table td {{ word-break: normal; white-space: nowrap; }}
    .change-kind {{
      display: inline-flex;
      align-items: center;
      border: 1px solid #d0d7de;
      border-radius: 999px;
      padding: 2px 8px;
      background: #fff;
      font-size: 12px;
      font-weight: 700;
      color: #1f2328;
    }}
    .line-no {{
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }}
    .change-inline {{
      font-family: Consolas, "SFMono-Regular", monospace;
      line-height: 1.7;
    }}
    .value-before, .value-after, .value-context {{
      display: inline-block;
      border: 1px solid transparent;
      border-radius: 4px;
      padding: 2px 6px;
    }}
    .value-before {{
      background: var(--removed);
      border-color: #f4b8b2;
      color: #8a1f16;
    }}
    .value-after {{
      background: var(--added);
      border-color: #a8dfd2;
      color: #007a63;
    }}
    .value-context {{
      color: var(--muted);
      padding-left: 0;
    }}
    .diff-arrow {{ color: var(--muted); font-weight: 700; padding: 0 8px; }}
    .diff-prefix {{ color: var(--muted); font-weight: 700; margin-right: 6px; }}
    .line-added {{ background: var(--added); }}
    .line-removed {{ background: var(--removed); }}
    .line-changed {{ background: var(--changed); }}
    .line-context {{ background: var(--context); color: var(--muted); }}
    .raw-diff summary {{ cursor: pointer; color: #0969da; font-weight: 700; margin: 10px 0; }}
    pre {{
      background: #0d1117;
      color: #e6edf3;
      border-radius: 6px;
      padding: 12px;
      overflow: auto;
      line-height: 1.4;
      font-size: 12px;
    }}
    a {{ color: #0969da; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 900px) {{
      .counts {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .table-panel {{ overflow-x: auto; }}
      table {{ min-width: 1000px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{escape(APP_NAME)} 스냅샷 비교 리포트</h1>
      <div class="meta">버전: v{escape(APP_VERSION)} | 기준: {escape(Path(summary.base_snapshot).name)} | 비교: {escape(Path(summary.target_snapshot).name)} | 생성: {escape(summary.generated_at)}</div>
    </header>
    <section class="counts">
      <div class="count">긴급<strong>{counts.get('Critical', 0)}</strong></div>
      <div class="count">주의<strong>{counts.get('Warning', 0)}</strong></div>
      <div class="count">정보<strong>{counts.get('Info', 0)}</strong></div>
      <div class="count">변경없음<strong>{counts.get('Unchanged', 0)}</strong></div>
    </section>
    <section class="table-panel">
      <table>
        <thead>
          <tr>
            <th>등급</th>
            <th>상태</th>
            <th>장비</th>
            <th>명령</th>
            <th>분류</th>
            <th>변경 수</th>
            <th>첫 변경 내용</th>
            <th>요약</th>
            <th>상세</th>
          </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </section>
    {''.join(details_html)}
  </div>
</body>
</html>
"""
        path.write_text(html, encoding="utf-8")


def style_worksheet(sheet, headers, header_fill, severity_fill, max_width: int) -> None:
    from openpyxl.styles import Font

    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
    if "severity" in headers and sheet.max_row > 1:
        severity_col = headers.index("severity") + 1
        for row in range(2, sheet.max_row + 1):
            severity = sheet.cell(row=row, column=severity_col).value
            fill = severity_fill.get(severity)
            if fill:
                sheet.cell(row=row, column=severity_col).fill = fill
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        max_len = max(len(str(cell.value or "")) for cell in column)
        sheet.column_dimensions[column[0].column_letter].width = min(max(max_len + 2, 12), max_width)


def summary_label(item: DiffItem) -> str:
    return SUMMARY_LABELS_KO.get(item.summary, item.summary)


def change_type_label(kind: str) -> str:
    return CHANGE_TYPE_LABELS_KO.get(kind, kind)


def render_change_table(item: DiffItem) -> str:
    if not item.changed_lines:
        return "<p class='meta'>행 단위 변경 상세 없음</p>"

    rows = []
    for line in item.changed_lines:
        rows.append(
            f"<tr class='{line_css_class(line)}'>"
            f"<td><span class='change-kind'>{escape(change_type_label(line.kind))}</span></td>"
            f"<td class='line-no'>{escape(format_inline_line_no(line))}</td>"
            f"<td class='change-inline'>{render_inline_change(line)}</td>"
            "</tr>"
        )
    return (
        "<div class='change-table-wrap'>"
        "<table class='change-table'>"
        "<thead><tr><th>유형</th><th>라인</th><th>변경 내용</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


def line_css_class(line: DiffLine) -> str:
    return {
        "added": "line-added",
        "removed": "line-removed",
        "changed": "line-changed",
        "context": "line-context",
    }.get(line.kind, "")


def format_line_no(value: int | None) -> str:
    return "-" if value is None else str(value)


def format_inline_line_no(line: DiffLine) -> str:
    base_line_no = format_line_no(line.base_line_no)
    target_line_no = format_line_no(line.target_line_no)
    if line.kind == "added":
        return f"- → {target_line_no}"
    if line.kind == "removed":
        return f"{base_line_no} → -"
    return f"{base_line_no} → {target_line_no}"


def render_inline_change(line: DiffLine) -> str:
    if line.kind == "changed":
        return (
            f"{render_value(line.base_text, 'value-before')}"
            "<span class='diff-arrow'>→</span>"
            f"{render_value(line.target_text, 'value-after')}"
        )
    if line.kind == "added":
        return f"<span class='diff-prefix'>추가:</span>{render_value(line.target_text, 'value-after')}"
    if line.kind == "removed":
        return f"<span class='diff-prefix'>삭제:</span>{render_value(line.base_text, 'value-before')}"
    return render_value(line.target_text or line.base_text, "value-context")


def render_value(value: str, css_class: str) -> str:
    return f"<span class='{css_class}'>{escape(redact_sensitive_text(value) or '-')}</span>"
