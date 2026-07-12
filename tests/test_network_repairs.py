"""Tests for safe repair enumeration, authorization and rollback behavior."""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from monitor.network_diagnostics import (
    CommandResult,
    Confidence,
    DiagnosisReport,
    Evidence,
    FailureCause,
    NetworkInterface,
    NetworkSnapshot,
    NetworkState,
    ProbeKind,
    ProbeResult,
    ProbeStatus,
    ProxyConfiguration,
)
from monitor.network_repairs import (
    RepairAction,
    RepairExecutor,
    RepairKind,
    RepairStatus,
    SubprocessRepairRunner,
    list_repair_actions,
    list_repair_guidance,
)


def _report(
    *,
    state=NetworkState.LIMITED,
    platform="windows",
    managed=False,
    pac=False,
    vpn=False,
    remote=False,
    interface=None,
    portal_url=None,
):
    iface = interface or NetworkInterface(
        "Ethernet",
        True,
        ipv4=("192.168.1.20",),
        stable_id="11111111-2222-3333-4444-555555555555",
    )
    proxy = ProxyConfiguration(
        pac_url="https://policy.example/proxy.pac" if pac else None
    )
    snapshot = NetworkSnapshot(
        datetime.now(timezone.utc),
        platform,
        (iface,),
        iface.name,
        "192.168.1.1",
        True,
        ("192.168.1.1",),
        proxy,
        vpn_active=vpn,
        managed_network=managed,
        dot1x_suspected=managed,
        remote_session=remote,
    )
    probes = [
        ProbeResult(ProbeKind.LINK, ProbeStatus.SUCCESS, 0),
        ProbeResult(ProbeKind.ROUTE, ProbeStatus.SUCCESS, 0),
    ]
    if portal_url:
        probes.append(
            ProbeResult(
                ProbeKind.CAPTIVE_PORTAL,
                ProbeStatus.FAILURE,
                1,
                FailureCause.CAPTIVE_PORTAL_DETECTED,
                details={"final_url": portal_url},
            )
        )
    now = datetime.now(timezone.utc)
    return DiagnosisReport(
        state,
        Confidence.LIKELY,
        "test",
        snapshot,
        tuple(probes),
        (Evidence("test", "test", Confidence.LIKELY),),
        now,
        now,
    )


def _action(report, kind, platform=None, **kwargs):
    return next(
        item
        for item in list_repair_actions(
            report,
            platform_name=platform,
            **kwargs,
        )
        if item.kind is kind
    )


class FakeRunner:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.calls = []

    def run(self, args, *, timeout, cancel_event=None, elevated=False):
        self.calls.append((tuple(args), elevated, cancel_event))
        if self.results:
            template = self.results.pop(0)
            return CommandResult(
                tuple(args),
                template.returncode,
                template.stdout,
                template.stderr,
                template.timed_out,
                template.cancelled,
            )
        return CommandResult(tuple(args), 0)


def test_managed_remote_and_vpn_networks_block_disruptive_actions():
    for report in (
        _report(managed=True),
        _report(pac=True),
        _report(vpn=True),
        _report(remote=True),
    ):
        actions = list_repair_actions(report, platform_name="windows")
        renew = next(item for item in actions if item.kind is RepairKind.RENEW_DHCP)
        reconnect = next(
            item for item in actions if item.kind is RepairKind.RECONNECT_INTERFACE
        )
        assert not renew.eligible and renew.blocked_reason
        assert not reconnect.eligible and reconnect.blocked_reason


def test_static_interface_never_offers_dhcp_renewal():
    interface = NetworkInterface(
        "Ethernet",
        True,
        ipv4=("192.168.1.20",),
        dhcp_enabled=False,
        stable_id="11111111-2222-3333-4444-555555555555",
    )
    report = _report(interface=interface)
    renew = _action(report, RepairKind.RENEW_DHCP, "windows")
    assert not renew.eligible
    assert "static" in renew.blocked_reason


def test_unknown_dhcp_state_is_ineligible_until_confirmed():
    interface = NetworkInterface(
        "Ethernet",
        True,
        ipv4=("192.168.1.20",),
        dhcp_enabled=None,
        stable_id="11111111-2222-3333-4444-555555555555",
    )
    report = _report(interface=interface)
    renew = _action(report, RepairKind.RENEW_DHCP, "windows")

    assert not renew.eligible
    assert "could not be confirmed" in renew.blocked_reason


def test_confirmed_dhcp_interface_is_eligible_for_renewal():
    interface = NetworkInterface(
        "Ethernet",
        True,
        ipv4=("192.168.1.20",),
        dhcp_enabled=True,
        stable_id="11111111-2222-3333-4444-555555555555",
    )
    report = _report(interface=interface)
    renew = _action(report, RepairKind.RENEW_DHCP, "windows")

    assert renew.eligible
    assert renew.blocked_reason is None


def test_each_mutating_action_requires_individual_confirmation():
    report = _report()
    runner = FakeRunner()
    action = _action(report, RepairKind.FLUSH_DNS, "windows")
    executor = RepairExecutor(platform_name="windows", runner=runner)

    result = executor.execute(action, report, confirmed=False)

    assert result.status is RepairStatus.NOT_CONFIRMED
    assert not runner.calls


def test_forged_action_is_rejected_without_running_commands():
    report = _report()
    runner = FakeRunner()
    forged = RepairAction(
        "forged",
        RepairKind.FLUSH_DNS,
        "forged",
        "forged",
        "system",
        "windows",
        command_preview=(("cmd.exe", "/c", "danger"),),
    )
    executor = RepairExecutor(platform_name="windows", runner=runner)

    result = executor.execute(forged, report, confirmed=True)

    assert result.status is RepairStatus.BLOCKED
    assert not runner.calls


def test_flush_dns_uses_fixed_shell_free_command_and_post_test():
    report = _report()
    runner = FakeRunner()
    post_calls = []
    action = _action(report, RepairKind.FLUSH_DNS, "windows")
    executor = RepairExecutor(
        platform_name="windows",
        runner=runner,
        post_test=lambda: post_calls.append(True) or report,
    )

    result = executor.execute(action, report, confirmed=True)

    assert result.status is RepairStatus.SUCCEEDED
    assert post_calls == [True]
    assert runner.calls[0][0] == ("varedura-network-helper", "flush_dns")
    assert result.post_report is report


def test_reconnect_always_runs_reactivation_in_finally_even_on_failure():
    report = _report()
    runner = FakeRunner([CommandResult(("disable",), 1), CommandResult(("enable",), 0)])
    action = _action(report, RepairKind.RECONNECT_INTERFACE, "windows")
    executor = RepairExecutor(platform_name="windows", runner=runner)

    result = executor.execute(action, report, confirmed=True)

    assert result.status is RepairStatus.FAILED
    assert len(runner.calls) == 2
    assert runner.calls[0][0][:2] == (
        "varedura-network-helper",
        "adapter_disable",
    )
    assert runner.calls[1][0][:2] == (
        "varedura-network-helper",
        "adapter_enable",
    )
    assert result.rollback_attempted
    assert result.rollback_succeeded


def test_windows_adapter_name_is_quoted_inside_exact_match_script():
    from monitor.network_repairs import _windows_elevated_script

    interface = NetworkInterface(
        "Wi-Fi'; Write-Output INJECTED; #",
        True,
        ipv4=("192.168.1.20",),
        stable_id="11111111-2222-3333-4444-555555555555",
    )
    report = _report(interface=interface)
    action = _action(report, RepairKind.RECONNECT_INTERFACE, "windows")
    disable = action.command_preview[0]
    assert disable == (
        "varedura-network-helper",
        "adapter_disable",
        interface.name,
        interface.stable_id,
    )
    script = _windows_elevated_script(
        "adapter_disable", interface.name, interface.stable_id
    )
    assert "$name='Wi-Fi''; Write-Output INJECTED; #'" in script
    assert "-ceq $name" in script


def test_reconnect_attempts_rollback_when_runner_raises_on_disconnect():
    report = _report()

    class RaisingRunner(FakeRunner):
        def run(self, args, **kwargs):
            self.calls.append((tuple(args), kwargs.get("elevated"), None))
            if len(self.calls) == 1:
                raise OSError("disconnect exploded")
            return CommandResult(tuple(args), 0)

    runner = RaisingRunner()
    action = _action(report, RepairKind.RECONNECT_INTERFACE, "windows")
    result = RepairExecutor(platform_name="windows", runner=runner).execute(
        action, report, confirmed=True
    )

    assert result.status is RepairStatus.FAILED
    assert len(runner.calls) == 2
    assert result.rollback_attempted
    assert result.rollback_succeeded


def test_linux_reconnect_uses_exact_uuid_and_checkpoint_restore():
    connection_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    interface = NetworkInterface(
        "eth0",
        True,
        ipv4=("192.168.1.20",),
        dhcp_enabled=True,
        connection_uuid=connection_uuid,
    )
    report = _report(interface=interface, platform="linux")
    runner = FakeRunner()
    action = _action(report, RepairKind.RECONNECT_INTERFACE, "linux")

    result = RepairExecutor(
        platform_name="linux",
        runner=runner,
        command_exists=lambda name: name if name == "nmcli" else None,
    ).execute(action, report, confirmed=True)

    assert result.status is RepairStatus.SUCCEEDED
    assert len(runner.calls) == 1
    command = runner.calls[0][0]
    assert command[:3] == ("nmcli", "device", "checkpoint")
    assert command[-3:] == ("down", "uuid", connection_uuid)
    assert "connect" not in command
    assert result.rollback_attempted
    assert result.rollback_succeeded


def test_networkmanager_checkpoint_receives_explicit_restore_answer(monkeypatch):
    import monitor.network_repairs as repairs

    written = []

    class FakeStdin:
        def write(self, value):
            written.append(value)

        def flush(self):
            return None

        def close(self):
            return None

    class FakeProcess:
        def __init__(self):
            self.stdin = FakeStdin()
            self.returncode = 0

        def poll(self):
            return 0

        def communicate(self, timeout=None):
            return "", ""

    monkeypatch.setattr(
        repairs.subprocess, "Popen", lambda *args, **kwargs: FakeProcess()
    )
    runner = SubprocessRepairRunner(platform_name="linux")
    command = (
        "nmcli",
        "device",
        "checkpoint",
        "--timeout",
        "20",
        "eth0",
        "--",
        "nmcli",
        "connection",
        "down",
        "uuid",
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )

    result = runner.run(command, timeout=1)

    assert result.returncode == 0
    assert written == ["No\n"]


def test_macos_dhcp_refresh_uses_protected_system_api_script():
    interface = NetworkInterface(
        "en0",
        True,
        ipv4=("192.168.1.20",),
        dhcp_enabled=True,
        service_name="Wi-Fi",
    )
    report = _report(interface=interface, platform="darwin")
    action = _action(report, RepairKind.RENEW_DHCP, "darwin")
    command = action.command_preview[0]

    assert command[:4] == ("/usr/bin/osascript", "-l", "JavaScript", "-e")
    assert "SCNetworkInterfaceForceConfigurationRefresh" in command[4]
    assert command[-1] == "en0"
    assert "monitor." not in " ".join(command)


def test_windows_helper_script_accepts_only_enumerated_operations():
    from monitor.network_repairs import _windows_elevated_script

    allowed = _windows_elevated_script("flush_dns")
    runner = SubprocessRepairRunner(platform_name="windows")
    blocked = runner.run(
        ("varedura-network-helper", "run_anything", "cmd.exe"),
        timeout=1,
        elevated=True,
    )

    assert "Clear-DnsClientCache" in allowed
    assert "monitor.network_repair_helper" not in allowed
    assert blocked.returncode is None
    assert "not-allowed" in blocked.stderr


def test_windows_renew_script_rejects_wildcards_and_checks_ipv6_exit():
    from monitor.network_repairs import _windows_elevated_script

    stable_id = "11111111-2222-3333-4444-555555555555"
    script = _windows_elevated_script("renew_dhcp", "Ethernet", stable_id)
    assert "IpRenewAddress" in script
    assert "LASTEXITCODE" in script
    assert "monitor.network_repair_helper" not in script

    try:
        _windows_elevated_script("renew_dhcp", "Eth*", stable_id)
    except ValueError as exc:
        assert "wildcards" in str(exc)
    else:
        raise AssertionError("ipconfig wildcard scope must be rejected")


def test_pre_cancelled_action_has_no_side_effects():
    report = _report()
    runner = FakeRunner()
    action = _action(report, RepairKind.FLUSH_DNS, "windows")
    cancel = threading.Event()
    cancel.set()

    result = RepairExecutor(platform_name="windows", runner=runner).execute(
        action,
        report,
        confirmed=True,
        cancel_event=cancel,
    )

    assert result.status is RepairStatus.CANCELLED
    assert not runner.calls


def test_recent_preflight_blocks_when_vpn_appears_after_diagnosis():
    report = _report()
    fresh_report = _report(vpn=True)
    runner = FakeRunner()
    action = _action(report, RepairKind.RECONNECT_INTERFACE, "windows")
    executor = RepairExecutor(
        platform_name="windows",
        runner=runner,
        preflight_snapshot=lambda: fresh_report.snapshot,
    )

    result = executor.execute(action, report, confirmed=True)

    assert result.status is RepairStatus.BLOCKED
    assert "Recent preflight" in result.message
    assert not runner.calls


def test_recent_preflight_rechecks_dhcp_before_renewal():
    stable_id = "11111111-2222-3333-4444-555555555555"
    original = NetworkInterface(
        "Ethernet",
        True,
        ipv4=("192.168.1.20",),
        dhcp_enabled=True,
        stable_id=stable_id,
    )
    changed = NetworkInterface(
        "Ethernet",
        True,
        ipv4=("192.168.1.20",),
        dhcp_enabled=False,
        stable_id=stable_id,
    )
    report = _report(interface=original)
    fresh_report = _report(interface=changed)
    runner = FakeRunner()
    action = _action(report, RepairKind.RENEW_DHCP, "windows")
    executor = RepairExecutor(
        platform_name="windows",
        runner=runner,
        preflight_snapshot=lambda: fresh_report.snapshot,
    )

    result = executor.execute(action, report, confirmed=True)

    assert result.status is RepairStatus.BLOCKED
    assert "could not confirm DHCP" in result.message
    assert not runner.calls


def test_captive_portal_url_is_sanitized_before_browser_open():
    report = _report(
        state=NetworkState.CAPTIVE_PORTAL,
        portal_url="http://user:password@portal.example/login?next=1#secret",
    )
    opened = []
    action = _action(report, RepairKind.OPEN_CAPTIVE_PORTAL, "windows")
    executor = RepairExecutor(
        platform_name="windows",
        runner=FakeRunner(),
        browser_open=lambda url: opened.append(url) or True,
    )

    result = executor.execute(action, report, confirmed=True)

    assert result.status is RepairStatus.SUCCEEDED
    assert opened == ["http://portal.example/login?next=1"]


def test_invalid_app_ca_never_changes_system_trust(tmp_path):
    report = _report(state=NetworkState.TLS_POLICY_BLOCKED)
    invalid = tmp_path / "not-a-ca.txt"
    invalid.write_text("not a certificate", encoding="utf-8")
    action = _action(
        report,
        RepairKind.CONFIGURE_APP_CA,
        "windows",
        app_ca_file=str(invalid),
    )

    result = RepairExecutor(platform_name="windows", runner=FakeRunner()).execute(
        action,
        report,
        confirmed=True,
    )

    assert result.status is RepairStatus.FAILED
    assert result.app_ca_file is None


def _fake_der_certificate(*, ca: bool) -> bytes:
    def tlv(tag: int, value: bytes) -> bytes:
        assert len(value) < 128
        return bytes((tag, len(value))) + value

    constraints = tlv(0x30, tlv(0x01, b"\xff" if ca else b"\x00"))
    extension = tlv(
        0x30,
        tlv(0x06, b"\x55\x1d\x13") + tlv(0x04, constraints),
    )
    return tlv(0x30, extension)


def test_app_ca_is_single_ca_and_copied_to_fingerprint_store(monkeypatch, tmp_path):
    import monitor.network_repairs as repairs

    source = tmp_path / "institution.pem"
    source.write_text(
        repairs.ssl.DER_cert_to_PEM_cert(_fake_der_certificate(ca=True)),
        encoding="ascii",
    )
    monkeypatch.setattr(
        repairs.ssl, "create_default_context", lambda **_kwargs: object()
    )
    store = tmp_path / "app-store"

    stored_value = repairs._validate_app_ca(
        str(source),
        store_directory=store,
    )
    stored = Path(stored_value)
    original = stored.read_bytes()
    source.write_text("replaced after consent", encoding="utf-8")

    assert stored.parent == store
    assert len(stored.stem) == 64
    assert stored.suffix == ".pem"
    assert stored.read_bytes() == original


def test_app_ca_rejects_bundle_and_non_ca_basic_constraints(monkeypatch, tmp_path):
    import monitor.network_repairs as repairs

    monkeypatch.setattr(
        repairs.ssl, "create_default_context", lambda **_kwargs: object()
    )
    leaf_pem = repairs.ssl.DER_cert_to_PEM_cert(_fake_der_certificate(ca=False))
    leaf = tmp_path / "leaf.pem"
    leaf.write_text(leaf_pem, encoding="ascii")
    bundle = tmp_path / "bundle.pem"
    bundle.write_text(leaf_pem + leaf_pem, encoding="ascii")

    for candidate, marker in (
        (leaf, "BasicConstraints"),
        (bundle, "bundles"),
    ):
        try:
            repairs._validate_app_ca(
                str(candidate),
                store_directory=tmp_path / "store",
            )
        except ValueError as exc:
            assert marker in str(exc)
        else:
            raise AssertionError(f"{candidate.name} must be rejected")


def test_app_ca_requires_successful_online_postcheck(monkeypatch, tmp_path):
    import monitor.network_repairs as repairs

    report = _report(state=NetworkState.TLS_POLICY_BLOCKED)
    candidate = tmp_path / "candidate.pem"
    candidate.write_text("validated by test double", encoding="utf-8")
    stored = str(tmp_path / "stored.pem")
    monkeypatch.setattr(repairs, "_validate_app_ca", lambda *args, **kwargs: stored)
    action = _action(
        report,
        RepairKind.CONFIGURE_APP_CA,
        "windows",
        app_ca_file=str(candidate),
    )

    for post_report in (
        replace(report, cancelled=True),
        report,
    ):
        result = RepairExecutor(
            platform_name="windows",
            runner=FakeRunner(),
            post_test=lambda post_report=post_report: post_report,
        ).execute(action, report, confirmed=True)
        assert result.status is RepairStatus.POSTCHECK_FAILED
        assert result.app_ca_file is None

    online = _report(state=NetworkState.ONLINE_MANAGED)
    result = RepairExecutor(
        platform_name="windows",
        runner=FakeRunner(),
        post_test=lambda: online,
    ).execute(action, report, confirmed=True)
    assert result.status is RepairStatus.SUCCEEDED
    assert result.app_ca_file == stored


def test_fortinet_untrusted_ca_marker_is_explicitly_rejected(tmp_path):
    from monitor.network_repairs import _validate_app_ca

    candidate = tmp_path / "Fortinet_CA_Untrusted.pem"
    candidate.write_text("Fortinet_CA_Untrusted", encoding="utf-8")
    try:
        _validate_app_ca(str(candidate))
    except ValueError as exc:
        assert "must never be trusted" in str(exc)
    else:
        raise AssertionError("Fortinet_CA_Untrusted must be rejected")


def test_guidance_forbids_fortinet_untrusted_and_global_resets():
    guidance = list_repair_guidance(_report())
    text = " ".join(f"{item.title} {item.explanation}" for item in guidance)

    assert "Fortinet_CA_Untrusted" in text
    assert "Winsock" in text
    assert "firewall" in text
