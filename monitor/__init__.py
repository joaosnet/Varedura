"""Monitor module - Real-time system monitoring tools."""

from monitor.stalker import main as run_stalker
from monitor.stalker import StalkerConfig

__all__ = ["run_stalker", "StalkerConfig"]
