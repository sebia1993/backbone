from __future__ import annotations

import argparse
import html
import json
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .mock_validation import create_mock_validation_artifacts
from .paths import runtime_root
from .snapshot import SnapshotStore
from .version import APP_NAME, APP_VERSION


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def web_data_root() -> Path:
    root = runtime_root()
    if getattr(sys, "frozen", False) and root.name.lower() == "runtime":
        return root.parent
    return root


def build_health_payload() -> dict[str, object]:
    return {
        "ok": True,
        "app": APP_NAME,
        "version": APP_VERSION,
        "mode": "webapp",
    }


def build_home_page() -> str:
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>백본 상태 추적기 웹앱</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fa;
      --panel: #ffffff;
      --text: #17212b;
      --muted: #52616f;
      --line: #d9e2ec;
      --accent: #008c95;
      --accent-dark: #00656c;
    }
    body {
      margin: 0;
      font-family: "Malgun Gothic", "Apple SD Gothic Neo", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }
    header {
      background: #102a43;
      color: #f8fafc;
      padding: 24px clamp(18px, 4vw, 40px);
    }
    main {
      max-width: 1040px;
      margin: 0 auto;
      padding: 24px clamp(16px, 4vw, 32px) 48px;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 20px;
      letter-spacing: 0;
    }
    p {
      margin: 0 0 12px;
    }
    .meta {
      margin-top: 6px;
      color: #bcccdc;
      font-size: 14px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(16, 42, 67, 0.08);
    }
    .button {
      display: inline-block;
      border-radius: 6px;
      background: var(--accent);
      color: #ffffff;
      padding: 10px 14px;
      text-decoration: none;
      font-weight: 700;
    }
    .button:hover {
      background: var(--accent-dark);
    }
    code {
      background: #eef2f6;
      border: 1px solid #d9e2ec;
      border-radius: 4px;
      padding: 2px 5px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.95em;
    }
    ul {
      margin: 0;
      padding-left: 20px;
    }
    li + li {
      margin-top: 6px;
    }
  </style>
</head>
<body>
  <header>
    <h1>백본 상태 추적기 웹앱</h1>
    <div class="meta">로컬 PC에서만 열리는 운영 점검 화면입니다.</div>
  </header>
  <main>
    <div class="grid">
      <section class="panel">
        <h2>상태</h2>
        <p>웹앱 런타임이 정상으로 시작되었습니다.</p>
        <ul>
          <li>앱 버전: <code>""" + html.escape(APP_VERSION) + """</code></li>
          <li>헬스 체크: <code>/health</code></li>
        </ul>
      </section>
      <section class="panel">
        <h2>샘플 검증</h2>
        <p>실제 장비 접속 없이 샘플 스냅샷과 비교 리포트를 생성합니다.</p>
        <p><a class="button" href="/sample">샘플 검증 생성</a></p>
      </section>
      <section class="panel">
        <h2>저장 위치</h2>
        <p>웹앱에서 생성한 결과는 웹앱 폴더 아래 <code>outputs</code>에 저장됩니다.</p>
      </section>
    </div>
  </main>
</body>
</html>
"""


def build_sample_result_page() -> str:
    store = SnapshotStore(web_data_root() / "outputs" / "snapshots")
    result = create_mock_validation_artifacts(store)
    links = [
        ("백본3 OFF 비교 리포트", result.off_report),
        ("복구 후 비교 리포트", result.restore_report),
        ("OFF 이후 복구 비교 리포트", result.restore_from_off_report),
    ]
    items = "\n".join(
        f"<li>{html.escape(label)}: <code>{html.escape(str(path))}</code></li>" for label, path in links
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>샘플 검증 생성 완료</title>
  <style>
    body {{ font-family: "Malgun Gothic", Arial, sans-serif; margin: 32px; color: #17212b; line-height: 1.6; }}
    a {{ color: #00656c; font-weight: 700; }}
    code {{ background: #eef2f6; border: 1px solid #d9e2ec; border-radius: 4px; padding: 2px 5px; }}
  </style>
</head>
<body>
  <h1>샘플 검증 생성 완료</h1>
  <p>실제 장비 접속 없이 샘플 스냅샷과 HTML 비교 리포트를 만들었습니다.</p>
  <ul>
    {items}
  </ul>
  <p><a href="/">웹앱 홈으로 돌아가기</a></p>
</body>
</html>
"""


class BackboneWebAppHandler(BaseHTTPRequestHandler):
    server_version = "BackboneWebApp/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("", "/"):
            self._send_html(build_home_page())
            return
        if path == "/health":
            self._send_json(build_health_payload())
            return
        if path == "/sample":
            self._send_html(build_sample_result_page())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: object) -> None:
        print("[webapp] " + format % args)

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, payload: dict[str, object]) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_smoke_check() -> int:
    home = build_home_page()
    health = build_health_payload()
    checks = [
        "백본 상태 추적기 웹앱" in home,
        "/health" in home,
        health.get("ok") is True,
        health.get("mode") == "webapp",
    ]
    if not all(checks):
        print("webapp_smoke=failed")
        return 1
    print("webapp_smoke=ok")
    return 0


def run_server(host: str, port: int, open_browser: bool = True) -> int:
    server = ThreadingHTTPServer((host, port), BackboneWebAppHandler)
    url = f"http://{host}:{port}/"
    print(f"웹앱 주소: {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("웹앱을 종료합니다.")
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="백본 상태 추적기 로컬 웹앱을 실행합니다.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    if args.smoke:
        return run_smoke_check()
    return run_server(args.host, args.port, open_browser=not args.no_browser)
