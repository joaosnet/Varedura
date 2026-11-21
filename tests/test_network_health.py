"""Unit tests for monitor.network_health.compute_health_score."""

from monitor.network_health import compute_health_score


def test_health_score_no_data_is_neutral():
    score, tier, color = compute_health_score([], [], threshold=100)
    assert score == 0
    assert tier == "—"
    assert color == "dim"


def test_health_score_great_connection_is_top_tier():
    hist = [12.0] * 20
    score, tier, color = compute_health_score(
        hist, hist, threshold=100, speed_compliant=True
    )
    assert score >= 90
    assert tier == "S"
    assert color == "green"


def test_health_score_all_timeouts_is_critical():
    hist = [None] * 20
    score, tier, color = compute_health_score(hist, hist, threshold=100)
    assert score == 0
    assert tier == "F"
    assert color == "red"


def test_health_score_laggy_is_lower_than_clean():
    clean = compute_health_score([15.0] * 20, [15.0] * 20, 100)[0]
    laggy = compute_health_score([260.0] * 20, [260.0] * 20, 100)[0]
    assert laggy < clean


def test_health_score_falls_back_to_local_history_and_respects_window():
    old_bad = [500.0] * 30
    recent_good = [10.0] * 20
    score, tier, _ = compute_health_score(
        old_bad + recent_good, [], threshold=100, speed_compliant=True, window=20
    )
    assert score >= 90
    assert tier == "S"


def test_health_score_speed_compliance_weights_10_percent():
    hist = [10.0] * 20
    s_ok = compute_health_score(hist, hist, 100, speed_compliant=True)[0]
    s_mid = compute_health_score(hist, hist, 100, speed_compliant=None)[0]
    s_bad = compute_health_score(hist, hist, 100, speed_compliant=False)[0]
    assert s_ok > s_mid > s_bad
    assert s_ok - s_bad == 10
