from io import StringIO

from rich.console import Console

from cli import ui_shared
from monitor import stalker


def test_legacy_defaults_never_restore_speculative_external_target():
    config = stalker.StalkerConfig()
    assert config.gateway_ip == ""
    assert config.external_ip == ""


def test_legacy_monitor_returns_without_ping_when_onboarding_is_incomplete(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(
        stalker,
        "run_ping",
        lambda host: (_ for _ in ()).throw(AssertionError("ping must not start")),
    )
    output = StringIO()

    stalker.main(external_console=Console(file=output, force_terminal=False))

    assert "target" in output.getvalue().casefold() or "destino" in output.getvalue().casefold()
