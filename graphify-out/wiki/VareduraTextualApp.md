# VareduraTextualApp

> God node · 171 connections · `cli/textual_app.py`

**Community:** [Community 1](Community_1.md)

## Connections by Relation

### calls
- run_textual_app() `EXTRACTED`
- test_late_league_callback_cannot_reenable_disabled_detector() `EXTRACTED`
- test_shutdown_close_resources_terminates_players() `EXTRACTED`
- test_additional_targets_do_not_increment_gamification_counters() `EXTRACTED`
- test_callback_from_previous_network_run_is_discarded() `EXTRACTED`
- test_shutdown_stop_monitors_sets_events() `EXTRACTED`

### contains
- textual_app.py `EXTRACTED`

### imports
- test_textual_app.py `EXTRACTED`
- test_textual_cameras.py `EXTRACTED`

### inherits
- [CamerasMixin](CamerasMixin.md) `EXTRACTED`

### method
- .on_button_pressed() `EXTRACTED`
- ._start_network() `EXTRACTED`
- ._compose_dashboard() `EXTRACTED`
- ._on_targets_selected() `EXTRACTED`
- ._render_target_cards() `EXTRACTED`
- ._network_log() `EXTRACTED`
- ._render_ports_table() `EXTRACTED`
- ._reconfigure_ping_scheduler() `EXTRACTED`
- ._accept_ping_result() `EXTRACTED`
- ._render_ping_update() `EXTRACTED`
- ._refresh_status_renderables() `EXTRACTED`
- ._compose_settings() `EXTRACTED`
- ._finish_cleanup() `EXTRACTED`
- ._refresh_dashboard_status() `EXTRACTED`
- ._save_settings() `EXTRACTED`
- ._run_cleanup_worker() `EXTRACTED`
- ._render_network_tick() `EXTRACTED`
- ._record_and_check() `EXTRACTED`
- ._unlock_achievements() `EXTRACTED`
- ._compose_cleanup() `EXTRACTED`
- *…and 91 more `method` connection(s) not listed (lowest-degree first to go)*

### rationale_for
- Main Textual TUI for Varedura. `EXTRACTED`

### uses
- [PingTarget](PingTarget.md) `INFERRED`
- [PingScheduler](PingScheduler.md) `INFERRED`
- TargetSelection `INFERRED`
- RepairExecutor `INFERRED`
- TargetCategory `INFERRED`
- TargetPickerScreen `INFERRED`
- MascotRenderer `INFERRED`
- NetworkSessionHistory `INFERRED`
- LeagueMatchDetector `INFERRED`
- LeagueDetectorState `INFERRED`
- PingStatus `INFERRED`
- NetworkState `INFERRED`
- DailyLogWriter `INFERRED`
- DiagnosticOptions `INFERRED`
- test_speed_worker_is_prepared_before_schedule_and_can_cancel_immediately() `INFERRED`
- test_textual_cleanup_worker_uses_fake_cleaner() `INFERRED`
- test_textual_docker_reward_and_achievement() `INFERRED`
- ProbeKind `INFERRED`
- STATES `INFERRED`
- test_textual_ports_view_populates_in_network_tab() `INFERRED`
- *…and 29 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*