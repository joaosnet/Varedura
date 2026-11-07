"""Edge AI Video Analytics & Anomaly Detection Pipeline for Varedura."""

from varedura.ai_vision.detector import Detection, ObjectDetector, YOLONanoDetector
from varedura.ai_vision.rules import (
    EventSeverity,
    GeometricRule,
    LineCrossingRule,
    LoiteringRule,
    MotionHeatmap,
    SpatialEvent,
    ZoneIntrusionRule,
)
from varedura.ai_vision.stream_processor import AIStreamProcessor

__all__ = [
    "Detection",
    "ObjectDetector",
    "YOLONanoDetector",
    "GeometricRule",
    "LineCrossingRule",
    "ZoneIntrusionRule",
    "LoiteringRule",
    "MotionHeatmap",
    "SpatialEvent",
    "EventSeverity",
    "AIStreamProcessor",
]
