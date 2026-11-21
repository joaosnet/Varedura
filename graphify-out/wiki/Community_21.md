# Community 21

> 38 nodes · cohesion 0.22

## Key Concepts

- **test_camera_bridge.py** (62 connections) — `tests/test_camera_bridge.py`
- **CameraSource** (33 connections) — `varedura/camera_bridge.py`
- **make_bridge()** (28 connections) — `tests/test_camera_bridge.py`
- **new_id()** (28 connections) — `tests/test_camera_bridge.py`
- **shutdown_executor()** (24 connections) — `tests/test_camera_bridge.py`
- **command()** (17 connections) — `tests/test_camera_bridge.py`
- **put_command()** (17 connections) — `tests/test_camera_bridge.py`
- **test_commands_are_processed_by_requested_at_not_uuid()** (8 connections) — `tests/test_camera_bridge.py`
- **test_shutdown_in_once_mode_skips_all_snapshots()** (8 connections) — `tests/test_camera_bridge.py`
- **test_capture_logs_only_sanitized_state_transitions()** (7 connections) — `tests/test_camera_bridge.py`
- **test_clear_location_is_idempotent_and_keeps_camera_in_catalog()** (7 connections) — `tests/test_camera_bridge.py`
- **test_command_idempotency_does_not_spawn_twice()** (7 connections) — `tests/test_camera_bridge.py`
- **test_command_session_lifecycle_and_single_session_limit()** (7 connections) — `tests/test_camera_bridge.py`
- **test_invalid_command_cannot_inject_url_or_escape_session_dir()** (7 connections) — `tests/test_camera_bridge.py`
- **test_live_lock_rejects_second_bridge()** (7 connections) — `tests/test_camera_bridge.py`
- **test_live_session_watchdog_stops_stalled_ffmpeg()** (7 connections) — `tests/test_camera_bridge.py`
- **test_location_command_persists_privately_and_survives_restart()** (7 connections) — `tests/test_camera_bridge.py`
- **test_rejected_start_still_publishes_terminal_session_state()** (7 connections) — `tests/test_camera_bridge.py`
- **test_session_expires_and_cleans_hls_media()** (7 connections) — `tests/test_camera_bridge.py`
- **test_shutdown_command_stops_ffmpeg_and_requests_clean_exit()** (7 connections) — `tests/test_camera_bridge.py`
- **test_shutdown_tick_does_not_schedule_new_snapshots()** (7 connections) — `tests/test_camera_bridge.py`
- **test_stale_start_command_is_rejected_without_spawning()** (7 connections) — `tests/test_camera_bridge.py`
- **test_set_location_rejects_invalid_or_free_text_payload()** (6 connections) — `tests/test_camera_bridge.py`
- **test_snapshot_is_published_atomically_with_subprocess_mock()** (6 connections) — `tests/test_camera_bridge.py`
- **test_startup_recovery_failure_rolls_back_pid_and_lock()** (6 connections) — `tests/test_camera_bridge.py`
- *... and 13 more nodes in this community*

## Relationships

- [Community 37](Community_37.md) (16 shared connections)
- [Community 5](Community_5.md) (14 shared connections)
- [Community 34](Community_34.md) (6 shared connections)
- [Community 61](Community_61.md) (5 shared connections)
- [Community 15](Community_15.md) (5 shared connections)
- [Community 92](Community_92.md) (5 shared connections)
- [Community 53](Community_53.md) (4 shared connections)
- [Community 2](Community_2.md) (2 shared connections)
- [Community 111](Community_111.md) (2 shared connections)
- [Community 54](Community_54.md) (2 shared connections)
- [Community 33](Community_33.md) (1 shared connections)
- [Community 99](Community_99.md) (1 shared connections)

## Source Files

- `tests/test_camera_bridge.py`
- `varedura/camera_bridge.py`

## Audit Trail

- EXTRACTED: 202 (93%)
- INFERRED: 16 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*