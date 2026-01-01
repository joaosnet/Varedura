"""Rich/Local daily log writer used by the Textual UI.

This module exposes a `DailyLogWriter` class that can be used as a file-like
writer with `rich.console.Console(file=writer)`. It writes messages to the UI
via the provided app (calling `call_from_thread`) and also persists them into
daily rotated files under `logs/YYYY-MM-DD.log`.

The file contains plain-text, timestamped messages. If the app is provided,
the messages are also written to Textual `Log`/`RichLog` using the same API.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
import asyncio


class DailyLogWriter:
    """File-like writer that writes log messages to a rotating daily file
    and optionally to a UI callback.

    The `ui_write` callable should accept a single string argument and will
    be scheduled using `app.call_from_thread` by the caller if needed.
    """

    def __init__(
        self,
        logs_dir: Optional[Path | str] = None,
        ui_write: Optional[Callable[[str], None]] = None,
    ):
        self.logs_dir = Path(logs_dir or "logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.ui_write = ui_write
        self._last_date = None
        self._current_fp = None

    def _open_today_file(self):
        today = datetime.now().date()
        if self._last_date == today and self._current_fp:
            return
        # Close previous
        if self._current_fp:
            try:
                self._current_fp.flush()
                self._current_fp.close()
            except Exception:
                pass
        self._last_date = today
        filename = self.logs_dir / f"{today.isoformat()}.log"
        # Open in append mode - text
        self._current_fp = open(filename, "a", encoding="utf-8")

    def write(self, text: str) -> None:
        # Normalize the message and split into lines
        if not text:
            return
        self._open_today_file()
        # Ensure trimmed trailing newlines when writing timestamped lines.
        lines = text.splitlines()
        for line in lines:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            out = f"[{ts}] {line}\n"
            try:
                if self._current_fp:
                    self._current_fp.write(out)
            except Exception:
                # Swallow errors to avoid crashing the writer
                pass
            # Also write to UI if provided
            if self.ui_write:
                try:
                    res = self.ui_write(line)
                    # If the ui_write returned a coroutine (async function), ensure it's awaited/scheduled
                    if asyncio.iscoroutine(res) or isinstance(res, asyncio.Future):
                        try:
                            # If an event loop is running, schedule the coroutine; otherwise run it directly
                            loop = None
                            try:
                                loop = asyncio.get_running_loop()
                            except RuntimeError:
                                loop = None
                            if loop and loop.is_running():
                                asyncio.create_task(res)
                            else:
                                asyncio.run(res)
                        except Exception:
                            # Swallow to avoid raising in logger
                            pass
                except Exception:
                    pass

    def flush(self) -> None:
        if self._current_fp:
            try:
                self._current_fp.flush()
            except Exception:
                pass

    def close(self) -> None:
        if self._current_fp:
            try:
                self._current_fp.flush()
                self._current_fp.close()
            except Exception:
                pass
