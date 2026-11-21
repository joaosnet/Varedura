# PingScheduler

> God node · 38 connections · `monitor/ping_scheduler.py`

**Community:** [Community 8](Community_8.md)

## Connections by Relation

### calls
- [main()](main.md) `EXTRACTED`
- ._start_network() `EXTRACTED`
- test_scheduler_limits_concurrency_and_staggers_secondaries() `EXTRACTED`
- test_reconfigure_discards_old_generation_result() `EXTRACTED`
- test_primary_failure_backoff_is_monotonic_and_bounded() `EXTRACTED`
- test_route_loss_still_allows_explicit_private_institutional_target() `EXTRACTED`
- test_route_loss_suspends_external_but_not_gateway() `EXTRACTED`
- test_three_failures_with_working_https_mark_icmp_filtered() `EXTRACTED`
- test_non_icmp_failure_is_never_relabelled_as_filtered() `EXTRACTED`
- test_reconfigure_never_overlaps_old_and_new_probe_for_same_target_id() `EXTRACTED`

### contains
- ping_scheduler.py `EXTRACTED`

### imports
- textual_app.py `EXTRACTED`
- stalker.py `EXTRACTED`
- test_ping_scheduler.py `EXTRACTED`

### method
- .poll() `EXTRACTED`
- .configure() `EXTRACTED`
- .stop() `EXTRACTED`
- .snapshot() `EXTRACTED`
- .set_route_available() `EXTRACTED`
- ._apply_result_locked() `EXTRACTED`
- ._requires_default_route() `EXTRACTED`
- .set_alternative_connectivity_healthy() `EXTRACTED`
- ._run_probe() `EXTRACTED`
- ._base_interval() `EXTRACTED`
- .in_flight_count() `EXTRACTED`
- .__init__() `EXTRACTED`
- .start() `EXTRACTED`
- ._invalidate_locked() `EXTRACTED`
- .next_wake_delay() `EXTRACTED`
- .__exit__() `EXTRACTED`
- .__enter__() `EXTRACTED`

### rationale_for
- Schedule a gateway, up to five saved targets and one League target. ``poll()``… `EXTRACTED`

### uses
- [VareduraTextualApp](VareduraTextualApp.md) `INFERRED`
- [PingTarget](PingTarget.md) `INFERRED`
- TargetSelection `INFERRED`
- PingProbeResult `INFERRED`
- PingStatus `INFERRED`
- HostKind `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*