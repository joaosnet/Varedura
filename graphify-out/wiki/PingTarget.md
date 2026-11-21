# PingTarget

> God node · 45 connections · `monitor/ping_targets.py`

**Community:** [Community 36](Community_36.md)

## Connections by Relation

### calls
- [main()](main.md) `EXTRACTED`
- .from_config() `EXTRACTED`
- ._start_network() `EXTRACTED`
- create_custom_target() `EXTRACTED`
- test_reconfigure_discards_old_generation_result() `EXTRACTED`
- test_route_loss_still_allows_explicit_private_institutional_target() `EXTRACTED`
- test_reconfigure_never_overlaps_old_and_new_probe_for_same_target_id() `EXTRACTED`
- ._reconfigure_ping_scheduler() `EXTRACTED`
- test_csv_rows_are_contiguous_by_target_generation() `EXTRACTED`
- test_history_groups_targets_generations_and_sessions() `EXTRACTED`
- test_league_exports_mask_ips_by_default() `EXTRACTED`
- test_pdf_export_keeps_target_blocks_separate() `EXTRACTED`
- test_target_card_statistics_include_jitter_trend_and_live_league_ip() `EXTRACTED`
- _gateway() `EXTRACTED`
- _league() `EXTRACTED`
- test_selection_enforces_five_persistent_and_primary() `EXTRACTED`

### contains
- ping_targets.py `EXTRACTED`

### imports
- textual_app.py `EXTRACTED`
- stalker.py `EXTRACTED`
- test_textual_app.py `EXTRACTED`
- league_detector.py `EXTRACTED`
- test_ping_scheduler.py `EXTRACTED`
- ping_scheduler.py `EXTRACTED`
- network_history.py `EXTRACTED`
- network_ui.py `EXTRACTED`
- test_network_history.py `EXTRACTED`

### method
- .__post_init__() `EXTRACTED`

### rationale_for
- A named ICMP destination. ``ephemeral`` targets (the gateway and the current… `EXTRACTED`

### references
- probe_ping() `EXTRACTED`
- .configure() `EXTRACTED`
- target_catalog() `EXTRACTED`
- .add_result() `EXTRACTED`
- target_by_id() `EXTRACTED`
- ._option_label() `EXTRACTED`
- ._run_probe() `EXTRACTED`
- .to_ping_target() `EXTRACTED`
- .primary_target() `EXTRACTED`

### uses
- [VareduraTextualApp](VareduraTextualApp.md) `INFERRED`
- [PingScheduler](PingScheduler.md) `INFERRED`
- TargetPickerScreen `INFERRED`
- NetworkSessionHistory `INFERRED`
- LeagueEndpoint `INFERRED`
- _result() `INFERRED`
- _TargetState `INFERRED`
- SchedulerTargetSnapshot `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*