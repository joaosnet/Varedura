"""Spatial Anomaly and Geometric Event Rules Engine.

Implements real-time Line-Crossing (Tripwire), Zone Intrusion (Polygon Geofencing),
Loitering detection, and Motion Heatmap density accumulation.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from varedura.ai_vision.detector import Detection

_log = logging.getLogger("varedura.ai_rules")


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SpatialEvent:
    """Anomalous or triggered event produced by rule evaluation."""
    rule_id: str
    rule_name: str
    camera_id: str
    severity: EventSeverity
    message: str
    detection: Detection
    timestamp: float = field(default_factory=time.time)
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "camera_id": self.camera_id,
            "severity": self.severity.value,
            "message": self.message,
            "detection": self.detection.to_dict(),
            "timestamp": self.timestamp,
            "extra_data": self.extra_data,
        }


def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Check if three points A, B, C are in counter-clockwise order."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def segments_intersect(
    A: Tuple[float, float],
    B: Tuple[float, float],
    C: Tuple[float, float],
    D: Tuple[float, float],
) -> bool:
    """Return True if line segment AB intersects line segment CD."""
    return (ccw(A, C, D) != ccw(B, C, D)) and (ccw(A, B, C) != ccw(A, B, D))


def point_in_polygon(point: Tuple[float, float], polygon: Sequence[Tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test for normalized 2D coordinates."""
    if len(polygon) < 3:
        return False

    x, y = point
    inside = False
    n = len(polygon)

    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


class GeometricRule:
    """Base class for geometric anomaly rules."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        target_classes: Optional[Sequence[str]] = None,
        severity: EventSeverity = EventSeverity.WARNING,
    ) -> None:
        self.rule_id = rule_id
        self.name = name
        self.target_classes = set(target_classes) if target_classes else None
        self.severity = severity

    def evaluate(
        self,
        camera_id: str,
        detections: List[Detection],
        history: Dict[int, List[Tuple[float, float, float]]],
    ) -> List[SpatialEvent]:
        raise NotImplementedError


class LineCrossingRule(GeometricRule):
    """Detects objects crossing a virtual tripwire line segment."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        # Normalized coordinates (x, y) in [0, 1]
        line_start: Tuple[float, float],
        line_end: Tuple[float, float],
        target_classes: Optional[Sequence[str]] = None,
        severity: EventSeverity = EventSeverity.WARNING,
    ) -> None:
        super().__init__(rule_id, name, target_classes, severity)
        self.line_start = line_start
        self.line_end = line_end

    def evaluate(
        self,
        camera_id: str,
        detections: List[Detection],
        history: Dict[int, List[Tuple[float, float, float]]],
    ) -> List[SpatialEvent]:
        events: List[SpatialEvent] = []

        for det in detections:
            if self.target_classes and det.class_name not in self.target_classes:
                continue

            if det.track_id is None or det.track_id not in history:
                continue

            track_history = history[det.track_id]
            if len(track_history) < 2:
                continue

            # Check segment between previous centroid and current centroid
            p_prev = (track_history[-2][0], track_history[-2][1])
            p_curr = det.centroid

            if segments_intersect(p_prev, p_curr, self.line_start, self.line_end):
                events.append(
                    SpatialEvent(
                        rule_id=self.rule_id,
                        rule_name=self.name,
                        camera_id=camera_id,
                        severity=self.severity,
                        message=f"{det.class_name.capitalize()} crossed tripwire '{self.name}'",
                        detection=det,
                        extra_data={"line": [self.line_start, self.line_end]},
                    )
                )

        return events


class ZoneIntrusionRule(GeometricRule):
    """Detects objects entering or occupying a prohibited polygon zone."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        polygon: List[Tuple[float, float]],
        min_dwell_seconds: float = 0.5,
        target_classes: Optional[Sequence[str]] = None,
        severity: EventSeverity = EventSeverity.CRITICAL,
    ) -> None:
        super().__init__(rule_id, name, target_classes, severity)
        self.polygon = polygon
        self.min_dwell_seconds = min_dwell_seconds
        # track_id -> first entry timestamp
        self._zone_entry: Dict[int, float] = {}

    def evaluate(
        self,
        camera_id: str,
        detections: List[Detection],
        history: Dict[int, List[Tuple[float, float, float]]],
    ) -> List[SpatialEvent]:
        events: List[SpatialEvent] = []
        now = time.time()
        active_tracks = set()

        for det in detections:
            if self.target_classes and det.class_name not in self.target_classes:
                continue

            if point_in_polygon(det.centroid, self.polygon):
                track_id = det.track_id or -1
                active_tracks.add(track_id)

                if track_id not in self._zone_entry:
                    self._zone_entry[track_id] = now

                dwell = now - self._zone_entry[track_id]
                if dwell >= self.min_dwell_seconds:
                    events.append(
                        SpatialEvent(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            camera_id=camera_id,
                            severity=self.severity,
                            message=f"{det.class_name.capitalize()} in restricted zone '{self.name}' ({dwell:.1f}s)",
                            detection=det,
                            extra_data={"polygon": self.polygon, "dwell_seconds": dwell},
                        )
                    )

        # Cleanup stale tracks
        self._zone_entry = {
            tid: t for tid, t in self._zone_entry.items() if tid in active_tracks
        }

        return events


class LoiteringRule(GeometricRule):
    """Detects stationary or slowly wandering objects remaining in scene > threshold."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        max_dwell_seconds: float = 10.0,
        target_classes: Optional[Sequence[str]] = None,
        severity: EventSeverity = EventSeverity.WARNING,
    ) -> None:
        super().__init__(rule_id, name, target_classes, severity)
        self.max_dwell_seconds = max_dwell_seconds
        self._first_seen: Dict[int, float] = {}

    def evaluate(
        self,
        camera_id: str,
        detections: List[Detection],
        history: Dict[int, List[Tuple[float, float, float]]],
    ) -> List[SpatialEvent]:
        events: List[SpatialEvent] = []
        now = time.time()
        active_tracks = set()

        for det in detections:
            if self.target_classes and det.class_name not in self.target_classes:
                continue

            track_id = det.track_id or -1
            active_tracks.add(track_id)

            if track_id not in self._first_seen:
                self._first_seen[track_id] = now

            dwell = now - self._first_seen[track_id]
            if dwell >= self.max_dwell_seconds:
                events.append(
                    SpatialEvent(
                        rule_id=self.rule_id,
                        rule_name=self.name,
                        camera_id=camera_id,
                        severity=self.severity,
                        message=f"{det.class_name.capitalize()} loitering detected ({dwell:.1f}s)",
                        detection=det,
                        extra_data={"dwell_seconds": dwell},
                    )
                )

        self._first_seen = {
            tid: t for tid, t in self._first_seen.items() if tid in active_tracks
        }
        return events


class MotionHeatmap:
    """2D Spatial density accumulator with temporal decay."""

    def __init__(self, grid_size: int = 32, decay_rate: float = 0.98) -> None:
        self.grid_size = grid_size
        self.decay_rate = decay_rate
        self.grid: List[List[float]] = [[0.0] * grid_size for _ in range(grid_size)]
        self.total_points = 0

    def add_point(self, x: float, y: float, weight: float = 1.0) -> None:
        """Add normalized (x, y) point [0, 1] to heatmap grid."""
        gx = max(0, min(self.grid_size - 1, int(x * self.grid_size)))
        gy = max(0, min(self.grid_size - 1, int(y * self.grid_size)))
        self.grid[gy][gx] += weight
        self.total_points += 1

    def decay(self) -> None:
        """Apply exponential decay factor across entire grid."""
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                self.grid[r][c] *= self.decay_rate

    def get_normalized_matrix(self) -> List[List[float]]:
        """Return 2D grid matrix scaled [0.0, 1.0]."""
        max_val = max(max(row) for row in self.grid) if self.grid else 1.0
        if max_val <= 0.0:
            return [[0.0] * self.grid_size for _ in range(self.grid_size)]

        return [[round(cell / max_val, 3) for cell in row] for row in self.grid]
