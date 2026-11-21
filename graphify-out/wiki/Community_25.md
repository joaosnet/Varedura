# Community 25

> 35 nodes · cohesion 0.09

## Key Concepts

- **AIStreamProcessor** (19 connections) — `varedura/ai_vision/stream_processor.py`
- **YOLONanoDetector** (12 connections) — `varedura/ai_vision/detector.py`
- **MotionHeatmap** (12 connections) — `varedura/ai_vision/rules.py`
- **VareduraDaemonState** (11 connections) — `varedura/daemon_api.py`
- **ObjectDetector** (8 connections) — `varedura/ai_vision/detector.py`
- **.process_frame()** (8 connections) — `varedura/ai_vision/stream_processor.py`
- **test_stream_processor_pipeline()** (7 connections) — `tests/test_ai_vision.py`
- **.get_or_create_processor()** (6 connections) — `varedura/daemon_api.py`
- **test_motion_heatmap()** (5 connections) — `tests/test_ai_vision.py`
- **.add_rule()** (5 connections) — `varedura/ai_vision/stream_processor.py`
- **.get_status_summary()** (5 connections) — `varedura/ai_vision/stream_processor.py`
- **.add_point()** (4 connections) — `varedura/ai_vision/rules.py`
- **.decay()** (4 connections) — `varedura/ai_vision/rules.py`
- **.get_normalized_matrix()** (4 connections) — `varedura/ai_vision/rules.py`
- **.__init__()** (4 connections) — `varedura/ai_vision/stream_processor.py`
- **._init_default_cameras()** (4 connections) — `varedura/daemon_api.py`
- **.add_event_listener()** (3 connections) — `varedura/ai_vision/stream_processor.py`
- **VideoFrame** (3 connections) — `varedura/ai_vision/stream_processor.py`
- **.__init__()** (3 connections) — `varedura/daemon_api.py`
- **.__init__()** (2 connections) — `varedura/ai_vision/detector.py`
- **Path** (1 connections)
- **Base interface for object detection inference.** (1 connections) — `varedura/ai_vision/detector.py`
- **Production YOLOv8/v11 nano ONNX Runtime detector with high-speed fallback.** (1 connections) — `varedura/ai_vision/detector.py`
- **.__init__()** (1 connections) — `varedura/ai_vision/rules.py`
- **2D Spatial density accumulator with temporal decay.** (1 connections) — `varedura/ai_vision/rules.py`
- *... and 10 more nodes in this community*

## Relationships

- [Community 4](Community_4.md) (22 shared connections)
- [Community 15](Community_15.md) (11 shared connections)
- [Community 73](Community_73.md) (3 shared connections)
- [Community 79](Community_79.md) (3 shared connections)
- [Community 7](Community_7.md) (1 shared connections)

## Source Files

- `tests/test_ai_vision.py`
- `varedura/ai_vision/detector.py`
- `varedura/ai_vision/rules.py`
- `varedura/ai_vision/stream_processor.py`
- `varedura/daemon_api.py`

## Audit Trail

- EXTRACTED: 69 (75%)
- INFERRED: 23 (25%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*