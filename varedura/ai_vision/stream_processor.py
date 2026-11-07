"""Asynchronous Stream Processor connecting Camera Feeds, AI Analytics & Anomaly Rules."""

from __future__ import annotations

import collections
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from varedura.ai_vision.detector import Detection, ObjectDetector, YOLONanoDetector
from varedura.ai_vision.rules import (
    GeometricRule,
    LineCrossingRule,
    MotionHeatmap,
    SpatialEvent,
    ZoneIntrusionRule,
)

_log = logging.getLogger("varedura.ai_processor")


@dataclass
class VideoFrame:
    """Represents a frame captured from camera stream."""
    camera_id: str
    data: bytes
    timestamp: float = field(default_factory=time.time)
    width: int = 1920
    height: int = 1080


class AIStreamProcessor:
    """Continuously processes frames from a camera, runs AI, checks anomaly rules."""

    def __init__(
        self,
        camera_id: str,
        detector: Optional[ObjectDetector] = None,
        max_fps: float = 10.0,
        pre_buffer_frames: int = 30,
    ) -> None:
        self.camera_id = camera_id
        self.detector = detector or YOLONanoDetector()
        self.max_fps = max_fps
        self.frame_interval = 1.0 / max(1.0, max_fps)

        self._rules: List[GeometricRule] = []
        self._heatmap = MotionHeatmap(grid_size=32)
        # track_id -> [(cx, cy, timestamp), ...]
        self._history: Dict[int, List[Tuple[float, float, float]]] = collections.defaultdict(list)
        self._pre_buffer: collections.deque[VideoFrame] = collections.deque(maxlen=pre_buffer_frames)
        self._recent_events: collections.deque[SpatialEvent] = collections.deque(maxlen=100)
        self._active_detections: List[Detection] = []

        self._lock = threading.RLock()
        self._last_process_time = 0.0
        self._event_listeners: List[Callable[[SpatialEvent], None]] = []

    def add_rule(self, rule: GeometricRule) -> None:
        """Register a spatial anomaly rule (tripwire, geofence, etc)."""
        with self._lock:
            self._rules.append(rule)

    def add_event_listener(self, callback: Callable[[SpatialEvent], None]) -> None:
        with self._lock:
            self._event_listeners.append(callback)

    def process_frame(self, frame_bytes: bytes) -> Tuple[List[Detection], List[SpatialEvent]]:
        """Process single video frame bytes, evaluate AI and rules."""
        now = time.time()
        if now - self._last_process_time < self.frame_interval:
            return self._active_detections, []

        self._last_process_time = now

        # 1. Run Object Detector
        detections = self.detector.detect(frame_bytes)

        # 2. Update tracking history and motion heatmap
        with self._lock:
            self._active_detections = detections
            self._pre_buffer.append(VideoFrame(camera_id=self.camera_id, data=frame_bytes, timestamp=now))
            self._heatmap.decay()

            current_track_ids = set()
            for det in detections:
                if det.track_id is not None:
                    current_track_ids.add(det.track_id)
                    cx, cy = det.centroid
                    self._history[det.track_id].append((cx, cy, now))
                    if len(self._history[det.track_id]) > 30:
                        self._history[det.track_id].pop(0)

                    # Update Heatmap
                    self._heatmap.add_point(cx, cy, weight=1.0)

            # Cleanup expired tracks
            stale_tracks = [
                tid for tid, hist in self._history.items()
                if tid not in current_track_ids and (now - hist[-1][2]) > 5.0
            ]
            for tid in stale_tracks:
                del self._history[tid]

            # 3. Evaluate anomaly rules
            new_events: List[SpatialEvent] = []
            for rule in self._rules:
                triggered = rule.evaluate(
                    camera_id=self.camera_id,
                    detections=detections,
                    history=self._history,
                )
                for ev in triggered:
                    new_events.append(ev)
                    self._recent_events.append(ev)

            # 4. Notify listeners
            for ev in new_events:
                for cb in self._event_listeners:
                    try:
                        cb(ev)
                    except Exception as exc:
                        _log.debug("Event callback exception: %s", exc)

            return detections, new_events

    def get_status_summary(self) -> Dict[str, Any]:
        """Export real-time AI status for bridge and frontend catalog."""
        with self._lock:
            return {
                "camera_id": self.camera_id,
                "active_detections": [d.to_dict() for d in self._active_detections],
                "active_detection_count": len(self._active_detections),
                "recent_event_count": len(self._recent_events),
                "recent_events": [e.to_dict() for e in list(self._recent_events)[-10:]],
                "heatmap_points": self._heatmap.total_points,
                "heatmap": self._heatmap.get_normalized_matrix(),
                "rules_count": len(self._rules),
            }
