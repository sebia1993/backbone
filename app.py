from __future__ import annotations

import sys

from core.diagnostics.codes import explain_code
from core.diagnostics.runner import run_self_check
from core.gui import main, smoke_check
from core.mockserver.runner import run_mock_server_cli


if __name__ == "__main__":
    # 이 파일은 실행 모드의 교차로입니다. GUI 실행 외에도 테스트/진단/mock 서버를
    # 같은 EXE에서 바로 호출할 수 있게 CLI 옵션을 먼저 확인합니다.
    if "--smoke-check" in sys.argv:
        smoke_check()
    elif "--mock-server" in sys.argv:
        raise SystemExit(run_mock_server_cli(sys.argv[1:]))
    elif "--explain-code" in sys.argv:
        index = sys.argv.index("--explain-code")
        code = sys.argv[index + 1] if len(sys.argv) > index + 1 else ""
        print(explain_code(code))
    elif "--diagnose" in sys.argv:
        result = run_self_check()
        print(f"진단 리포트: {result.reports.html}")
        print(f"진단 티켓: {result.reports.ticket}")
    else:
        main()
