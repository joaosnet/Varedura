"""Thread-safe, target-aware ping history and privacy-preserving exports."""

from __future__ import annotations

import csv
import ipaddress
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Iterable

from monitor.ping_targets import PingProbeResult, PingTarget, TargetCategory


def mask_ip(value: str) -> str:
    """Mask an endpoint as IPv4 /24 or IPv6 /64 while retaining correlation."""
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return value
    prefix = 24 if address.version == 4 else 64
    return str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))


@dataclass(frozen=True, slots=True)
class NetworkHistoryRecord:
    timestamp_utc: datetime
    target_id: str
    generation: int
    label: str
    target_kind: str
    configured_host: str
    resolved_ip: str
    remote_port: int | None
    probe_method: str
    status: str
    latency_ms: float | None
    session_id: str | None = None


class NetworkSessionHistory:
    """Own all ping samples for one application session without mixing targets."""

    def __init__(self, *, max_records: int = 50_000) -> None:
        self._max_records = max(100, int(max_records))
        self._records: list[NetworkHistoryRecord] = []
        self._lock = threading.RLock()

    def add_result(
        self,
        result: PingProbeResult,
        target: PingTarget,
        *,
        remote_port: int | None = None,
        session_id: str | None = None,
    ) -> NetworkHistoryRecord:
        resolved = ""
        try:
            resolved = str(ipaddress.ip_address(result.host))
        except ValueError:
            pass
        record = NetworkHistoryRecord(
            timestamp_utc=result.observed_at.astimezone(timezone.utc),
            target_id=result.target_id,
            generation=result.generation,
            label=target.label,
            target_kind=target.category.value,
            configured_host=target.host,
            resolved_ip=resolved,
            remote_port=remote_port,
            probe_method=result.method,
            status=result.status.value,
            latency_ms=result.latency_ms,
            session_id=session_id,
        )
        with self._lock:
            self._records.append(record)
            overflow = len(self._records) - self._max_records
            if overflow > 0:
                del self._records[:overflow]
        return record

    def snapshot(self) -> tuple[NetworkHistoryRecord, ...]:
        with self._lock:
            return tuple(self._records)

    def grouped(self) -> dict[tuple[str, int, str | None], list[NetworkHistoryRecord]]:
        groups: dict[tuple[str, int, str | None], list[NetworkHistoryRecord]] = (
            defaultdict(list)
        )
        for record in self.snapshot():
            groups[(record.target_id, record.generation, record.session_id)].append(
                record
            )
        return dict(groups)

    @staticmethod
    def _private_host(
        record: NetworkHistoryRecord, include_full_ips: bool
    ) -> tuple[str, str]:
        if include_full_ips or record.target_kind != TargetCategory.LEAGUE_MATCH.value:
            return record.configured_host, record.resolved_ip
        return mask_ip(record.configured_host), mask_ip(record.resolved_ip)

    def export_csv(self, path: Path, *, include_full_ips: bool = False) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                (
                    "timestamp_utc",
                    "target_id",
                    "generation",
                    "label",
                    "target_kind",
                    "configured_host",
                    "resolved_ip",
                    "remote_port",
                    "probe_method",
                    "status",
                    "latency_ms",
                    "session_id",
                )
            )
            groups = self.grouped()
            for group_key in sorted(
                groups,
                key=lambda key: (key[0], key[1], key[2] or ""),
            ):
                for record in groups[group_key]:
                    host, resolved = self._private_host(record, include_full_ips)
                    writer.writerow(
                        (
                            record.timestamp_utc.isoformat(),
                            record.target_id,
                            record.generation,
                            record.label,
                            record.target_kind,
                            host,
                            resolved,
                            record.remote_port or "",
                            record.probe_method,
                            record.status,
                            ""
                            if record.latency_ms is None
                            else f"{record.latency_ms:.3f}",
                            record.session_id or "",
                        )
                    )
        return path

    def export_pdf(self, path: Path, *, include_full_ips: bool = False) -> Path:
        """Generate a compact report with one statistics block per target generation."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib import colors

        path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()
        story: list = [
            Paragraph("Varedura — Relatório de Rede", styles["Title"]),
            Spacer(1, 5 * mm),
        ]
        for (_target_id, generation, session_id), records in self.grouped().items():
            first = records[0]
            host, _ = self._private_host(first, include_full_ips)
            successful = [
                record.latency_ms for record in records if record.latency_ms is not None
            ]
            loss = 100.0 * (len(records) - len(successful)) / len(records)
            heading = f"{first.label} — geração {generation}"
            if session_id:
                heading += f" — sessão {session_id[:8]}"
            story.extend(
                [
                    Paragraph(heading, styles["Heading2"]),
                    Paragraph(f"Destino: {host}", styles["BodyText"]),
                    Table(
                        [
                            ["Amostras", "Mínimo", "Média", "Máximo", "Sem resposta"],
                            [
                                str(len(records)),
                                f"{min(successful):.1f} ms" if successful else "—",
                                f"{fmean(successful):.1f} ms" if successful else "—",
                                f"{max(successful):.1f} ms" if successful else "—",
                                f"{loss:.1f}%",
                            ],
                        ],
                        style=TableStyle(
                            [
                                (
                                    "BACKGROUND",
                                    (0, 0),
                                    (-1, 0),
                                    colors.HexColor("#164e63"),
                                ),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                                ("PADDING", (0, 0), (-1, -1), 5),
                            ]
                        ),
                    ),
                    Spacer(1, 4 * mm),
                ]
            )
        document = SimpleDocTemplate(str(path), pagesize=A4)
        document.build(story)
        return path

    def export_bundle(
        self,
        directory: Path = Path("exports"),
        *,
        include_full_ips: bool = False,
    ) -> tuple[Path, Path]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = directory / f"ping_targets_{stamp}.csv"
        pdf_path = directory / f"network_report_{stamp}.pdf"
        self.export_csv(csv_path, include_full_ips=include_full_ips)
        self.export_pdf(pdf_path, include_full_ips=include_full_ips)
        return csv_path, pdf_path


def summarize_latencies(
    records: Iterable[NetworkHistoryRecord],
) -> tuple[float | None, float | None, float | None]:
    values = [record.latency_ms for record in records if record.latency_ms is not None]
    if not values:
        return None, None, None
    return min(values), fmean(values), max(values)


__all__ = [
    "NetworkHistoryRecord",
    "NetworkSessionHistory",
    "mask_ip",
    "summarize_latencies",
]
