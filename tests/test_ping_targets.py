"""Catalogue, validation, migration and bounded ICMP probe tests."""

import threading

import pytest

from monitor import ping_targets as targets


def test_catalog_has_stable_ids_and_unique_entries():
    ids = [target.id for target in targets.TARGET_CATALOG]
    assert len(ids) == len(set(ids))
    for expected in (
        "cloudflare_ipv4",
        "google_ipv4",
        "quad9_ipv4",
        "lol_br1_api",
    ):
        assert targets.target_by_id(expected) is not None
    assert targets.target_by_id("missing") is None
    assert targets.target_catalog(targets.TargetCategory.WEB)
    assert targets.target_by_id("fortnite_nac").host == "ping-nac.ds.on.epicgames.com"


@pytest.mark.parametrize(
    ("raw", "canonical", "kind"),
    [
        ("1.1.1.1", "1.1.1.1", targets.HostKind.IPV4),
        ("2606:4700:4700:0:0:0:0:1111", "2606:4700:4700::1111", targets.HostKind.IPV6),
        ("ExAmPlE.COM.", "example.com", targets.HostKind.HOSTNAME),
        ("münich.example", "xn--mnich-kva.example", targets.HostKind.HOSTNAME),
    ],
)
def test_validate_host_canonicalizes_without_resolving(raw, canonical, kind):
    validated = targets.validate_host(raw)
    assert validated.host == canonical
    assert validated.kind is kind


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.com",
        "example.com:443",
        "1.1.1.1/24",
        "*.example.com",
        "-n",
        "host name",
        "example.com\n--help",
        "user@example.com",
        "[2606:4700:4700::1111]",
        "fe80::1%eth0",
        "224.0.0.1",
        "0.0.0.0",
        "255.255.255.255",
    ],
)
def test_validate_host_rejects_unsafe_or_ambiguous_input(raw):
    with pytest.raises(ValueError):
        targets.validate_host(raw)


def test_private_institutional_target_is_allowed_and_flagged():
    validated = targets.validate_host("10.20.30.40")
    custom = targets.create_custom_target("10.20.30.40", "Intranet")
    assert validated.is_private
    assert custom.category is targets.TargetCategory.CUSTOM
    assert "institucional" in custom.warning


@pytest.mark.parametrize("label", ["[red]spoof[/]", "line\nbreak", "x" * 97])
def test_custom_target_label_rejects_markup_controls_and_excessive_length(label):
    with pytest.raises(ValueError, match="unsafe formatting"):
        targets.create_custom_target("example.com", label)


def test_selection_round_trip_and_legacy_migration():
    custom = targets.create_custom_target("intranet.example", "Intranet")
    selection = targets.TargetSelection(
        targets=(targets.target_by_id("cloudflare_ipv4"), custom),
        primary_target_id=custom.id,
        onboarding_completed=True,
        league_auto_detect=False,
    )
    restored = targets.TargetSelection.from_config(selection.to_config())
    assert restored.selected_target_ids == selection.selected_target_ids
    assert restored.primary_target_id == custom.id
    assert not restored.league_auto_detect

    legacy = targets.TargetSelection.from_config({"external_host": "my.router.example"})
    assert len(legacy.targets) == 1
    assert legacy.primary_target_id == legacy.targets[0].id
    assert legacy.onboarding_completed

    old_default = targets.TargetSelection.from_config(
        {"external_host": targets.LEGACY_DEFAULT_HOST}
    )
    assert not old_default.targets
    assert not old_default.onboarding_completed


def test_selection_enforces_five_persistent_and_primary():
    six = tuple(targets.TARGET_CATALOG[:6])
    with pytest.raises(ValueError, match="at most"):
        targets.TargetSelection(six, six[0].id)
    with pytest.raises(ValueError, match="primary"):
        targets.TargetSelection((targets.TARGET_CATALOG[0],), "missing")
    live = targets.PingTarget(
        "league_match_test",
        "League",
        "1.1.1.1",
        targets.TargetCategory.LEAGUE_MATCH,
        ephemeral=True,
    )
    with pytest.raises(ValueError, match="ephemeral"):
        targets.TargetSelection((live,), live.id)
    with pytest.raises(ValueError, match="completed onboarding"):
        targets.TargetSelection(onboarding_completed=True)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("64 bytes from 1.1.1.1: time=12.4 ms", 12.4),
        ("Resposta: tempo=8,5ms TTL=57", 8.5),
        ("Reply from 1.1.1.1: time<1ms TTL=57", 0.5),
        ("Antwort von 1.1.1.1: Zeit=17ms TTL=57", 17.0),
        ("Request timed out.", None),
    ],
)
def test_parse_ping_latency_is_locale_tolerant(output, expected):
    assert targets.parse_ping_latency(output) == expected


def test_build_ping_command_uses_argument_list_and_address_family():
    command = targets.build_ping_command(
        "2606:4700:4700::1111", timeout_seconds=0.7, system="Windows"
    )
    assert command == [
        "ping",
        "-6",
        "-n",
        "1",
        "-w",
        "700",
        "2606:4700:4700::1111",
    ]
    assert targets.build_ping_command("1.1.1.1", system="Linux")[-1] == "1.1.1.1"
    hostname_command = targets.build_ping_command("example.com", system="Linux")
    assert "-4" not in hostname_command and "-6" not in hostname_command


class _CompletedPopen:
    def __init__(self, _command, **kwargs):
        assert kwargs["shell"] is False
        self.returncode = 0
        self.pid = 321

    def poll(self):
        return self.returncode

    def communicate(self, timeout=None):
        return "Reply: time=14.2ms", ""


class _HangingPopen:
    def __init__(self, _command, **_kwargs):
        self.returncode = None
        self.pid = 322

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = -15

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode

    def communicate(self, timeout=None):
        return "", ""


def test_probe_ping_returns_structured_success(monkeypatch):
    monkeypatch.setattr(targets.subprocess, "Popen", _CompletedPopen)
    target = targets.target_by_id("cloudflare_ipv4")
    result = targets.probe_ping(target, generation=7)
    assert result.status is targets.PingStatus.SUCCESS
    assert result.latency_ms == 14.2
    assert result.target_id == "cloudflare_ipv4"
    assert result.generation == 7
    assert result.success


def test_probe_ping_honours_cancellation_before_spawn(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("subprocess must not start")

    monkeypatch.setattr(targets.subprocess, "Popen", fail_if_called)
    cancelled = threading.Event()
    cancelled.set()
    result = targets.probe_ping("1.1.1.1", cancel_event=cancelled)
    assert result.status is targets.PingStatus.CANCELLED


def test_probe_ping_has_parent_timeout(monkeypatch):
    monkeypatch.setattr(targets.subprocess, "Popen", _HangingPopen)
    monkeypatch.setattr(
        targets,
        "_terminate_process",
        lambda process: process.terminate(),
    )
    result = targets.probe_ping("1.1.1.1", timeout_seconds=0.05)
    assert result.status is targets.PingStatus.TIMEOUT
    assert result.duration_ms < 500
