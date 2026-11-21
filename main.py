"""Lightweight command dispatcher for Varedura.

Keep this module free of Rich, Textual, monitor and image imports so the
console entry point reaches the Textual UI as quickly as possible.
"""

from __future__ import annotations


def main() -> None:
    """Start the Textual interface with all heavy imports deferred."""
    from cli.textual_app import run_textual_app

    run_textual_app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
