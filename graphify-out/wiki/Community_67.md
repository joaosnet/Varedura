# Community 67

> 17 nodes · cohesion 0.18

## Key Concepts

- **NetIPPacket** (20 connections) — `rtsp/xiongmai.py`
- **MockNetIPServer** (10 connections) — `tests/test_xiongmai_p2p.py`
- **.to_bytes()** (8 connections) — `rtsp/xiongmai.py`
- **.from_bytes()** (7 connections) — `rtsp/xiongmai.py`
- **.discover()** (7 connections) — `rtsp/xiongmai.py`
- **test_netip_packet_serialization()** (5 connections) — `tests/test_xiongmai_p2p.py`
- **._run()** (4 connections) — `tests/test_xiongmai_p2p.py`
- **test_netip_packet_incomplete_buffer()** (4 connections) — `tests/test_xiongmai_p2p.py`
- **.get_json()** (3 connections) — `rtsp/xiongmai.py`
- **Any** (2 connections)
- **Parse packet from byte buffer. Returns (packet, bytes_consumed).** (1 connections) — `rtsp/xiongmai.py`
- **Decode payload as JSON if possible.** (1 connections) — `rtsp/xiongmai.py`
- **Broadcast NetIP discovery packet over UDP port 34567 and return found cameras.** (1 connections) — `rtsp/xiongmai.py`
- **Represents a decoded NetIP binary packet.** (1 connections) — `rtsp/xiongmai.py`
- **Serialize packet into NetIP wire format.** (1 connections) — `rtsp/xiongmai.py`
- **.__init__()** (1 connections) — `tests/test_xiongmai_p2p.py`
- **In-memory mock Xiongmai NetIP server for integration testing.** (1 connections) — `tests/test_xiongmai_p2p.py`

## Relationships

- [Community 47](Community_47.md) (13 shared connections)
- [Community 59](Community_59.md) (8 shared connections)
- [Community 77](Community_77.md) (2 shared connections)
- [Community 79](Community_79.md) (2 shared connections)
- [Community 58](Community_58.md) (2 shared connections)

## Source Files

- `rtsp/xiongmai.py`
- `tests/test_xiongmai_p2p.py`

## Audit Trail

- EXTRACTED: 43 (83%)
- INFERRED: 9 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*