from __future__ import annotations

import sys

from core.diagnostics.codes import explain_code
from core.diagnostics.runner import run_self_check
from core.gui import main, smoke_check
from core.mockserver.runner import run_mock_server_cli


if __name__ == "__main__":
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
        print(f"Diagnostic report: {result.reports.html}")
        print(f"Diagnostic ticket: {result.reports.ticket}")
    else:
        main()
