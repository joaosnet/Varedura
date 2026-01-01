"""Admin helper script for running admin-only tasks.

This script is intended to be invoked with a `runas` elevation from the UI.
It exposes a small set of operations that require admin privileges (e.g., compacting VHDX or configuring sparse mode).
"""

from __future__ import annotations

import sys
import argparse
from docker_cleaner.core import WSLDockerCleaner


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Admin-only tasks for Docker-Clennear")
    parser.add_argument(
        "task", choices=["compact_vhdx", "configure_sparse"], help="Admin task to run"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cleaner = WSLDockerCleaner()
    if not cleaner.is_admin():
        # Guard: If we are not admin, print error and exit non-zero
        print("This helper script must be run as administrator.")
        return 1
    if args.task == "compact_vhdx":
        res = cleaner.compact_vhdx_files()
        print("Compact VHDX result:", res)
        return 0 if res else 1
    if args.task == "configure_sparse":
        res = cleaner.configure_wsl_sparse()
        print("Configure sparse result:", res)
        return 0 if res else 1
    # unreachable
    return 2


if __name__ == "__main__":
    sys.exit(main())
