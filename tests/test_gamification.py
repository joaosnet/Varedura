import pytest

from cli import gamification as g


@pytest.fixture(autouse=True)
def isolated_prefs(monkeypatch, tmp_path):
    from cli import ui_shared

    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "prefs.json")
    yield


def test_health_score_no_data_is_neutral():
    score, tier, _ = g.compute_health_score([], [], threshold=100)
    assert score == 0 and tier == "—"


def test_health_score_great_connection_is_top_tier():
    hist = [12.0] * 20
    score, tier, _ = g.compute_health_score(hist, hist, threshold=100, speed_compliant=True)
    assert score >= 90 and tier == "S"


def test_health_score_timeouts_are_critical():
    hist = [None] * 20
    score, tier, _ = g.compute_health_score(hist, hist, threshold=100)
    assert score == 0 and tier == "F"


def test_health_score_laggy_is_lower_than_clean():
    clean = g.compute_health_score([15.0] * 20, [15.0] * 20, 100)[0]
    laggy = g.compute_health_score([260.0] * 20, [260.0] * 20, 100)[0]
    assert laggy < clean


def test_streak_resets_on_lag():
    s = g.StreakTracker()
    assert s.update(True, 1.0) == 1.0
    assert s.update(True, 1.0) == 2.0
    assert s.update(False, 1.0) == 0.0


def test_update_records_keeps_best_and_accumulates():
    state = g.GameState()
    g.update_records(state, ping=30, download=100, pings=5)
    g.update_records(state, ping=18, download=80, pings=5)
    assert state.best_ping == 18  # lower is better
    assert state.best_download == 100  # higher is better
    assert state.total_pings == 10


def test_check_achievements_unlocks_once():
    state = g.GameState()
    g.update_records(state, ping=15)  # sub20
    first = g.check_achievements(state)
    assert "sub20" in first
    # Idempotent: already unlocked -> not returned again.
    assert "sub20" not in g.check_achievements(state)


def test_game_state_round_trips_through_prefs():
    state = g.load_game_state()
    g.update_records(state, space_freed_gb=6.0, cleanups=1)
    state.achievements.add("docker_first")
    g.save_game_state(state)

    reloaded = g.load_game_state()
    assert reloaded.total_space_freed_gb == 6.0
    assert reloaded.cleanups_run == 1
    assert "docker_first" in reloaded.achievements
