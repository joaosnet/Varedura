# Community 18

> 41 nodes · cohesion 0.11

## Key Concepts

- **test_network_diagnostics.py** (37 connections) — `tests/test_network_diagnostics.py`
- **ProxyConfiguration** (19 connections) — `monitor/network_diagnostics.py`
- **FakeBackend** (15 connections) — `tests/test_network_diagnostics.py`
- **_snapshot()** (15 connections) — `tests/test_network_diagnostics.py`
- **SnapshotCollector** (13 connections) — `monitor/network_diagnostics.py`
- **DiagnosticOptions** (12 connections) — `monitor/network_diagnostics.py`
- **_diagnose()** (11 connections) — `tests/test_network_diagnostics.py`
- **test_snapshot_cancels_while_psutil_enumeration_is_stalled()** (8 connections) — `tests/test_network_diagnostics.py`
- **_interface()** (7 connections) — `tests/test_network_diagnostics.py`
- **FakeCommandRunner** (6 connections) — `tests/test_network_diagnostics.py`
- **test_cancellation_is_reported_before_first_external_probe()** (6 connections) — `tests/test_network_diagnostics.py`
- **test_ipv6_only_snapshot_uses_ipv6_default_route()** (6 connections) — `tests/test_network_diagnostics.py`
- **test_linux_networkmanager_dhcp_method_is_collected()** (6 connections) — `tests/test_network_diagnostics.py`
- **test_macos_dhcp_configuration_is_collected_for_exact_service()** (6 connections) — `tests/test_network_diagnostics.py`
- **test_snapshot_bounds_a_stalled_psutil_enumeration()** (6 connections) — `tests/test_network_diagnostics.py`
- **test_snapshot_collector_parses_route_and_stays_offline_capable()** (6 connections) — `tests/test_network_diagnostics.py`
- **test_cancellation_is_preserved_even_when_snapshot_has_no_route()** (5 connections) — `tests/test_network_diagnostics.py`
- **test_fortigate_untrusted_block_certificate_is_specific_tls_policy_state()** (5 connections) — `tests/test_network_diagnostics.py`
- **test_linux_networkd_dhcp_client_is_collected()** (5 connections) — `tests/test_network_diagnostics.py`
- **test_pac_without_explicit_proxy_never_bypasses_policy()** (5 connections) — `tests/test_network_diagnostics.py`
- **test_policy_block_page_is_not_misclassified_as_captive_portal()** (5 connections) — `tests/test_network_diagnostics.py`
- **test_verified_https_through_explicit_proxy_is_online_managed()** (5 connections) — `tests/test_network_diagnostics.py`
- **test_active_link_without_default_route_is_local_only()** (4 connections) — `tests/test_network_diagnostics.py`
- **test_https_success_with_failed_icmp_is_online_not_offline()** (4 connections) — `tests/test_network_diagnostics.py`
- **test_no_active_interface_finishes_locally_without_external_probes()** (4 connections) — `tests/test_network_diagnostics.py`
- *... and 16 more nodes in this community*

## Relationships

- [Community 16](Community_16.md) (21 shared connections)
- [Community 41](Community_41.md) (10 shared connections)
- [Community 19](Community_19.md) (6 shared connections)
- [Community 29](Community_29.md) (6 shared connections)
- [Community 24](Community_24.md) (4 shared connections)
- [Community 1](Community_1.md) (2 shared connections)
- [Community 15](Community_15.md) (2 shared connections)
- [Community 30](Community_30.md) (1 shared connections)
- [Community 72](Community_72.md) (1 shared connections)
- [Community 66](Community_66.md) (1 shared connections)
- [Community 97](Community_97.md) (1 shared connections)
- [Community 54](Community_54.md) (1 shared connections)

## Source Files

- `monitor/network_diagnostics.py`
- `tests/test_network_diagnostics.py`

## Audit Trail

- EXTRACTED: 138 (94%)
- INFERRED: 9 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*