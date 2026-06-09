"""Subtle gamification core for Varedura: health score, records, achievements.

Pure logic + persistence only (no Textual / Rich here) so it stays testable.
State is persisted in the shared prefs file under the ``"game"`` key. Persistence
helpers import ``cli.ui_shared`` lazily to avoid an import cycle (ui_shared builds
Rich widgets from this module).
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from typing import Optional, Sequence

# ── Health score ────────────────────────────────────────────────────────────

# Named tiers, evaluated high -> low. (min_score, tier, color)
_TIERS: list[tuple[int, str, str]] = [
    (90, "S", "green"),
    (75, "A", "cyan"),
    (55, "B", "yellow"),
    (35, "C", "orange1"),
    (0, "F", "red"),
]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def compute_health_score(
    local_hist: Sequence[Optional[float]],
    ext_hist: Sequence[Optional[float]],
    threshold: int,
    speed_compliant: Optional[bool] = None,
    window: int = 20,
) -> tuple[int, str, str]:
    """Compute a 0-100 connection health score from recent ping history.

    Uses the external (internet) history when available, falling back to the
    local gateway history. Returns ``(score, tier, color)``. With no samples
    yet, returns ``(0, "—", "dim")``.
    """
    samples = list(ext_hist)[-window:] or list(local_hist)[-window:]
    if not samples:
        return 0, "—", "dim"

    valid = [v for v in samples if v is not None]
    loss_frac = (len(samples) - len(valid)) / len(samples)

    if not valid:
        # Everything timed out in the window -> critical but not "no data".
        return 0, "F", "red"

    avg = statistics.fmean(valid)
    jitter = statistics.pstdev(valid) if len(valid) > 1 else 0.0
    thr = max(1, threshold)

    # Latency: full marks at <= 0.5x threshold, zero at >= 3x threshold.
    latency = _clamp(100 * (1 - (avg - thr * 0.5) / (thr * 2.5)))
    # Jitter: full marks at 0, zero once stdev reaches the threshold.
    jitter_score = _clamp(100 * (1 - jitter / thr))
    loss_score = 100 * (1 - loss_frac)
    if speed_compliant is True:
        compliance = 100.0
    elif speed_compliant is False:
        compliance = 0.0
    else:
        compliance = 50.0  # unknown -> neutral, do not punish

    score = int(round(0.40 * latency + 0.20 * jitter_score + 0.30 * loss_score + 0.10 * compliance))
    score = int(_clamp(score))

    for minimum, tier, color in _TIERS:
        if score >= minimum:
            return score, tier, color
    return score, "F", "red"


# ── Streak ──────────────────────────────────────────────────────────────────


@dataclass
class StreakTracker:
    """Runtime tracker of consecutive lag-free seconds."""

    seconds: float = 0.0

    def update(self, ok: bool, interval: float) -> float:
        """Advance the streak. ``ok`` means ping <= threshold and not lost."""
        self.seconds = self.seconds + interval if ok else 0.0
        return self.seconds


# ── Persisted game state ─────────────────────────────────────────────────────


@dataclass
class GameState:
    best_ping: Optional[float] = None  # lowest ms seen
    best_download: float = 0.0  # highest Mbps seen
    best_streak_s: float = 0.0
    total_pings: int = 0
    total_monitor_s: float = 0.0
    total_space_freed_gb: float = 0.0
    cleanups_run: int = 0
    reports_exported: int = 0
    anatel_ever: bool = False
    achievements: set[str] = field(default_factory=set)


def load_game_state() -> GameState:
    """Load the persisted game state from the shared prefs file."""
    from cli.ui_shared import load_prefs

    raw = load_prefs().get("game", {})
    if not isinstance(raw, dict):
        raw = {}
    state = GameState()
    for key, value in raw.items():
        if key == "achievements" and isinstance(value, list):
            state.achievements = set(value)
        elif hasattr(state, key) and key != "achievements":
            setattr(state, key, value)
    return state


def save_game_state(state: GameState) -> None:
    """Persist the game state into the shared prefs file."""
    from cli.ui_shared import load_prefs, save_prefs

    data = load_prefs()
    payload = asdict(state)
    payload["achievements"] = sorted(state.achievements)
    data["game"] = payload
    save_prefs(data)


def update_records(
    state: GameState,
    *,
    ping: Optional[float] = None,
    download: Optional[float] = None,
    streak_s: Optional[float] = None,
    pings: int = 0,
    monitor_s: float = 0.0,
    space_freed_gb: float = 0.0,
    cleanups: int = 0,
    reports: int = 0,
    anatel: bool = False,
) -> GameState:
    """Merge new metrics into the state, keeping bests and accumulating totals."""
    if ping is not None and ping > 0:
        state.best_ping = ping if state.best_ping is None else min(state.best_ping, ping)
    if download is not None and download > 0:
        state.best_download = max(state.best_download, download)
    if streak_s is not None:
        state.best_streak_s = max(state.best_streak_s, streak_s)
    state.total_pings += pings
    state.total_monitor_s += monitor_s
    state.total_space_freed_gb += space_freed_gb
    state.cleanups_run += cleanups
    state.reports_exported += reports
    if anatel:
        state.anatel_ever = True
    return state


# ── Achievements ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Achievement:
    id: str
    name_key: str
    desc_key: str
    emoji: str
    predicate: "object"  # Callable[[GameState], bool]


ACHIEVEMENTS: list[Achievement] = [
    Achievement("sub20", "game.ach_sub20", "game.ach_sub20_desc", "🚀",
                lambda s: s.best_ping is not None and s.best_ping <= 20),
    Achievement("anatel", "game.ach_anatel", "game.ach_anatel_desc", "📜",
                lambda s: s.anatel_ever),
    Achievement("streak1h", "game.ach_streak1h", "game.ach_streak1h_desc", "⏱",
                lambda s: s.best_streak_s >= 3600),
    Achievement("pings1k", "game.ach_pings1k", "game.ach_pings1k_desc", "🎯",
                lambda s: s.total_pings >= 1000),
    Achievement("first_report", "game.ach_report", "game.ach_report_desc", "📄",
                lambda s: s.reports_exported >= 1),
    Achievement("docker_first", "game.ach_docker_first", "game.ach_docker_first_desc", "🧹",
                lambda s: s.cleanups_run >= 1),
    Achievement("docker5gb", "game.ach_docker5gb", "game.ach_docker5gb_desc", "💾",
                lambda s: s.total_space_freed_gb >= 5),
]


def check_achievements(state: GameState) -> list[str]:
    """Return newly unlocked achievement ids, recording them on the state."""
    unlocked: list[str] = []
    for ach in ACHIEVEMENTS:
        if ach.id in state.achievements:
            continue
        try:
            if ach.predicate(state):
                state.achievements.add(ach.id)
                unlocked.append(ach.id)
        except Exception:
            continue
    return unlocked


def achievement_by_id(ach_id: str) -> Optional[Achievement]:
    for ach in ACHIEVEMENTS:
        if ach.id == ach_id:
            return ach
    return None
