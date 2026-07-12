import csv
from datetime import datetime, timezone

from monitor.network_history import NetworkSessionHistory, mask_ip
from monitor.ping_targets import (
    PingProbeResult,
    PingStatus,
    PingTarget,
    TargetCategory,
)


def _result(target: PingTarget, *, generation: int, latency: float | None):
    return PingProbeResult(
        target_id=target.id,
        generation=generation,
        host=target.host,
        status=PingStatus.SUCCESS if latency is not None else PingStatus.TIMEOUT,
        started_monotonic=1.0,
        completed_monotonic=1.01,
        latency_ms=latency,
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_history_groups_targets_generations_and_sessions():
    history = NetworkSessionHistory()
    first = PingTarget("first", "First", "1.1.1.1", TargetCategory.INFRASTRUCTURE)
    second = PingTarget("second", "Second", "8.8.8.8", TargetCategory.INFRASTRUCTURE)
    history.add_result(_result(first, generation=1, latency=10), first)
    history.add_result(_result(first, generation=2, latency=20), first)
    history.add_result(_result(second, generation=1, latency=None), second)

    assert len(history.grouped()) == 3


def test_league_exports_mask_ips_by_default(tmp_path):
    target = PingTarget(
        "league_match_session",
        "League match",
        "104.160.131.3",
        TargetCategory.LEAGUE_MATCH,
        ephemeral=True,
    )
    history = NetworkSessionHistory()
    history.add_result(
        _result(target, generation=1, latency=35),
        target,
        remote_port=5001,
        session_id="session-1",
    )

    masked = history.export_csv(tmp_path / "masked.csv").read_text(encoding="utf-8")
    full = history.export_csv(tmp_path / "full.csv", include_full_ips=True).read_text(
        encoding="utf-8"
    )
    assert "104.160.131.0/24" in masked
    assert "104.160.131.3" not in masked
    assert "104.160.131.3" in full


def test_mask_ip_supports_ipv4_ipv6_and_hostnames():
    assert mask_ip("203.0.113.42") == "203.0.113.0/24"
    assert mask_ip("2001:db8:1234:5678::1") == "2001:db8:1234:5678::/64"
    assert mask_ip("example.com") == "example.com"


def test_pdf_export_keeps_target_blocks_separate(tmp_path):
    target = PingTarget(
        "cloudflare", "Cloudflare", "1.1.1.1", TargetCategory.INFRASTRUCTURE
    )
    history = NetworkSessionHistory()
    history.add_result(_result(target, generation=1, latency=11), target)
    path = history.export_pdf(tmp_path / "report.pdf")
    assert path.exists()
    assert path.stat().st_size > 500


def test_csv_rows_are_contiguous_by_target_generation(tmp_path):
    history = NetworkSessionHistory()
    first = PingTarget("first", "First", "1.1.1.1", TargetCategory.INFRASTRUCTURE)
    second = PingTarget("second", "Second", "8.8.8.8", TargetCategory.INFRASTRUCTURE)
    history.add_result(_result(first, generation=1, latency=10), first)
    history.add_result(_result(second, generation=1, latency=20), second)
    history.add_result(_result(first, generation=1, latency=11), first)

    path = history.export_csv(tmp_path / "grouped.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        ids = [row["target_id"] for row in csv.DictReader(handle)]
    assert ids == ["first", "first", "second"]
