"""Unit and integration tests for Edge AI Video Analytics Pipeline."""

import time
import pytest

from varedura.ai_vision.detector import (
    Detection,
    YOLONanoDetector,
    compute_iou,
    nms,
)
from varedura.ai_vision.rules import (
    EventSeverity,
    LineCrossingRule,
    LoiteringRule,
    MotionHeatmap,
    SpatialEvent,
    ZoneIntrusionRule,
    ccw,
    point_in_polygon,
    segments_intersect,
)
from varedura.ai_vision.stream_processor import AIStreamProcessor


def test_iou_calculation():
    b1 = [0.0, 0.0, 1.0, 1.0]
    b2 = [0.0, 0.0, 1.0, 1.0]
    assert compute_iou(b1, b2) == 1.0

    b3 = [0.5, 0.5, 1.5, 1.5]
    iou = compute_iou(b1, b3)
    assert 0.14 < iou < 0.15

    b4 = [2.0, 2.0, 3.0, 3.0]
    assert compute_iou(b1, b4) == 0.0


def test_nms_suppression():
    d1 = Detection(class_id=0, class_name="person", confidence=0.9, bbox=(0.1, 0.1, 0.5, 0.5))
    d2 = Detection(class_id=0, class_name="person", confidence=0.8, bbox=(0.12, 0.12, 0.52, 0.52))
    d3 = Detection(class_id=2, class_name="car", confidence=0.85, bbox=(0.6, 0.6, 0.9, 0.9))

    kept = nms([d1, d2, d3], iou_threshold=0.45)
    assert len(kept) == 2
    assert d1 in kept
    assert d3 in kept
    assert d2 not in kept


def test_geometric_line_intersection():
    # Perpendicular intersecting segments
    A = (0.0, 0.5)
    B = (1.0, 0.5)
    C = (0.5, 0.0)
    D = (0.5, 1.0)
    assert segments_intersect(A, B, C, D) is True

    # Parallel non-intersecting segments
    E = (0.0, 0.2)
    F = (1.0, 0.2)
    assert segments_intersect(A, B, E, F) is False


def test_point_in_polygon():
    polygon = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
    assert point_in_polygon((0.5, 0.5), polygon) is True
    assert point_in_polygon((0.1, 0.1), polygon) is False
    assert point_in_polygon((0.9, 0.9), polygon) is False


def test_line_crossing_rule():
    rule = LineCrossingRule(
        rule_id="rule_tripwire_1",
        name="Front Gate Line",
        line_start=(0.0, 0.5),
        line_end=(1.0, 0.5),
        target_classes=["person"],
    )

    det = Detection(
        class_id=0,
        class_name="person",
        confidence=0.95,
        bbox=(0.4, 0.55, 0.6, 0.75),  # centroid at (0.5, 0.65)
        track_id=1,
    )

    # History where track moved from (0.5, 0.3) -> (0.5, 0.65)
    history = {1: [(0.5, 0.3, time.time() - 0.2), (0.5, 0.65, time.time())]}

    events = rule.evaluate(camera_id="cam_01", detections=[det], history=history)
    assert len(events) == 1
    assert events[0].rule_id == "rule_tripwire_1"
    assert events[0].severity == EventSeverity.WARNING


def test_zone_intrusion_rule():
    polygon = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
    rule = ZoneIntrusionRule(
        rule_id="rule_zone_1",
        name="Restricted Yard",
        polygon=polygon,
        min_dwell_seconds=0.0,  # immediate trigger
        target_classes=["person", "car"],
    )

    det_inside = Detection(
        class_id=0,
        class_name="person",
        confidence=0.9,
        bbox=(0.4, 0.4, 0.6, 0.6),  # centroid at (0.5, 0.5)
        track_id=2,
    )

    events = rule.evaluate(camera_id="cam_01", detections=[det_inside], history={})
    assert len(events) == 1
    assert events[0].rule_id == "rule_zone_1"
    assert events[0].severity == EventSeverity.CRITICAL


def test_motion_heatmap():
    hm = MotionHeatmap(grid_size=16, decay_rate=0.5)
    hm.add_point(0.5, 0.5, weight=2.0)
    matrix1 = hm.get_normalized_matrix()
    assert matrix1[8][8] == 1.0

    hm.decay()
    matrix2 = hm.get_normalized_matrix()
    assert matrix2[8][8] == 1.0  # normalized max is still 1.0 if only 1 point


def test_stream_processor_pipeline():
    processor = AIStreamProcessor(camera_id="cam_garage")
    rule = ZoneIntrusionRule(
        rule_id="rule_garage",
        name="Garage Floor",
        polygon=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        min_dwell_seconds=0.0,
    )
    processor.add_rule(rule)

    recorded_events = []
    processor.add_event_listener(recorded_events.append)

    # Mock frame bytes
    fake_frame = b"\xff\xd8\xff\xe0...fake_jpeg"
    dets, events = processor.process_frame(fake_frame)

    summary = processor.get_status_summary()
    assert summary["camera_id"] == "cam_garage"
    assert summary["rules_count"] == 1
    assert "heatmap" in summary
