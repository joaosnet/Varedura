# CameraSource

> God node · 33 connections · `varedura/camera_bridge.py`

**Community:** [Community 21](Community_21.md)

## Connections by Relation

### calls
- load_private_inventory() `EXTRACTED`
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg() `EXTRACTED`
- test_commands_are_processed_by_requested_at_not_uuid() `EXTRACTED`
- test_shutdown_in_once_mode_skips_all_snapshots() `EXTRACTED`
- test_capture_logs_only_sanitized_state_transitions() `EXTRACTED`
- test_clear_location_is_idempotent_and_keeps_camera_in_catalog() `EXTRACTED`
- test_command_idempotency_does_not_spawn_twice() `EXTRACTED`
- test_command_session_lifecycle_and_single_session_limit() `EXTRACTED`
- test_hls_h264_uses_remux_without_audio() `EXTRACTED`
- test_invalid_command_cannot_inject_url_or_escape_session_dir() `EXTRACTED`
- test_live_lock_rejects_second_bridge() `EXTRACTED`
- test_live_session_watchdog_stops_stalled_ffmpeg() `EXTRACTED`
- test_location_command_persists_privately_and_survives_restart() `EXTRACTED`
- test_rejected_start_still_publishes_terminal_session_state() `EXTRACTED`
- test_session_expires_and_cleans_hls_media() `EXTRACTED`
- test_shutdown_command_stops_ffmpeg_and_requests_clean_exit() `EXTRACTED`
- test_shutdown_tick_does_not_schedule_new_snapshots() `EXTRACTED`
- test_stale_start_command_is_rejected_without_spawning() `EXTRACTED`
- test_snapshot_is_published_atomically_with_subprocess_mock() `EXTRACTED`
- test_startup_recovery_failure_rolls_back_pid_and_lock() `EXTRACTED`
- *…and 5 more `calls` connection(s) not listed (lowest-degree first to go)*

### contains
- camera_bridge.py `EXTRACTED`

### imports
- test_camera_bridge.py `EXTRACTED`

### method
- .public_dict() `EXTRACTED`

### rationale_for
- Fonte privada mais estado público de uma câmera conhecida. `EXTRACTED`

### references
- .capture_snapshot() `EXTRACTED`
- ._apply_capture() `EXTRACTED`
- .start_hls() `EXTRACTED`

### uses
- make_bridge() `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*