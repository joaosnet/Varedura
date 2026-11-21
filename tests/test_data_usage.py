"""Franquia por ciclo, histórico de velocidade e laudo PDF por tipo de plano."""

from __future__ import annotations

import datetime
import glob
import os

import pytest

from monitor import data_usage
from monitor.data_usage import (
    DataUsageTracker,
    load_speed_samples,
    record_speed_sample,
    samples_for_report,
)
from monitor.plan_profiles import PlanKind, PlanProfile, SpeedSample

GB = 1024**3
PREPAID = PlanProfile(
    id="sim",
    name="Pré-pago",
    kind=PlanKind.MOBILE,
    operadora="Operadora Teste",
    plano="Pré 10GB",
    quota_gb=10,
    cycle_start="2026-11-01",
    cycle_days=30,
)


def test_usage_counts_deltas_survives_reboot_and_rolls_cycle(tmp_path):
    path = tmp_path / "usage.json"
    day = datetime.date(2026, 11, 10)
    tracker = DataUsageTracker(path)
    assert tracker.update(PREPAID, 5 * GB, day) == 0  # 1ª leitura só define a base
    assert tracker.update(PREPAID, 6 * GB, day) == 1 * GB
    # Reboot: contador volta a um valor menor; tudo desde o boot é consumo novo.
    assert tracker.update(PREPAID, GB // 2, day, force_save=True) == GB + GB // 2

    reloaded = DataUsageTracker(path)
    assert reloaded.cycle_bytes(PREPAID, day) == GB + GB // 2
    assert reloaded.update(PREPAID, GB, day) == 2 * GB

    # Ciclo seguinte zera o acumulado sem recontar o tráfego anterior.
    next_cycle = datetime.date(2026, 12, 2)
    assert reloaded.update(PREPAID, GB, next_cycle) == 0
    assert reloaded.update(PREPAID, GB + 100, next_cycle) == 100


def test_speed_history_roundtrip_filters_by_profile_and_cycle(tmp_path):
    path = tmp_path / "speed.jsonl"
    inside = datetime.datetime(2026, 11, 15, 10, 0, 0)
    record_speed_sample(SpeedSample(inside, 30, 8, 40, "Fast.com", "srv", "sim", "mobile"), path)
    record_speed_sample(
        SpeedSample(datetime.datetime(2026, 10, 20, 9, 0), 25, 5, profile_id="sim"), path
    )
    record_speed_sample(SpeedSample(inside, 500, 250, profile_id="home"), path)
    path.write_text(path.read_text(encoding="utf-8") + "linha corrompida\n", encoding="utf-8")

    assert len(load_speed_samples(path=path)) == 3
    session = [SpeedSample(inside, 30, 8, profile_id="sim")]  # duplicata do persistido
    report = samples_for_report(
        PREPAID, session, now=datetime.datetime(2026, 11, 20, 12, 0), path=path
    )
    assert [(s.down_mbps, s.provider) for s in report] == [(30.0, "Fast.com")]


def _pdf_text(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


@pytest.mark.parametrize("kind", ["fixed", "mobile"])
def test_report_uses_active_profile_and_consumer_wording(kind, monkeypatch, tmp_path):
    pytest.importorskip("matplotlib")
    import monitor.stalker as stalker
    from monitor.speed_tester import get_speed_tester

    monkeypatch.chdir(tmp_path)
    profile = (
        PREPAID
        if kind == "mobile"
        else PlanProfile(
            id="home",
            name="Fibra",
            operadora="Provedor Teste",
            plano="Fibra 600",
            down_mbps=600,
            up_mbps=300,
        )
    )
    now = datetime.datetime.now()
    record_speed_sample(SpeedSample(now, 120, 280, 12, "Speedtest.net", "srv", profile.id))
    data_usage.get_usage_tracker().update(profile, 1 * GB)
    data_usage.get_usage_tracker().update(profile, 4 * GB)

    monkeypatch.setattr(stalker, "full_ping_history", [(now, 5.0, 30.0)] * 5)
    stats = get_speed_tester().stats
    for name in ("timestamps", "history_down", "history_up", "history_providers"):
        getattr(stats, name).clear()
    monkeypatch.setattr(stats, "test_count", 0)
    stalker.set_contract(profile)
    stalker.set_report_context(
        target_rows=[("Cloudflare (1.1.1.1)", "5", "20.0", "30.0", "41.0", "0.0%")]
    )
    try:
        stalker._generate_combined_pdf_worker()
    finally:
        stalker.set_contract(None)
        stalker.set_report_context()

    (pdf,) = glob.glob(os.path.join("exports", "relatorio_formal_*.pdf"))
    text = _pdf_text(pdf)
    compact = text.replace(" ", "")
    assert "WLANSISTEMAS" not in compact
    assert "AGÊNCIANACIONAL" not in compact
    assert "LAUDOELABORADOPELOCONSUMIDOR" in compact
    assert profile.operadora.replace(" ", "") in compact
    assert "Cloudflare" in text
    if kind == "mobile":
        assert "FRANQUIADEDADOS" in compact
        assert "SEMREFERÊNCIA" in compact  # pré-pago sem velocidade anunciada
    else:
        # 120 Mbps de 600 contratados: abaixo da referência de 80%.
        assert "ABAIXODAREFERÊNCIA" in compact
        assert "FRANQUIADEDADOS" not in compact
