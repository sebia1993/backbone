from __future__ import annotations

import sys

from core.webapp import main


def _configure_cli_output_encoding(*streams: object) -> None:
    if not streams:
        streams = (sys.stdout, sys.stderr)

    for stream in streams:
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            continue


if __name__ == "__main__":
    _configure_cli_output_encoding()
    raise SystemExit(main(sys.argv[1:]))
