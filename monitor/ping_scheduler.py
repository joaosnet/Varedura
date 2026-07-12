"""Fair, bounded scheduler for multiple ICMP targets.

The scheduler is inert until :meth:`PingScheduler.poll` or
:meth:`PingScheduler.start` is called.  Its monotonic clock and executor are
injectable so cadence, backoff and stale-generation behaviour can be tested
without real time or network traffic.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import CancelledError, Executor, Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Callable

from monitor.ping_targets import (
    MAX_PERSISTENT_TARGETS,
    PingProbeResult,
    PingStatus,
    PingTarget,
    TargetSelection,
    HostKind,
    probe_ping,
    validate_host,
)


MAX_CONCURRENT_PROBES = 3


class TargetRole(StrEnum):
    GATEWAY = "gateway"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    LEAGUE = "league"


_FAST_BACKOFF = (1.0, 2.0, 5.0, 15.0, 30.0)
_SECONDARY_BACKOFF = (3.0, 6.0, 15.0, 30.0)
_ROLE_PRIORITY = {
    TargetRole.GATEWAY: 0,
    TargetRole.LEAGUE: 1,
    TargetRole.PRIMARY: 2,
    TargetRole.SECONDARY: 3,
}


@dataclass(frozen=True, slots=True)
class SchedulerTargetSnapshot:
    target: PingTarget
    role: TargetRole
    generation: int
    next_due: float
    failures: int
    in_flight: bool
    last_result: PingProbeResult | None


@dataclass(slots=True)
class _TargetState:
    target: PingTarget
    role: TargetRole
    generation: int
    next_due: float
    failures: int = 0
    in_flight: bool = False
    last_result: PingProbeResult | None = None

    def snapshot(self) -> SchedulerTargetSnapshot:
        return SchedulerTargetSnapshot(
            target=self.target,
            role=self.role,
            generation=self.generation,
            next_due=self.next_due,
            failures=self.failures,
            in_flight=self.in_flight,
            last_result=self.last_result,
        )


@dataclass(slots=True)
class _Flight:
    target_id: str
    generation: int
    cancel_event: threading.Event


ProbeCallable = Callable[..., PingProbeResult]
ResultCallback = Callable[[PingProbeResult], None]
_FILTERABLE_ICMP_FAILURES = {PingStatus.TIMEOUT, PingStatus.UNREACHABLE}


class PingScheduler:
    """Schedule a gateway, up to five saved targets and one League target.

    ``poll()`` is suitable for an existing application worker.  ``start()`` is
    a convenience background loop.  At most three probes and at most one probe
    per target can be active at once.
    """

    def __init__(
        self,
        *,
        probe: ProbeCallable = probe_ping,
        executor: Executor | None = None,
        clock: Callable[[], float] = time.monotonic,
        max_concurrent: int = MAX_CONCURRENT_PROBES,
        probe_timeout: float = 1.25,
        route_retry_interval: float = 15.0,
    ) -> None:
        if not 1 <= max_concurrent <= MAX_CONCURRENT_PROBES:
            raise ValueError(
                f"max_concurrent must be between 1 and {MAX_CONCURRENT_PROBES}"
            )
        self._probe = probe
        self._clock = clock
        self._max_concurrent = max_concurrent
        self._probe_timeout = probe_timeout
        self._route_retry_interval = max(1.0, route_retry_interval)
        self._executor = executor or ThreadPoolExecutor(
            max_workers=max_concurrent,
            thread_name_prefix="varedura-ping",
        )
        self._owns_executor = executor is None
        self._states: dict[str, _TargetState] = {}
        self._generation_counters: dict[str, int] = {}
        self._flights: dict[Future[PingProbeResult], _Flight] = {}
        self._route_available = True
        self._alternative_connectivity_healthy = False
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._closed = False

    def configure(
        self,
        selection: TargetSelection,
        *,
        gateway_target: PingTarget | None = None,
        league_target: PingTarget | None = None,
    ) -> None:
        """Atomically replace desired targets and invalidate changed work."""

        if len(selection.targets) > MAX_PERSISTENT_TARGETS:
            raise ValueError("too many persistent ping targets")
        if league_target is not None and not league_target.ephemeral:
            raise ValueError("the live League target must be ephemeral")
        desired: list[tuple[PingTarget, TargetRole]] = []
        if gateway_target is not None:
            desired.append((gateway_target, TargetRole.GATEWAY))
        for target in selection.targets:
            role = (
                TargetRole.PRIMARY
                if target.id == selection.primary_target_id
                else TargetRole.SECONDARY
            )
            desired.append((target, role))
        if league_target is not None:
            desired.append((league_target, TargetRole.LEAGUE))
        ids = [target.id for target, _ in desired]
        if len(set(ids)) != len(ids):
            raise ValueError("scheduler target ids must be unique")

        now = self._clock()
        secondary_count = sum(role is TargetRole.SECONDARY for _, role in desired)
        secondary_index = 0
        with self._lock:
            if self._closed:
                raise RuntimeError("scheduler is closed")
            desired_ids = set(ids)
            for target_id in set(self._states) - desired_ids:
                self._invalidate_locked(target_id)
                del self._states[target_id]

            for target, role in desired:
                old = self._states.get(target.id)
                if old is not None and old.target == target and old.role is role:
                    if role is TargetRole.SECONDARY:
                        secondary_index += 1
                    continue
                if old is not None:
                    self._invalidate_locked(target.id)
                generation = self._generation_counters.get(target.id, 0) + 1
                self._generation_counters[target.id] = generation
                if role is TargetRole.SECONDARY:
                    secondary_index += 1
                    # Distribute cold-start probes through the first 3s window.
                    offset = (3.0 * secondary_index) / (secondary_count + 1)
                else:
                    offset = 0.0
                self._states[target.id] = _TargetState(
                    target=target,
                    role=role,
                    generation=generation,
                    next_due=now + offset,
                )

    def set_route_available(self, available: bool) -> None:
        """Suspend external probes while continuing to observe the gateway."""

        now = self._clock()
        with self._lock:
            previous = self._route_available
            self._route_available = bool(available)
            if previous and not available:
                for future, flight in tuple(self._flights.items()):
                    state = self._states.get(flight.target_id)
                    if state is not None and self._requires_default_route(state):
                        flight.cancel_event.set()
                        future.cancel()
            elif available and not previous:
                for state in self._states.values():
                    if self._requires_default_route(state) and not state.in_flight:
                        state.next_due = now

    def set_alternative_connectivity_healthy(self, healthy: bool) -> None:
        """Tell the scheduler HTTPS/TCP works despite possible ICMP filtering."""

        with self._lock:
            self._alternative_connectivity_healthy = bool(healthy)

    def poll(self, now: float | None = None) -> list[PingProbeResult]:
        """Collect finished work and submit currently due probes without blocking."""

        current = self._clock() if now is None else now
        accepted: list[PingProbeResult] = []
        with self._lock:
            if self._closed:
                return accepted
            for future, flight in tuple(self._flights.items()):
                if not future.done():
                    continue
                del self._flights[future]
                state = self._states.get(flight.target_id)
                if state is not None and state.generation == flight.generation:
                    state.in_flight = False
                try:
                    result = future.result()
                except CancelledError:
                    result = PingProbeResult(
                        target_id=flight.target_id,
                        generation=flight.generation,
                        host=state.target.host if state is not None else "",
                        status=PingStatus.CANCELLED,
                        started_monotonic=current,
                        completed_monotonic=current,
                    )
                except Exception as exc:
                    result = PingProbeResult(
                        target_id=flight.target_id,
                        generation=flight.generation,
                        host=state.target.host if state is not None else "",
                        status=PingStatus.ERROR,
                        started_monotonic=current,
                        completed_monotonic=current,
                        detail=str(exc),
                    )
                if (
                    state is None
                    or state.generation != flight.generation
                    or result.generation != flight.generation
                    or result.target_id != flight.target_id
                ):
                    continue
                result = self._apply_result_locked(state, result, current)
                accepted.append(result)

            capacity = self._max_concurrent - len(self._flights)
            if capacity <= 0:
                return accepted
            # A cancelled running future cannot be forcefully stopped by
            # ThreadPoolExecutor.  Keep its target reserved until it actually
            # finishes so a reconfiguration never creates two simultaneous
            # probes for the same target id.
            active_target_ids = {
                flight.target_id
                for future, flight in self._flights.items()
                if not future.done()
            }
            due = sorted(
                (
                    state
                    for state in self._states.values()
                    if not state.in_flight
                    and state.target.id not in active_target_ids
                    and state.next_due <= current
                ),
                key=lambda state: (
                    state.next_due,
                    _ROLE_PRIORITY[state.role],
                    state.target.id,
                ),
            )
            for state in due:
                if capacity <= 0:
                    break
                if not self._route_available and self._requires_default_route(state):
                    state.next_due = current + self._route_retry_interval
                    continue
                cancel_event = threading.Event()
                try:
                    future = self._executor.submit(
                        self._run_probe,
                        state.target,
                        state.generation,
                        cancel_event,
                    )
                except RuntimeError:
                    state.next_due = current + self._base_interval(state.role)
                    continue
                state.in_flight = True
                self._flights[future] = _Flight(
                    target_id=state.target.id,
                    generation=state.generation,
                    cancel_event=cancel_event,
                )
                capacity -= 1
        return accepted

    def _run_probe(
        self,
        target: PingTarget,
        generation: int,
        cancel_event: threading.Event,
    ) -> PingProbeResult:
        return self._probe(
            target,
            generation=generation,
            timeout_seconds=self._probe_timeout,
            cancel_event=cancel_event,
        )

    def _apply_result_locked(
        self,
        state: _TargetState,
        result: PingProbeResult,
        now: float,
    ) -> PingProbeResult:
        if result.success:
            state.failures = 0
            interval = self._base_interval(state.role)
        elif result.status is PingStatus.CANCELLED:
            interval = self._base_interval(state.role)
        else:
            state.failures += 1
            if (
                state.failures >= 3
                and self._alternative_connectivity_healthy
                and state.role is not TargetRole.GATEWAY
                and result.status in _FILTERABLE_ICMP_FAILURES
            ):
                result = replace(
                    result,
                    status=PingStatus.ICMP_FILTERED,
                    detail=(result.detail + " | ICMP possivelmente filtrado").strip(
                        " |"
                    ),
                )
                interval = 30.0
            else:
                steps = (
                    _SECONDARY_BACKOFF
                    if state.role is TargetRole.SECONDARY
                    else _FAST_BACKOFF
                )
                interval = steps[min(max(state.failures - 1, 0), len(steps) - 1)]
        state.last_result = result
        state.next_due = now + interval
        return result

    @staticmethod
    def _base_interval(role: TargetRole) -> float:
        return 3.0 if role is TargetRole.SECONDARY else 1.0

    @staticmethod
    def _requires_default_route(state: _TargetState) -> bool:
        if state.role is TargetRole.GATEWAY:
            return False
        try:
            validated = validate_host(state.target.host)
        except ValueError:
            return True
        return not (
            validated.kind in {HostKind.IPV4, HostKind.IPV6}
            and (validated.is_private or validated.is_link_local or validated.is_loopback)
        )

    def _invalidate_locked(self, target_id: str) -> None:
        state = self._states.get(target_id)
        if state is not None:
            state.generation += 1
            self._generation_counters[target_id] = max(
                state.generation, self._generation_counters.get(target_id, 0)
            )
        for future, flight in tuple(self._flights.items()):
            if flight.target_id == target_id:
                flight.cancel_event.set()
                future.cancel()

    def snapshot(self) -> tuple[SchedulerTargetSnapshot, ...]:
        with self._lock:
            return tuple(
                state.snapshot()
                for state in sorted(
                    self._states.values(),
                    key=lambda item: (_ROLE_PRIORITY[item.role], item.target.id),
                )
            )

    @property
    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._flights)

    def next_wake_delay(self, *, maximum: float = 0.25) -> float:
        with self._lock:
            if not self._states:
                return maximum
            due = min(state.next_due for state in self._states.values())
        return max(0.01, min(maximum, due - self._clock()))

    def start(
        self,
        callback: ResultCallback,
        *,
        tick_interval: float = 0.05,
    ) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("scheduler is closed")
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()

            def loop() -> None:
                while not self._stop_event.is_set():
                    for result in self.poll():
                        if self._stop_event.is_set():
                            break
                        try:
                            callback(result)
                        except Exception:
                            pass
                    self._stop_event.wait(
                        min(max(0.01, tick_interval), self.next_wake_delay())
                    )

            self._thread = threading.Thread(
                target=loop,
                name="varedura-ping-scheduler",
                daemon=True,
            )
            self._thread.start()

    def stop(self, *, wait: bool = True) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._stop_event.set()
            for future, flight in tuple(self._flights.items()):
                flight.cancel_event.set()
                future.cancel()
            thread = self._thread
        if wait and thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        if self._owns_executor:
            self._executor.shutdown(wait=wait, cancel_futures=True)

    close = stop

    def __enter__(self) -> "PingScheduler":
        return self

    def __exit__(self, *_args: object) -> None:
        self.stop()


__all__ = [
    "MAX_CONCURRENT_PROBES",
    "PingScheduler",
    "SchedulerTargetSnapshot",
    "TargetRole",
]
