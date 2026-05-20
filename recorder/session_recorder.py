"""Session recorder — captures Rich console output as SVG snapshots."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from rich.console import Console, RenderableType


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
        console: Optional[Console] = None,
    ):
        self.width = width
        self.height = height
        self.snapshot_interval = snapshot_interval
        self.max_frames = max_frames

        self._console: Optional[Console] = console
        self._external_console = console
        self._svg_frames: list[str] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._snapshot_thread: Optional[threading.Thread] = None
        self._recording = False
        self._renderable: Optional[RenderableType] = None

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

    def set_renderable(self, renderable: Optional[RenderableType]) -> None:
        """Set a live renderable to snapshot directly.

        When set, each snapshot renders this object into a fresh console
        instead of reading from the accumulated console buffer.
        Call with None to revert to normal console-based capture.
        """
        self._renderable = renderable

    def __enter__(self) -> "SessionRecorder":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        """Begin recording with periodic snapshots."""
        if self._external_console is not None:
            self._console = self._external_console
        else:
            self._console = Console(record=True, width=self.width)

        self._svg_frames = []
        self._stop_event.clear()
        self._recording = True

        try:
            self._console.export_text(clear=True)
        except Exception:
            pass

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
        self._snapshot_thread = None

        # Capture final state (dedup handled inside _take_snapshot)
        self._take_snapshot()

    def _snapshot_loop(self) -> None:
        """Background loop taking periodic SVG snapshots."""
        while not self._stop_event.is_set() and len(self._svg_frames) < self.max_frames:
            self._take_snapshot()
            self._stop_event.wait(self.snapshot_interval)

    def _take_snapshot(self) -> None:
        """Capture current console state as SVG."""
        try:
            renderable = self._renderable
            if renderable is not None:
                # Render the live object into a fresh console for a clean frame
                temp = Console(
                    record=True,
                    width=self.width,
                    height=self.height,
                    force_terminal=True,
                )
                temp.print(renderable)
                svg = temp.export_svg(title="Varedura")
            elif self._console is not None:
                svg = self._console.export_svg(title="Varedura", clear=False)
            else:
                return

            if not svg:
                return
            with self._lock:
                if len(self._svg_frames) >= self.max_frames:
                    return
                # Skip duplicate consecutive frames
                if self._svg_frames and svg == self._svg_frames[-1]:
                    return
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
