from __future__ import annotations

import sys

from core.gui import main, smoke_check


if __name__ == "__main__":
    if "--smoke-check" in sys.argv:
        smoke_check()
    else:
        main()
