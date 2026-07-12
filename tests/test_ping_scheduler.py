"""Deterministic cadence, concurrency, backoff and generation tests."""

from concurrent.futures import Future

from monitor.ping_scheduler import PingScheduler, TargetRole
from monitor.ping_targets import (
    PingProbeResult,
    PingStatus,
    PingTarget,
    TargetCategory,
    TargetSelection,
    target_by_id,
)


class _Clock:
    value = 0.0

    def __call__(self):
        return self.value


class _ManualFuture(Future):
    # Model already-running work: configure() can signal cancellation but cannot
    # forcibly remove it, which lets the stale-generation path be exercised.
    def cancel(self):
        return False


class _ManualExecutor:
    def __init__(self):
        self.pending = []

    def submit(self, fn, *args, **kwargs):
        future = _ManualFuture()
        self.pending.append((future, fn, args, kwargs))
        return future

    def complete(self, index=0):
        future, fn, args, kwargs = self.pending.pop(index)
        future.set_result(fn(*args, **kwargs))
        return future

    def complete_all(self):
        while self.pending:
            self.complete()


def _selection(count=1):
    targets = tuple(
        target
        for target in (
            target_by_id("cloudflare_ipv4"),
            target_by_id("google_ipv4"),
            target_by_id("quad9_ipv4"),
            target_by_id("web_github"),
            target_by_id("lol_br1_api"),
        )[:count]
        if target is not None
    )
    return TargetSelection(targets, targets[0].id, onboarding_completed=True)


def _result(target, generation, status=PingStatus.SUCCESS):
    return PingProbeResult(
        target_id=target.id,
        generation=generation,
        host=target.host,
        status=status,
        started_monotonic=0.0,
        completed_monotonic=0.01,
        latency_ms=10.0 if status is PingStatus.SUCCESS else None,
    )


def _gateway():
    return PingTarget(
        "gateway_current",
        "Gateway",
        "192.168.1.1",
        TargetCategory.GATEWAY,
        ephemeral=True,
    )


def _league():
    return PingTarget(
        "league_match_session",
        "League",
        "104.160.131.3",
        TargetCategory.LEAGUE_MATCH,
        ephemeral=True,
    )


def test_scheduler_limits_concurrency_and_staggers_secondaries():
    clock = _Clock()
    executor = _ManualExecutor()

    def probe(target, *, generation, **_kwargs):
        return _result(target, generation)

    scheduler = PingScheduler(probe=probe, executor=executor, clock=clock)
    scheduler.configure(
        _selection(5), gateway_target=_gateway(), league_target=_league()
    )
    assert len(scheduler.snapshot()) == 7  # gateway + five saved + League

    scheduler.poll(now=0.0)
    assert scheduler.in_flight_count == 3
    roles = {snapshot.role for snapshot in scheduler.snapshot() if snapshot.in_flight}
    assert roles == {TargetRole.GATEWAY, TargetRole.PRIMARY, TargetRole.LEAGUE}

    executor.complete_all()
    accepted = scheduler.poll(now=0.0)
    assert len(accepted) == 3
    assert scheduler.in_flight_count == 0
    assert all(
        state.next_due > 0
        for state in scheduler.snapshot()
        if state.role is TargetRole.SECONDARY
    )
    scheduler.stop()


def test_primary_failure_backoff_is_monotonic_and_bounded():
    clock = _Clock()
    executor = _ManualExecutor()

    def fail(target, *, generation, **_kwargs):
        return _result(target, generation, PingStatus.TIMEOUT)

    scheduler = PingScheduler(probe=fail, executor=executor, clock=clock)
    scheduler.configure(_selection())
    expected_due = (1.0, 3.0, 8.0, 23.0, 53.0)
    now = 0.0
    for due in expected_due:
        scheduler.poll(now=now)
        assert scheduler.in_flight_count == 1
        executor.complete()
        scheduler.poll(now=now)
        state = scheduler.snapshot()[0]
        assert state.next_due == due
        scheduler.poll(now=due - 0.01)
        assert scheduler.in_flight_count == 0
        now = due
    scheduler.stop()


def test_route_loss_suspends_external_but_not_gateway():
    executor = _ManualExecutor()
    scheduler = PingScheduler(
        probe=lambda target, *, generation, **kwargs: _result(target, generation),
        executor=executor,
        clock=lambda: 0.0,
    )
    scheduler.configure(_selection(), gateway_target=_gateway())
    scheduler.set_route_available(False)
    scheduler.poll(now=0.0)
    states = {state.role: state for state in scheduler.snapshot()}
    assert states[TargetRole.GATEWAY].in_flight
    assert not states[TargetRole.PRIMARY].in_flight
    assert states[TargetRole.PRIMARY].next_due == 15.0
    scheduler.stop()


def test_route_loss_still_allows_explicit_private_institutional_target():
    executor = _ManualExecutor()
    private = PingTarget(
        "private_target", "Intranet", "10.20.30.40", TargetCategory.CUSTOM
    )
    selection = TargetSelection((private,), private.id, onboarding_completed=True)
    scheduler = PingScheduler(
        probe=lambda target, *, generation, **kwargs: _result(target, generation),
        executor=executor,
        clock=lambda: 0.0,
    )
    scheduler.configure(selection)
    scheduler.set_route_available(False)
    scheduler.poll(now=0.0)
    assert scheduler.in_flight_count == 1
    scheduler.stop()


def test_reconfigure_discards_old_generation_result():
    executor = _ManualExecutor()

    def probe(target, *, generation, cancel_event, **_kwargs):
        status = PingStatus.CANCELLED if cancel_event.is_set() else PingStatus.SUCCESS
        return _result(target, generation, status)

    old = PingTarget("stable_id", "Old", "1.1.1.1", TargetCategory.CUSTOM)
    new = PingTarget("stable_id", "New", "8.8.8.8", TargetCategory.CUSTOM)
    scheduler = PingScheduler(probe=probe, executor=executor, clock=lambda: 0.0)
    scheduler.configure(TargetSelection((old,), old.id))
    scheduler.poll(now=0.0)
    old_generation = scheduler.snapshot()[0].generation
    scheduler.configure(TargetSelection((new,), new.id))
    new_generation = scheduler.snapshot()[0].generation
    assert new_generation > old_generation

    executor.complete()
    assert scheduler.poll(now=0.0) == []
    assert scheduler.snapshot()[0].last_result is None
    scheduler.stop()


def test_reconfigure_never_overlaps_old_and_new_probe_for_same_target_id():
    executor = _ManualExecutor()

    def probe(target, *, generation, **_kwargs):
        return _result(target, generation)

    old = PingTarget("stable_id", "Old", "1.1.1.1", TargetCategory.CUSTOM)
    new = PingTarget("stable_id", "New", "8.8.8.8", TargetCategory.CUSTOM)
    scheduler = PingScheduler(probe=probe, executor=executor, clock=lambda: 0.0)
    scheduler.configure(TargetSelection((old,), old.id))
    scheduler.poll(now=0.0)
    assert len(executor.pending) == 1

    scheduler.configure(TargetSelection((new,), new.id))
    scheduler.poll(now=0.0)
    assert len(executor.pending) == 1

    executor.complete()
    scheduler.poll(now=0.0)
    assert len(executor.pending) == 1
    scheduler.stop()


def test_three_failures_with_working_https_mark_icmp_filtered():
    executor = _ManualExecutor()

    def fail(target, *, generation, **_kwargs):
        return _result(target, generation, PingStatus.TIMEOUT)

    scheduler = PingScheduler(probe=fail, executor=executor, clock=lambda: 0.0)
    scheduler.configure(_selection())
    scheduler.set_alternative_connectivity_healthy(True)
    last = None
    for now in (0.0, 1.0, 3.0):
        scheduler.poll(now=now)
        executor.complete()
        last = scheduler.poll(now=now)[0]
    assert last is not None
    assert last.status is PingStatus.ICMP_FILTERED
    assert scheduler.snapshot()[0].next_due == 33.0
    scheduler.stop()


def test_non_icmp_failure_is_never_relabelled_as_filtered():
    executor = _ManualExecutor()

    def fail(target, *, generation, **_kwargs):
        return _result(target, generation, PingStatus.DNS_ERROR)

    scheduler = PingScheduler(probe=fail, executor=executor, clock=lambda: 0.0)
    scheduler.configure(_selection())
    scheduler.set_alternative_connectivity_healthy(True)
    last = None
    for now in (0.0, 1.0, 3.0):
        scheduler.poll(now=now)
        executor.complete()
        last = scheduler.poll(now=now)[0]
    assert last is not None
    assert last.status is PingStatus.DNS_ERROR
    scheduler.stop()
