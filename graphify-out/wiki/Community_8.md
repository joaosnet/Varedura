# Community 8

> 49 nodes · cohesion 0.12

## Key Concepts

- **PingScheduler** (38 connections) — `monitor/ping_scheduler.py`
- **test_ping_scheduler.py** (27 connections) — `tests/test_ping_scheduler.py`
- **.poll()** (16 connections) — `monitor/ping_scheduler.py`
- **.configure()** (14 connections) — `monitor/ping_scheduler.py`
- **test_scheduler_limits_concurrency_and_staggers_secondaries()** (14 connections) — `tests/test_ping_scheduler.py`
- **_ManualExecutor** (13 connections) — `tests/test_ping_scheduler.py`
- **test_reconfigure_discards_old_generation_result()** (13 connections) — `tests/test_ping_scheduler.py`
- **test_primary_failure_backoff_is_monotonic_and_bounded()** (12 connections) — `tests/test_ping_scheduler.py`
- **test_route_loss_still_allows_explicit_private_institutional_target()** (12 connections) — `tests/test_ping_scheduler.py`
- **test_route_loss_suspends_external_but_not_gateway()** (12 connections) — `tests/test_ping_scheduler.py`
- **test_three_failures_with_working_https_mark_icmp_filtered()** (12 connections) — `tests/test_ping_scheduler.py`
- **_result()** (11 connections) — `tests/test_ping_scheduler.py`
- **test_non_icmp_failure_is_never_relabelled_as_filtered()** (11 connections) — `tests/test_ping_scheduler.py`
- **test_reconfigure_never_overlaps_old_and_new_probe_for_same_target_id()** (11 connections) — `tests/test_ping_scheduler.py`
- **.stop()** (10 connections) — `monitor/ping_scheduler.py`
- **_selection()** (8 connections) — `tests/test_ping_scheduler.py`
- **.snapshot()** (7 connections) — `monitor/ping_scheduler.py`
- **_TargetState** (7 connections) — `monitor/ping_scheduler.py`
- **target_by_id()** (7 connections) — `monitor/ping_targets.py`
- **TargetRole** (6 connections) — `monitor/ping_scheduler.py`
- **._apply_result_locked()** (5 connections) — `monitor/ping_scheduler.py`
- **._requires_default_route()** (5 connections) — `monitor/ping_scheduler.py`
- **.set_route_available()** (5 connections) — `monitor/ping_scheduler.py`
- **_gateway()** (5 connections) — `tests/test_ping_scheduler.py`
- **._base_interval()** (4 connections) — `monitor/ping_scheduler.py`
- *... and 24 more nodes in this community*

## Relationships

- [Community 11](Community_11.md) (18 shared connections)
- [Community 36](Community_36.md) (17 shared connections)
- [Community 87](Community_87.md) (9 shared connections)
- [Community 28](Community_28.md) (9 shared connections)
- [Community 108](Community_108.md) (3 shared connections)
- [Community 6](Community_6.md) (2 shared connections)
- [Community 107](Community_107.md) (2 shared connections)
- [Community 30](Community_30.md) (1 shared connections)
- [Community 110](Community_110.md) (1 shared connections)
- [Community 1](Community_1.md) (1 shared connections)

## Source Files

- `monitor/ping_scheduler.py`
- `monitor/ping_targets.py`
- `tests/test_ping_scheduler.py`

## Audit Trail

- EXTRACTED: 137 (69%)
- INFERRED: 62 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*