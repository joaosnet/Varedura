"""Deterministic tests for the layered, policy-aware diagnostic engine."""

from __future__ import annotations

import socket
import threading
import time
import types
from datetime import datetime, timezone

from monitor import network_diagnostics as nd


def _interface(name="Ethernet", *, up=True, ipv4=("192.168.1.10",)):
    return nd.NetworkInterface(name=name, is_up=up, ipv4=ipv4)


def _snapshot(
    *,
    interface=True,
    route=True,
    apipa=False,
    proxy=None,
    managed=False,
    vpn=False,
    remote=False,
):
    interfaces = (_interface(),) if interface else ()
    return nd.NetworkSnapshot(
        captured_at=datetime.now(timezone.utc),
        platform="windows",
        interfaces=interfaces,
        active_interface="Ethernet" if interface else None,
        default_gateway="192.168.1.1" if route else None,
        route_present=route,
        dns_servers=("192.168.1.1",),
        proxy=proxy or nd.ProxyConfiguration(),
        apipa=apipa,
        managed_network=managed,
        vpn_active=vpn,
        remote_session=remote,
    )


class FakeBackend:
    def __init__(self, *, https=None, captive=None, ping_code=0):
        self.https = https or nd.HttpObservation(200, "https://www.microsoft.com/")
        self.captive = captive or nd.HttpObservation(
            200,
            "http://www.msftconnecttest.com/connecttest.txt",
            "Microsoft Connect Test",
        )
        self.ping_code = ping_code
        self.calls = []

    def resolve(self, host, *, timeout, cancel_event):
        self.calls.append(("dns", host))
        return ("203.0.113.10",)

    def tcp_connect(self, host, port, *, timeout, cancel_event):
        self.calls.append(("tcp", host, port))

    def http_get(
        self,
        url,
        *,
        proxies,
        timeout,
        cancel_event,
        ca_file=None,
    ):
        self.calls.append(("http", url, dict(proxies), ca_file))
        return self.https if url.startswith("https://") else self.captive

    def ping(self, host, *, timeout, cancel_event):
        self.calls.append(("ping", host))
        return nd.CommandResult(("ping", host), self.ping_code)


def _diagnose(snapshot, backend, **option_overrides):
    values = {
        "overall_timeout": 1.0,
        "snapshot_timeout": 0.1,
        "per_probe_timeout": 0.1,
    }
    values.update(option_overrides)
    engine = nd.NetworkDiagnosticEngine(probe_backend=backend)
    return engine.diagnose(snapshot=snapshot, options=nd.DiagnosticOptions(**values))


def test_https_success_with_failed_icmp_is_online_not_offline():
    report = _diagnose(_snapshot(), FakeBackend(ping_code=1))

    assert report.state is nd.NetworkState.ONLINE
    assert report.confidence is nd.Confidence.CONFIRMED
    assert (
        report.probe(nd.ProbeKind.ICMP).cause
        is nd.FailureCause.ICMP_FILTERED_OR_UNSUPPORTED
    )
    assert any(item.code == "icmp-filtered" for item in report.evidence)


def test_verified_https_through_explicit_proxy_is_online_managed():
    proxy = nd.ProxyConfiguration((("https", "http://proxy.example:8080"),))
    backend = FakeBackend()

    report = _diagnose(_snapshot(proxy=proxy, managed=True), backend)

    assert report.state is nd.NetworkState.ONLINE_MANAGED
    assert ("tcp", "proxy.example", 8080) in backend.calls
    http_calls = [call for call in backend.calls if call[0] == "http"]
    assert http_calls and http_calls[0][2] == {"https": "http://proxy.example:8080"}


def test_verified_https_with_confirmed_app_ca_is_online_managed():
    probes = [
        nd.ProbeResult(nd.ProbeKind.LINK, nd.ProbeStatus.SUCCESS, 0),
        nd.ProbeResult(nd.ProbeKind.ROUTE, nd.ProbeStatus.SUCCESS, 0),
        nd.ProbeResult(
            nd.ProbeKind.HTTPS,
            nd.ProbeStatus.SUCCESS,
            1,
            details={"app_ca": True},
        ),
    ]
    state, confidence, *_ = nd.classify_diagnosis(_snapshot(), probes)
    assert state is nd.NetworkState.ONLINE_MANAGED
    assert confidence is nd.Confidence.CONFIRMED


def test_pac_without_explicit_proxy_never_bypasses_policy():
    proxy = nd.ProxyConfiguration(pac_url="https://policy.example/proxy.pac")
    backend = FakeBackend()

    report = _diagnose(
        _snapshot(proxy=proxy, managed=True),
        backend,
        enable_icmp=False,
    )

    assert report.state is nd.NetworkState.UNKNOWN
    assert [call[0] for call in backend.calls] == ["dns"]
    assert report.probe(nd.ProbeKind.TCP).status is nd.ProbeStatus.SKIPPED
    assert report.probe(nd.ProbeKind.HTTPS).cause is nd.FailureCause.PAC_UNAVAILABLE


def test_fortigate_untrusted_block_certificate_is_specific_tls_policy_state():
    https = nd.HttpObservation(
        None,
        "https://www.microsoft.com/",
        error="certificate verify failed: Fortinet_CA_Untrusted",
    )
    report = _diagnose(_snapshot(managed=True), FakeBackend(https=https))

    assert report.state is nd.NetworkState.TLS_POLICY_BLOCKED
    assert report.confidence is nd.Confidence.CONFIRMED
    assert (
        report.probe(nd.ProbeKind.HTTPS).cause is nd.FailureCause.FORTIGATE_BLOCK_CERT
    )


def test_policy_block_page_is_not_misclassified_as_captive_portal():
    blocked = nd.HttpObservation(
        403,
        "http://www.msftconnecttest.com/connecttest.txt",
        body="Access denied by institutional policy",
    )
    report = _diagnose(_snapshot(managed=True), FakeBackend(captive=blocked))

    assert report.state is nd.NetworkState.POLICY_BLOCKED
    assert (
        report.probe(nd.ProbeKind.CAPTIVE_PORTAL).cause
        is nd.FailureCause.POLICY_BLOCKED
    )


def test_no_active_interface_finishes_locally_without_external_probes():
    backend = FakeBackend()

    report = _diagnose(_snapshot(interface=False, route=False), backend)

    assert report.state is nd.NetworkState.OFFLINE
    assert report.confidence is nd.Confidence.CONFIRMED
    assert not backend.calls


def test_active_link_without_default_route_is_local_only():
    report = _diagnose(_snapshot(route=False), FakeBackend())

    assert report.state is nd.NetworkState.LOCAL_ONLY
    assert report.probe(nd.ProbeKind.ROUTE).cause is nd.FailureCause.NO_DEFAULT_ROUTE


def test_total_external_transport_failure_is_offline():
    probes = [
        nd.ProbeResult(nd.ProbeKind.LINK, nd.ProbeStatus.SUCCESS, 0),
        nd.ProbeResult(nd.ProbeKind.ROUTE, nd.ProbeStatus.SUCCESS, 0),
        nd.ProbeResult(
            nd.ProbeKind.DNS,
            nd.ProbeStatus.FAILURE,
            1,
            nd.FailureCause.DNS_RESOLUTION_FAILED,
        ),
        nd.ProbeResult(
            nd.ProbeKind.TCP,
            nd.ProbeStatus.TIMED_OUT,
            1,
            nd.FailureCause.TIMEOUT,
        ),
        nd.ProbeResult(
            nd.ProbeKind.CAPTIVE_PORTAL,
            nd.ProbeStatus.FAILURE,
            1,
            nd.FailureCause.INCONCLUSIVE,
        ),
        nd.ProbeResult(
            nd.ProbeKind.HTTPS,
            nd.ProbeStatus.FAILURE,
            1,
            nd.FailureCause.INCONCLUSIVE,
        ),
    ]
    state, confidence, *_ = nd.classify_diagnosis(_snapshot(), probes)
    assert state is nd.NetworkState.OFFLINE
    assert confidence is nd.Confidence.LIKELY


def test_cancellation_is_reported_before_first_external_probe():
    cancel = threading.Event()
    cancel.set()
    backend = FakeBackend()
    engine = nd.NetworkDiagnosticEngine(probe_backend=backend)

    report = engine.diagnose(
        snapshot=_snapshot(),
        options=nd.DiagnosticOptions(overall_timeout=1, per_probe_timeout=0.1),
        cancel_event=cancel,
    )

    assert report.cancelled
    assert not backend.calls
    assert any(probe.status is nd.ProbeStatus.CANCELLED for probe in report.probes)


def test_cancellation_is_preserved_even_when_snapshot_has_no_route():
    cancel = threading.Event()
    cancel.set()
    report = nd.NetworkDiagnosticEngine(probe_backend=FakeBackend()).diagnose(
        snapshot=_snapshot(route=False),
        options=nd.DiagnosticOptions(overall_timeout=1, per_probe_timeout=0.1),
        cancel_event=cancel,
    )
    assert report.cancelled
    assert any(probe.status is nd.ProbeStatus.CANCELLED for probe in report.probes)


def test_proxy_url_credentials_are_redacted_and_not_retained():
    value, had_credentials = nd._sanitize_proxy_url(
        "http://sensitive-user:sensitive-password@proxy.example:3128"
    )

    assert had_credentials
    assert value == "http://proxy.example:3128"
    assert "sensitive" not in value


def test_pac_url_credentials_are_redacted_without_losing_query():
    value, had_credentials = nd._sanitize_pac_url(
        "https://user:secret@policy.example/proxy.pac?site=branch#fragment"
    )
    assert had_credentials
    assert value == "https://policy.example/proxy.pac?site=branch"
    assert "secret" not in value


class FakeCommandRunner:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def run(self, args, *, timeout, cancel_event=None):
        self.calls.append(tuple(args))
        return nd.CommandResult(tuple(args), 0, stdout=self.output)


def test_snapshot_collector_parses_route_and_stays_offline_capable(monkeypatch):
    interface = _interface(name="eth0", ipv4=("10.0.0.20",))
    monkeypatch.setattr(nd, "_interface_addresses", lambda: (interface,))
    monkeypatch.setattr(nd, "_read_dns_resolv_conf", lambda: ("10.0.0.53",))
    monkeypatch.setattr(
        nd,
        "_collect_proxy_configuration",
        lambda system, environ, **kwargs: nd.ProxyConfiguration(),
    )
    monkeypatch.setattr(
        nd, "_process_security_flags", lambda cancel_event=None: (False, False)
    )
    runner = FakeCommandRunner("default via 10.0.0.1 dev eth0 proto dhcp\n")
    collector = nd.SnapshotCollector(
        command_runner=runner,
        platform_name="linux",
        environ={},
        command_exists=lambda _name: None,
    )

    snapshot = collector.collect(timeout=0.5)

    assert snapshot.active_interface == "eth0"
    assert snapshot.default_gateway == "10.0.0.1"
    assert snapshot.route_present
    assert snapshot.dns_servers == ("10.0.0.53",)
    assert runner.calls == [("ip", "route", "show", "default")]


def test_ipv6_only_snapshot_uses_ipv6_default_route(monkeypatch):
    interface = nd.NetworkInterface(
        name="eth0",
        is_up=True,
        ipv6=("2001:db8::20",),
    )
    monkeypatch.setattr(nd, "_interface_addresses", lambda: (interface,))
    monkeypatch.setattr(nd, "_read_dns_resolv_conf", lambda: ("2001:4860:4860::8888",))
    monkeypatch.setattr(
        nd,
        "_collect_proxy_configuration",
        lambda system, environ, **kwargs: nd.ProxyConfiguration(),
    )
    monkeypatch.setattr(
        nd, "_process_security_flags", lambda cancel_event=None: (False, False)
    )

    class IPv6Runner:
        def __init__(self):
            self.calls = []

        def run(self, args, **kwargs):
            command = tuple(args)
            self.calls.append(command)
            output = (
                "default via fe80::1 dev eth0 metric 10\n" if "-6" in command else ""
            )
            return nd.CommandResult(command, 0, stdout=output)

    runner = IPv6Runner()
    snapshot = nd.SnapshotCollector(
        command_runner=runner,
        platform_name="linux",
        environ={},
        command_exists=lambda _name: None,
    ).collect(timeout=0.5)

    assert snapshot.ipv6_only
    assert snapshot.route_present
    assert snapshot.default_gateway == "fe80::1"
    assert runner.calls[:2] == [
        ("ip", "route", "show", "default"),
        ("ip", "-6", "route", "show", "default"),
    ]


def test_interface_collection_handles_psutil_records(monkeypatch):
    address = types.SimpleNamespace(
        family=socket.AF_INET,
        address="192.168.50.4",
    )
    stats = types.SimpleNamespace(isup=True, mtu=1500, speed=1000)
    monkeypatch.setattr(nd.psutil, "net_if_addrs", lambda: {"lan0": [address]})
    monkeypatch.setattr(nd.psutil, "net_if_stats", lambda: {"lan0": stats})

    interfaces = nd._interface_addresses()

    assert interfaces[0].name == "lan0"
    assert interfaces[0].ipv4 == ("192.168.50.4",)
    assert interfaces[0].is_up


def test_snapshot_bounds_a_stalled_psutil_enumeration(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    def stalled_interfaces():
        entered.set()
        release.wait(1)
        return ()

    monkeypatch.setattr(nd, "_interface_addresses", stalled_interfaces)
    monkeypatch.setattr(
        nd,
        "_collect_proxy_configuration",
        lambda system, environ, **kwargs: nd.ProxyConfiguration(),
    )
    monkeypatch.setattr(
        nd, "_process_security_flags", lambda cancel_event=None: (False, False)
    )
    runner = FakeCommandRunner("")
    collector = nd.SnapshotCollector(
        command_runner=runner,
        platform_name="linux",
        environ={},
        command_exists=lambda _name: None,
    )

    started = time.monotonic()
    snapshot = collector.collect(timeout=0.08)
    elapsed = time.monotonic() - started
    release.set()

    assert entered.is_set()
    assert elapsed < 0.3
    assert not snapshot.interfaces
    assert "interface-enumeration-timeout" in snapshot.command_errors


def test_snapshot_cancels_while_psutil_enumeration_is_stalled(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    cancel = threading.Event()

    def stalled_interfaces():
        entered.set()
        release.wait(1)
        return ()

    def cancel_after_start():
        entered.wait(0.5)
        cancel.set()

    monkeypatch.setattr(nd, "_interface_addresses", stalled_interfaces)
    monkeypatch.setattr(
        nd,
        "_collect_proxy_configuration",
        lambda system, environ, **kwargs: nd.ProxyConfiguration(),
    )
    monkeypatch.setattr(
        nd, "_process_security_flags", lambda cancel_event=None: (False, False)
    )
    trigger = threading.Thread(target=cancel_after_start, daemon=True)
    trigger.start()
    runner = FakeCommandRunner("")
    collector = nd.SnapshotCollector(
        command_runner=runner,
        platform_name="linux",
        environ={},
        command_exists=lambda _name: None,
    )

    started = time.monotonic()
    snapshot = collector.collect(timeout=1, cancel_event=cancel)
    elapsed = time.monotonic() - started
    release.set()
    trigger.join(timeout=0.2)

    assert elapsed < 0.3
    assert not runner.calls
    assert "interface-enumeration-cancelled" in snapshot.command_errors


def test_linux_networkmanager_dhcp_method_is_collected(monkeypatch):
    interface = _interface(name="eth0", ipv4=("10.0.0.20",))
    monkeypatch.setattr(nd, "_interface_addresses", lambda: (interface,))
    monkeypatch.setattr(nd, "_read_dns_resolv_conf", lambda: ("10.0.0.53",))
    monkeypatch.setattr(
        nd,
        "_collect_proxy_configuration",
        lambda system, environ, **kwargs: nd.ProxyConfiguration(),
    )
    monkeypatch.setattr(
        nd, "_process_security_flags", lambda cancel_event=None: (False, False)
    )
    profile_uuid = "11111111-2222-3333-4444-555555555555"

    class NetworkManagerRunner:
        def run(self, args, **kwargs):
            command = tuple(args)
            if command[:3] == ("ip", "route", "show"):
                output = "default via 10.0.0.1 dev eth0\n"
            elif "--active" in command:
                output = f"{profile_uuid}:eth0\n"
            elif "ipv4.method" in command:
                output = "auto\n"
            else:
                output = ""
            return nd.CommandResult(command, 0, stdout=output)

    snapshot = nd.SnapshotCollector(
        command_runner=NetworkManagerRunner(),
        platform_name="linux",
        environ={},
        command_exists=lambda name: name if name == "nmcli" else None,
    ).collect(timeout=1)

    assert snapshot.selected_interface is not None
    assert snapshot.selected_interface.dhcp_enabled is True
    assert snapshot.selected_interface.connection_uuid == profile_uuid
    assert nd._parse_nm_ipv4_method("manual\n") is False


def test_linux_networkd_dhcp_client_is_collected(monkeypatch):
    interface = _interface(name="eth0", ipv4=("10.0.0.20",))
    monkeypatch.setattr(nd, "_interface_addresses", lambda: (interface,))
    monkeypatch.setattr(nd, "_read_dns_resolv_conf", lambda: ("10.0.0.53",))
    monkeypatch.setattr(nd.socket, "if_nametoindex", lambda _name: 2)
    monkeypatch.setattr(
        nd,
        "_collect_proxy_configuration",
        lambda system, environ, **kwargs: nd.ProxyConfiguration(),
    )
    monkeypatch.setattr(
        nd, "_process_security_flags", lambda cancel_event=None: (False, False)
    )

    class NetworkdRunner:
        def run(self, args, **kwargs):
            command = tuple(args)
            output = (
                "default via 10.0.0.1 dev eth0\n"
                if command[0] == "ip"
                else 's "bound"\n'
            )
            return nd.CommandResult(command, 0, stdout=output)

    snapshot = nd.SnapshotCollector(
        command_runner=NetworkdRunner(),
        platform_name="linux",
        environ={},
        command_exists=lambda name: name if name == "busctl" else None,
    ).collect(timeout=1)

    assert snapshot.selected_interface is not None
    assert snapshot.selected_interface.dhcp_enabled is True


def test_macos_dhcp_configuration_is_collected_for_exact_service(monkeypatch):
    interface = _interface(name="en0", ipv4=("10.0.0.20",))
    monkeypatch.setattr(nd, "_interface_addresses", lambda: (interface,))
    monkeypatch.setattr(
        nd,
        "_collect_proxy_configuration",
        lambda system, environ, **kwargs: nd.ProxyConfiguration(),
    )
    monkeypatch.setattr(
        nd, "_process_security_flags", lambda cancel_event=None: (False, False)
    )

    class MacOSRunner:
        def run(self, args, **kwargs):
            command = tuple(args)
            if command[0] == "route":
                output = "gateway: 10.0.0.1\ninterface: en0\n"
            elif command == ("scutil", "--dns"):
                output = "nameserver[0] : 10.0.0.53\n"
            elif command == ("networksetup", "-listnetworkserviceorder"):
                output = "(1) Wi-Fi\n(Hardware Port: Wi-Fi, Device: en0)\n"
            else:
                assert command == ("networksetup", "-getinfo", "Wi-Fi")
                output = "DHCP Configuration\nIP address: 10.0.0.20\n"
            return nd.CommandResult(command, 0, stdout=output)

    snapshot = nd.SnapshotCollector(
        command_runner=MacOSRunner(),
        platform_name="darwin",
        environ={},
    ).collect(timeout=1)

    assert snapshot.selected_interface is not None
    assert snapshot.selected_interface.service_name == "Wi-Fi"
    assert snapshot.selected_interface.dhcp_enabled is True
    assert nd._parse_macos_dhcp_configuration("Manual Configuration\n") is False


def test_macos_service_mapping_uses_exact_bsd_device():
    output = """
(1) Wi-Fi
(Hardware Port: Wi-Fi, Device: en0)
(2) USB 10/100/1000 LAN
(Hardware Port: USB LAN, Device: en5)
"""
    assert nd._parse_macos_network_services(output) == {
        "en0": "Wi-Fi",
        "en5": "USB 10/100/1000 LAN",
    }


def test_windows_combined_payload_parses_dns_and_dhcp():
    payload = (
        '{"Dns":[{"InterfaceAlias":"Ethernet",'
        '"ServerAddresses":["10.0.0.53"]}],'
        '"Interfaces":[{"InterfaceAlias":"Ethernet","Dhcp":1},'
        '{"InterfaceAlias":"Static","Dhcp":0}],'
        '"Adapters":[{"Name":"Ethernet",'
        '"InterfaceGuid":"11111111-2222-3333-4444-555555555555"}]}'
    )
    assert nd._parse_windows_dns(payload) == ("10.0.0.53",)
    assert nd._parse_windows_dhcp(payload) == {"Ethernet": True, "Static": False}
    assert nd._parse_windows_adapter_ids(payload) == {
        "Ethernet": "11111111-2222-3333-4444-555555555555"
    }


def test_route_parser_selects_lowest_metric_and_dns_filters_active_interface():
    routes = (
        "default via 10.0.0.1 dev eth0 metric 500\n"
        "default via 192.168.1.1 dev wlan0 metric 20\n"
    )
    gateway, interface, present = nd._parse_route("linux", routes, ())
    assert (gateway, interface, present) == ("192.168.1.1", "wlan0", True)

    payload = (
        '{"Dns":[{"InterfaceAlias":"Corp",'
        '"ServerAddresses":["10.0.0.53"]},{"InterfaceAlias":"Home",'
        '"ServerAddresses":["192.168.1.1"]}]}'
    )
    assert nd._parse_windows_dns(payload, interface_name="Corp") == ("10.0.0.53",)
