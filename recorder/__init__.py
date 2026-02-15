"""Recorder module for Varedura — terminal session recording to GIF."""

from recorder.session_recorder import SessionRecorder
from recorder.gif_generator import generate_gif

__all__ = ["SessionRecorder", "generate_gif"]
