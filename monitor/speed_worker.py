"""Isolated child-process entry point for one bandwidth provider.

The parent passes an enumerated provider id.  This module is deliberately not
imported by the TUI: requests, Selenium and browser processes exist only in the
short-lived worker tree created after an explicit user action.
"""

from __future__ import annotations

import argparse
import json
from typing import Any


PROVIDER_IDS = ("speedtest", "fast", "brasil_banda_larga", "simet")


def run_provider(provider_id: str) -> dict[str, Any]:
    from monitor.speed_providers import (
        BrasilBandaLargaProvider,
        FastComProvider,
        SimetProvider,
        SpeedtestNetProvider,
    )

    factories = {
        "speedtest": SpeedtestNetProvider,
        "fast": FastComProvider,
        "brasil_banda_larga": BrasilBandaLargaProvider,
        "simet": SimetProvider,
    }
    factory = factories.get(provider_id)
    if factory is None:
        return {"ok": False, "error": "unknown-provider"}
    provider = factory()
    try:
        if not provider.is_available():
            return {"ok": False, "error": "provider-unavailable"}
        result = provider.run_test()
        if result is None:
            return {"ok": False, "error": "provider-failed"}
        return {
            "ok": True,
            "result": {
                "download_mbps": result.download_mbps,
                "upload_mbps": result.upload_mbps,
                "ping_ms": result.ping_ms,
                "servidor": result.servidor,
                "timestamp": result.timestamp.isoformat(),
                "provider_name": result.provider_name,
            },
        }
    finally:
        provider.cleanup()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--provider", required=True, choices=PROVIDER_IDS)
    args = parser.parse_args(argv)
    try:
        payload = run_provider(args.provider)
    except BaseException as exc:
        payload = {"ok": False, "error": type(exc).__name__}
    print(json.dumps(payload, ensure_ascii=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
