"""Rendering utilities for the Varedura mascot."""

from __future__ import annotations

import itertools
import time
import threading
from typing import Optional

from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from mascot.frames import FRAMES, COMPACT, STATES


class MascotRenderer:
    """Renders the Varedura mascot in various states with optional speech bubbles."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._stop_event = threading.Event()
        self._animation_thread: Optional[threading.Thread] = None

    # ── Static rendering ────────────────────────────────────────────

    def render_static(self, state: str = STATES.IDLE, message: str = "") -> Panel:
        """Return a Rich Panel with the mascot in the given state."""
        frames = FRAMES.get(state, FRAMES[STATES.IDLE])
        frame_style, border_style, title_style = self._panel_styles(state)
        frame_text = Text(frames[0], style=frame_style)

        content_parts = [frame_text]
        if message:
            bubble = self._speech_bubble(message, state)
            content_parts.append(Text("\n"))
            content_parts.append(bubble)

        group = Text()
        for part in content_parts:
            group.append_text(part)

        return Panel(
            Align.center(group),
            border_style=border_style,
            title=f"[{title_style}]✦ Varedura[/]",
            padding=(0, 1),
        )

    def render_inline(self, state: str = STATES.IDLE) -> str:
        """Return a compact single-line mascot string for inline use."""
        frames = COMPACT.get(state, COMPACT[STATES.IDLE])
        if isinstance(frames, list):
            return frames[0]
        return frames

    def get_mascot_and_content(self, state: str, message: str, content) -> Columns:
        """Return mascot alongside other Rich content (for menu layout)."""
        mascot_panel = self.render_static(state, message)
        return Columns([mascot_panel, content], expand=True, padding=(0, 2))

    # ── Speech bubble ───────────────────────────────────────────────

    @staticmethod
    def _speech_bubble(message: str, state: str = STATES.IDLE) -> Text:
        """Create a speech bubble around the message."""
        lines = message.split("\n")
        max_len = max(len(line) for line in lines)
        width = max_len + 2
        bubble_style = "dim white"
        if state == STATES.WORKING:
            bubble_style = "bright_cyan"
        elif state == STATES.SUCCESS:
            bubble_style = "bright_green"
        elif state == STATES.ERROR:
            bubble_style = "bright_red"

        parts = []
        parts.append(f"  ╭{'─' * width}╮\n")
        for line in lines:
            parts.append(f"  │ {line:<{max_len}} │\n")
        parts.append(f"  ╰{'─' * width}╯\n")
        parts.append("     ╲")

        bubble_text = Text("".join(parts), style=bubble_style)
        return bubble_text

    @staticmethod
    def _panel_styles(state: str) -> tuple[str, str, str]:
        """Return frame, border and title style for each mascot state."""
        if state == STATES.WORKING:
            return ("bold bright_cyan", "bright_cyan", "bold bright_cyan")
        if state == STATES.SUCCESS:
            return ("bold bright_green", "green", "bold bright_green")
        if state == STATES.ERROR:
            return ("bold bright_red", "red", "bold bright_red")
        if state == STATES.WAVE:
            return ("bold magenta", "magenta", "bold magenta")
        return ("bold cyan", "cyan", "bold cyan")

    # ── Animated rendering (blocking with Live) ─────────────────────

    def animate(
        self,
        state: str = STATES.WORKING,
        message: str = "",
        duration: float = 0.0,
        fps: float = 2.0,
    ) -> None:
        """Show animated mascot using Rich Live (blocking).

        Args:
            state: Animation state to display.
            message: Speech bubble text.
            duration: How long to animate (0 = until stopped externally).
            fps: Frames per second.
        """
        frames = FRAMES.get(state, FRAMES[STATES.IDLE])
        frame_cycle = itertools.cycle(frames)
        interval = 1.0 / fps

        self._stop_event.clear()
        start = time.time()

        with Live(console=self.console, refresh_per_second=fps) as live:
            while not self._stop_event.is_set():
                frame = next(frame_cycle)
                frame_style, border_style, title_style = self._panel_styles(state)
                frame_text = Text(frame, style=frame_style)

                if message:
                    bubble = self._speech_bubble(message, state)
                    group = Text()
                    group.append_text(frame_text)
                    group.append_text(Text("\n"))
                    group.append_text(bubble)
                else:
                    group = frame_text

                panel = Panel(
                    Align.center(group),
                    border_style=border_style,
                    title=f"[{title_style}]✦ Varedura[/]",
                    padding=(0, 1),
                )
                live.update(panel)

                if duration > 0 and (time.time() - start) >= duration:
                    break

                self._stop_event.wait(interval)

    def stop(self) -> None:
        """Signal the animation loop to stop."""
        self._stop_event.set()

    # ── Background animation (non-blocking) ─────────────────────────

    def start_background(
        self,
        state: str = STATES.WORKING,
        message: str = "",
        fps: float = 2.0,
    ) -> None:
        """Start mascot animation in a background thread."""
        self.stop()
        if self._animation_thread and self._animation_thread.is_alive():
            self._animation_thread.join(timeout=1.0)

        self._stop_event.clear()
        self._animation_thread = threading.Thread(
            target=self.animate,
            args=(state, message, 0.0, fps),
            daemon=True,
        )
        self._animation_thread.start()

    def stop_background(self) -> None:
        """Stop background mascot animation."""
        self.stop()
        if self._animation_thread and self._animation_thread.is_alive():
            self._animation_thread.join(timeout=2.0)
        self._animation_thread = None

    # ── Convenience: show result ────────────────────────────────────

    def show_result(self, success: bool, message: str = "") -> None:
        """Display success or error mascot frame."""
        state = STATES.SUCCESS if success else STATES.ERROR
        panel = self.render_static(state, message)
        self.console.print(panel)

    def show_wave(self, message: str = "") -> None:
        """Display the wave/goodbye mascot."""
        panel = self.render_static(STATES.WAVE, message)
        self.console.print(panel)
