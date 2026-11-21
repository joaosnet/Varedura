"""Pure connection health score calculation extracted from legacy gamification."""

from __future__ import annotations

import statistics
from typing import Optional, Sequence

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

    score = int(
        round(
            0.40 * latency + 0.20 * jitter_score + 0.30 * loss_score + 0.10 * compliance
        )
    )
    score = int(_clamp(score))

    for minimum, tier, color in _TIERS:
        if score >= minimum:
            return score, tier, color
    return score, "F", "red"


__all__ = ["compute_health_score"]
