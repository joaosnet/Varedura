# Community 41

> 25 nodes · cohesion 0.11

## Key Concepts

- **.collect()** (23 connections) — `monitor/network_diagnostics.py`
- **ipaddress** (20 connections)
- **psutil** (15 connections)
- **_interface_addresses()** (8 connections) — `monitor/network_diagnostics.py`
- **_parse_route()** (8 connections) — `monitor/network_diagnostics.py`
- **_valid_ip()** (7 connections) — `monitor/network_diagnostics.py`
- **_parse_windows_dns()** (6 connections) — `monitor/network_diagnostics.py`
- **_valid_legacy_host()** (5 connections) — `cli/ui_shared.py`
- **_parse_macos_network_services()** (5 connections) — `monitor/network_diagnostics.py`
- **_parse_windows_adapter_ids()** (5 connections) — `monitor/network_diagnostics.py`
- **_parse_macos_dhcp_configuration()** (4 connections) — `monitor/network_diagnostics.py`
- **_parse_scutil_dns()** (4 connections) — `monitor/network_diagnostics.py`
- **_parse_windows_dhcp()** (4 connections) — `monitor/network_diagnostics.py`
- **_process_security_flags()** (4 connections) — `monitor/network_diagnostics.py`
- **test_windows_combined_payload_parses_dns_and_dhcp()** (4 connections) — `tests/test_network_diagnostics.py`
- **_read_dns_resolv_conf()** (3 connections) — `monitor/network_diagnostics.py`
- **test_route_parser_selects_lowest_metric_and_dns_filters_active_interface()** (3 connections) — `tests/test_network_diagnostics.py`
- **_default_route_command()** (2 connections) — `monitor/network_diagnostics.py`
- **_windows_dns_command()** (2 connections) — `monitor/network_diagnostics.py`
- **test_interface_collection_handles_psutil_records()** (2 connections) — `tests/test_network_diagnostics.py`
- **test_macos_service_mapping_uses_exact_bsd_device()** (2 connections) — `tests/test_network_diagnostics.py`
- **Cheap, resolution-free migration guard kept outside monitor imports.** (1 connections) — `cli/ui_shared.py`
- **metric()** (1 connections) — `monitor/network_diagnostics.py`
- **Map BSD device names to exact networksetup service names.** (1 connections) — `monitor/network_diagnostics.py`
- **Interpret the configuration heading emitted by ``networksetup -getinfo``.** (1 connections) — `monitor/network_diagnostics.py`

## Relationships

- [Community 16](Community_16.md) (17 shared connections)
- [Community 18](Community_18.md) (10 shared connections)
- [Community 12](Community_12.md) (6 shared connections)
- [Community 2](Community_2.md) (5 shared connections)
- [Community 19](Community_19.md) (5 shared connections)
- [Community 15](Community_15.md) (4 shared connections)
- [Community 66](Community_66.md) (4 shared connections)
- [Community 13](Community_13.md) (3 shared connections)
- [Community 33](Community_33.md) (3 shared connections)
- [Community 0](Community_0.md) (2 shared connections)
- [Community 11](Community_11.md) (2 shared connections)
- [Community 85](Community_85.md) (2 shared connections)

## Source Files

- `cli/ui_shared.py`
- `monitor/network_diagnostics.py`
- `tests/test_network_diagnostics.py`

## Audit Trail

- EXTRACTED: 103 (96%)
- INFERRED: 4 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*