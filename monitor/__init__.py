"""Real-time monitoring tools with lazy public exports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from monitor.stalker import StalkerConfig

__all__ = ["run_stalker", "StalkerConfig"]


def __getattr__(name: str) -> Any:
    """Preserve the historical API without importing the full monitor eagerly."""
    if name == "run_stalker":
        from monitor.stalker import main

        return main
    if name == "StalkerConfig":
        from monitor.stalker import StalkerConfig

        return StalkerConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
