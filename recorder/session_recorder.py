"""Session recorder — captures Rich console output as SVG snapshots."""

from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Optional

from rich.console import Console


class SessionRecorder:
    """Records a Rich console session by taking periodic SVG snapshots.

    Usage:
        recorder = SessionRecorder()
        with recorder:
            console.print("Hello!")
            # ... tool execution ...
        recorder.save_gif("output.gif")
    """

    def __init__(
        self,
        width: int = 120,
        height: int = 40,
        snapshot_interval: float = 1.0,
        max_frames: int = 60,
    ):
        self.width = width
        self.height = height
        self.snapshot_interval = snapshot_interval
        self.max_frames = max_frames

        self._console: Optional[Console] = None
        self._svg_frames: list[str] = []
        self._stop_event = threading.Event()
        self._snapshot_thread: Optional[threading.Thread] = None
        self._recording = False

    @property
    def console(self) -> Console:
        """The recording console. Use this to print during recording."""
        if self._console is None:
            self._console = Console(record=True, width=self.width)
        return self._console

    @property
    def frames(self) -> list[str]:
        """Collected SVG frames."""
        return self._svg_frames

    @property
    def is_recording(self) -> bool:
        return self._recording

    def __enter__(self) -> "SessionRecorder":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        """Begin recording with periodic snapshots."""
        self._console = Console(record=True, width=self.width)
        self._svg_frames = []
        self._stop_event.clear()
        self._recording = True

        self._snapshot_thread = threading.Thread(
            target=self._snapshot_loop, daemon=True
        )
        self._snapshot_thread.start()

    def stop(self) -> None:
        """Stop recording and capture final frame."""
        self._recording = False
        self._stop_event.set()

        if self._snapshot_thread and self._snapshot_thread.is_alive():
            self._snapshot_thread.join(timeout=2.0)

        # Capture final state
        self._take_snapshot()

    def _snapshot_loop(self) -> None:
        """Background loop taking periodic SVG snapshots."""
        while not self._stop_event.is_set() and len(self._svg_frames) < self.max_frames:
            self._take_snapshot()
            self._stop_event.wait(self.snapshot_interval)

    def _take_snapshot(self) -> None:
        """Capture current console state as SVG."""
        if self._console is None:
            return
        try:
            svg = self._console.export_svg(title="Varedura", clear=False)
            if svg and len(self._svg_frames) < self.max_frames:
                self._svg_frames.append(svg)
        except Exception:
            pass

    def save_gif(
        self,
        output_path: str | Path,
        fps: int = 2,
        last_frame_duration: float = 3.0,
    ) -> Optional[Path]:
        """Generate animated GIF from recorded frames.

        Returns:
            Path to the generated GIF, or None if generation failed.
        """
        if not self._svg_frames:
            return None

        from recorder.gif_generator import generate_gif

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        return generate_gif(
            svg_frames=self._svg_frames,
            output_path=path,
            fps=fps,
            last_frame_duration=last_frame_duration,
        )

    def save_svg(self, output_path: str | Path) -> Optional[Path]:
        """Save the final frame as a standalone SVG."""
        if not self._svg_frames:
            return None

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._svg_frames[-1], encoding="utf-8")
        return path
