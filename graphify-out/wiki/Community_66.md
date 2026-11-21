# Community 66

> 17 nodes · cohesion 0.20

## Key Concepts

- **test_port_scanner.py** (13 connections) — `tests/test_port_scanner.py`
- **get_listening_ports()** (7 connections) — `monitor/port_scanner.py`
- **_patch_processes()** (7 connections) — `tests/test_port_scanner.py`
- **get_process_connections_count()** (6 connections) — `monitor/port_scanner.py`
- **_conn()** (6 connections) — `tests/test_port_scanner.py`
- **search_port()** (4 connections) — `monitor/port_scanner.py`
- **test_get_listening_ports_access_denied_label()** (4 connections) — `tests/test_port_scanner.py`
- **test_get_listening_ports_filters_dedups_and_sorts()** (4 connections) — `tests/test_port_scanner.py`
- **test_get_process_connections_count_orders_and_limits()** (4 connections) — `tests/test_port_scanner.py`
- **test_run_full_scan_aggregates_state()** (4 connections) — `tests/test_port_scanner.py`
- **test_search_port_returns_matching_processes()** (4 connections) — `tests/test_port_scanner.py`
- **types** (4 connections)
- **Retorna os processos com mais conexões de rede. Args: limit: Número máximo de…** (1 connections) — `monitor/port_scanner.py`
- **Busca processos usando uma porta específica. Args: porta_numero: Número da…** (1 connections) — `monitor/port_scanner.py`
- **Retorna lista de portas TCP e UDP em listening. Returns: Tuple com (tcp_ports,…** (1 connections) — `monitor/port_scanner.py`
- **fake_process()** (1 connections) — `tests/test_port_scanner.py`
- **Tests for monitor.port_scanner (psutil fully mocked — no real sockets touched).** (1 connections) — `tests/test_port_scanner.py`

## Relationships

- [Community 3](Community_3.md) (6 shared connections)
- [Community 41](Community_41.md) (4 shared connections)
- [Community 6](Community_6.md) (3 shared connections)
- [Community 72](Community_72.md) (1 shared connections)
- [Community 97](Community_97.md) (1 shared connections)
- [Community 18](Community_18.md) (1 shared connections)
- [Community 21](Community_21.md) (1 shared connections)
- [Community 2](Community_2.md) (1 shared connections)

## Source Files

- `monitor/port_scanner.py`
- `tests/test_port_scanner.py`

## Audit Trail

- EXTRACTED: 44 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*