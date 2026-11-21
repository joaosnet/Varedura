# Community 52

> 22 nodes · cohesion 0.17

## Key Concepts

- **detect_default_gateway()** (12 connections) — `monitor/netinfo.py`
- **platform** (12 connections)
- **netinfo.py** (11 connections) — `monitor/netinfo.py`
- **test_netinfo.py** (10 connections) — `tests/test_netinfo.py`
- **_patch_run()** (8 connections) — `tests/test_netinfo.py`
- **_detect_unix()** (7 connections) — `monitor/netinfo.py`
- **_detect_windows()** (6 connections) — `monitor/netinfo.py`
- **_run()** (6 connections) — `monitor/netinfo.py`
- **test_detect_default_gateway_dispatches_by_platform()** (3 connections) — `tests/test_netinfo.py`
- **test_detect_default_gateway_returns_none_on_total_failure()** (3 connections) — `tests/test_netinfo.py`
- **test_detect_unix_falls_back_to_netstat()** (3 connections) — `tests/test_netinfo.py`
- **test_detect_unix_prefers_ip_route()** (3 connections) — `tests/test_netinfo.py`
- **test_detect_windows_none_when_no_valid_route()** (3 connections) — `tests/test_netinfo.py`
- **test_detect_windows_picks_lowest_valid_metric()** (3 connections) — `tests/test_netinfo.py`
- **_is_windows_admin()** (2 connections) — `monitor/network_repairs.py`
- **Lightweight network information helpers (gateway autodetection).** (1 connections) — `monitor/netinfo.py`
- **Run a command quietly and return stdout (empty string on failure).** (1 connections) — `monitor/netinfo.py`
- **Parse `route print` for the default route (locale-independent).** (1 connections) — `monitor/netinfo.py`
- **Parse `ip route` (Linux/Android) or `netstat -rn` (macOS/BSD).** (1 connections) — `monitor/netinfo.py`
- **Best-effort detection of the default gateway IP, or None if unknown.** (1 connections) — `monitor/netinfo.py`
- **fake_run()** (1 connections) — `tests/test_netinfo.py`
- **Tests for monitor.netinfo default-gateway detection (subprocess mocked).** (1 connections) — `tests/test_netinfo.py`

## Relationships

- [Community 12](Community_12.md) (5 shared connections)
- [Community 15](Community_15.md) (3 shared connections)
- [Community 99](Community_99.md) (2 shared connections)
- [Community 1](Community_1.md) (2 shared connections)
- [Community 16](Community_16.md) (2 shared connections)
- [Community 11](Community_11.md) (2 shared connections)
- [Community 73](Community_73.md) (1 shared connections)
- [Community 30](Community_30.md) (1 shared connections)
- [Community 2](Community_2.md) (1 shared connections)
- [Community 6](Community_6.md) (1 shared connections)
- [Community 97](Community_97.md) (1 shared connections)

## Source Files

- `monitor/netinfo.py`
- `monitor/network_repairs.py`
- `tests/test_netinfo.py`

## Audit Trail

- EXTRACTED: 59 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*