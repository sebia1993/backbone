from __future__ import annotations

import csv
import json
from dataclasses import asdict
from html import escape
from pathlib import Path

from .models import DiffSummary
from .snapshot import sanitize_filename
from .version import APP_NAME, APP_VERSION


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
            json.dumps(asdict(summary), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        self._write_html(html_path, summary)
        written_xlsx = self._write_xlsx(xlsx_path, summary)
        if not written_xlsx:
            self._write_csv(csv_path, summary)

        paths = {"html": html_path, "json": manifest_path}
        if written_xlsx:
            paths["xlsx"] = xlsx_path
        else:
            paths["csv"] = csv_path
        return paths

    @staticmethod
    def _rows(summary: DiffSummary) -> list[dict[str, str]]:
        return [
            {
                "severity": item.severity,
                "status": item.status,
                "device": item.device_name,
                "command_id": item.command_id,
                "command": item.command,
                "category": item.category,
                "summary": item.summary,
                "base_raw_file": item.base_raw_file,
                "target_raw_file": item.target_raw_file,
            }
            for item in summary.items
        ]

    def _write_csv(self, path: Path, summary: DiffSummary) -> None:
        rows = self._rows(summary)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["severity"])
            writer.writeheader()
            writer.writerows(rows)

    def _write_xlsx(self, path: Path, summary: DiffSummary) -> bool:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill
        except ImportError:  # pragma: no cover
            return False

        rows = self._rows(summary)
        headers = list(rows[0].keys()) if rows else ["severity", "status", "device", "command_id", "summary"]
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "diff_summary"
        sheet.append(headers)
        for row in rows:
            sheet.append([row.get(header, "") for header in headers])

        header_fill = PatternFill("solid", fgColor="D9EAF7")
        severity_fill = {
            "Critical": PatternFill("solid", fgColor="F4CCCC"),
            "Warning": PatternFill("solid", fgColor="FCE5CD"),
            "Info": PatternFill("solid", fgColor="D9EAD3"),
            "Unchanged": PatternFill("solid", fgColor="EFEFEF"),
        }
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
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
            sheet.column_dimensions[column[0].column_letter].width = min(max(max_len + 2, 12), 60)
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
            rows_html.append(
                "<tr>"
                f"<td><span class='badge' style='background:{colors.get(item.severity, '#667085')}'>{escape(item.severity)}</span></td>"
                f"<td>{escape(item.status)}</td>"
                f"<td>{escape(item.device_name)}</td>"
                f"<td>{escape(item.command_id)}</td>"
                f"<td>{escape(item.category)}</td>"
                f"<td>{escape(item.summary)}</td>"
                f"<td><a href='#{detail_id}'>diff</a></td>"
                "</tr>"
            )
            details_html.append(
                f"<section class='diff-block' id='{detail_id}'>"
                f"<h2>{escape(item.device_name)} / {escape(item.command_id)}</h2>"
                f"<p>{escape(item.summary)}</p>"
                f"<pre>{escape(item.diff or 'No diff body.')}</pre>"
                "</section>"
            )

        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(APP_NAME)} v{escape(APP_VERSION)} Snapshot Diff</title>
  <style>
    :root {{
      --bg: #f4f6f8;
      --panel: #ffffff;
      --line: #d0d7de;
      --text: #1f2328;
      --muted: #59636e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
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
    th, td {{ padding: 10px; border-bottom: 1px solid #eaeef2; text-align: left; font-size: 13px; }}
    th {{ background: #eef3f8; }}
    .badge {{ color: #fff; border-radius: 999px; padding: 3px 8px; font-size: 12px; font-weight: 700; }}
    .diff-block {{ padding: 14px; }}
    .diff-block h2 {{ margin: 0 0 6px; font-size: 17px; }}
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
      table {{ min-width: 900px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{escape(APP_NAME)} Snapshot Diff</h1>
      <div class="meta">Version: v{escape(APP_VERSION)} | Base: {escape(Path(summary.base_snapshot).name)} | Target: {escape(Path(summary.target_snapshot).name)} | Generated: {escape(summary.generated_at)}</div>
    </header>
    <section class="counts">
      <div class="count">Critical<strong>{counts.get('Critical', 0)}</strong></div>
      <div class="count">Warning<strong>{counts.get('Warning', 0)}</strong></div>
      <div class="count">Info<strong>{counts.get('Info', 0)}</strong></div>
      <div class="count">Unchanged<strong>{counts.get('Unchanged', 0)}</strong></div>
    </section>
    <section class="table-panel">
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th>Status</th>
            <th>Device</th>
            <th>Command</th>
            <th>Category</th>
            <th>Summary</th>
            <th>Detail</th>
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
