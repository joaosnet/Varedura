"""Lightweight command dispatcher for Varedura.

Keep this module free of Rich, Textual, monitor and image imports so the
console entry point reaches the selected UI as quickly as possible.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Start the selected interface with all heavy imports deferred."""
    argv = sys.argv[1:]
    use_legacy = (
        "--legacy-rich" in argv or os.environ.get("VAREDURA_UI", "").lower() == "rich"
    )
    if use_legacy:
        from cli.legacy_app import run_legacy_rich

        run_legacy_rich()
        return

    from cli.textual_app import run_textual_app

    run_textual_app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
