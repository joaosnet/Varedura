"""Perfis de plano: seleção pela rede, conformidade, ciclo e detecção de rede."""

from __future__ import annotations

import datetime
import json

from cli import ui_shared
from monitor import netinfo
from monitor.netinfo import detect_active_network as real_detect_active_network
from monitor.plan_profiles import (
    ActiveNetwork,
    NetworkKind,
    PlanKind,
    PlanProfile,
    SpeedSample,
    bind_to_network,
    current_cycle,
    evaluate_speed,
    profiles_from_prefs,
    quota_status,
    select_profile,
)

HOME = PlanProfile(
    id="home", name="Fibra casa", down_mbps=600, up_mbps=300, match_ssid="CasaWifi"
)
WORK = PlanProfile(
    id="work", name="Escritório", down_mbps=100, up_mbps=50, match_gateway="10.0.0.1"
)
PREPAID = PlanProfile(
    id="sim",
    name="Pré-pago",
    kind=PlanKind.MOBILE,
    quota_gb=10,
    cycle_start="2026-11-01",
    cycle_days=30,
    match_kind="mobile",
)
ALL = [HOME, WORK, PREPAID]


def _sample(down: float, up: float) -> SpeedSample:
    return SpeedSample(datetime.datetime(2026, 11, 20, 12, 0), down, up)


def test_select_profile_priority_manual_ssid_gateway_kind():
    wifi_home = ActiveNetwork(NetworkKind.WIFI, "casawifi", "192.168.18.1", "wlan0")
    assert select_profile(ALL, wifi_home) == (HOME, "ssid")
    assert select_profile(ALL, wifi_home, manual_id="work") == (WORK, "manual")

    no_ssid = ActiveNetwork(NetworkKind.WIFI, "", "10.0.0.1", "wlan0")
    assert select_profile(ALL, no_ssid) == (WORK, "gateway")

    mobile = ActiveNetwork(NetworkKind.MOBILE, "", "", "rmnet0")
    assert select_profile(ALL, mobile) == (PREPAID, "kind")


def test_mobile_network_never_falls_back_to_fixed_plan():
    mobile = ActiveNetwork(NetworkKind.MOBILE, interface="rmnet0")
    assert select_profile([HOME], mobile) == (None, "")
    # Rede desconhecida com um único plano: usa o único.
    assert select_profile([HOME], None) == (HOME, "only")
    # Um plano móvel sozinho nunca é aplicado em Wi-Fi.
    assert select_profile([PREPAID], ActiveNetwork(NetworkKind.WIFI, "Casa")) == (
        None,
        "",
    )
    # Plano fixo único, mas associado a outro Wi-Fi conhecido: não aplica.
    other = ActiveNetwork(NetworkKind.WIFI, "Vizinho", "192.168.0.1")
    assert select_profile([HOME, PREPAID], other) == (None, "")
    # Wi-Fi sem associação e vários planos: não adivinha.
    unknown_wifi = ActiveNetwork(NetworkKind.WIFI, "Outra", "172.16.0.1")
    assert select_profile(ALL, unknown_wifi) == (None, "")


def test_bind_to_network_prefers_ssid_then_gateway():
    blank = PlanProfile(id="x", name="X")
    with_ssid = bind_to_network(blank, ActiveNetwork(NetworkKind.WIFI, "Casa", "1.1.1.1"))
    assert (with_ssid.match_ssid, with_ssid.match_gateway) == ("Casa", "")
    without = bind_to_network(blank, ActiveNetwork(NetworkKind.WIFI, "", "192.168.18.1"))
    assert (without.match_ssid, without.match_gateway) == ("", "192.168.18.1")
    mobile = bind_to_network(blank, ActiveNetwork(NetworkKind.MOBILE))
    assert (mobile.match_kind, mobile.match_gateway) == ("mobile", "")


def test_evaluate_speed_reference_thresholds():
    ok = evaluate_speed(HOME, [_sample(590, 290), _sample(520, 260)])
    assert ok.status == "ok" and ok.pct_down > 80 and ok.instant_violations == 0

    below_avg = evaluate_speed(HOME, [_sample(300, 290), _sample(400, 280)])
    assert below_avg.status == "below" and below_avg.average_ok is False

    # Média boa, mas uma medição abaixo de 40% do plano.
    spike = evaluate_speed(HOME, [_sample(600, 300)] * 9 + [_sample(100, 300)])
    assert spike.average_ok is True and spike.instant_violations == 1
    assert spike.status == "below"

    assert evaluate_speed(HOME, []).status == "no_data"
    no_ref = evaluate_speed(PREPAID, [_sample(30, 10)])
    assert no_ref.status == "no_reference" and no_ref.avg_down == 30


def test_cycle_rolls_forward_and_quota_projection():
    today = datetime.date(2026, 12, 11)  # 40 dias após o início: 2º ciclo
    cycle = current_cycle(PREPAID, today)
    assert cycle.start == datetime.date(2026, 12, 1)
    assert cycle.end == datetime.date(2026, 12, 31)

    status = quota_status(PREPAID, 5 * 1024**3, today)
    assert round(status.used_gb, 2) == 5.0 and status.days_left == 20
    assert round(status.projected_gb, 1) == 15.0 and status.will_exceed
    assert not status.exceeded

    offset = PlanProfile.from_dict({**PREPAID.to_dict(), "used_offset_gb": 6})
    assert quota_status(offset, 5 * 1024**3, today).exceeded


def test_profiles_from_prefs_drops_invalid_entries():
    raw = [
        HOME.to_dict(),
        HOME.to_dict(),  # id duplicado
        {"name": ""},  # sem nome
        "lixo",
        {"name": "Neg", "down_mbps": -5, "kind": "???", "cycle_days": 9999},
    ]
    profiles = profiles_from_prefs(raw)
    assert [p.name for p in profiles] == ["Fibra casa", "Neg"]
    assert profiles[1].down_mbps == 0 and profiles[1].kind is PlanKind.FIXED
    assert profiles[1].cycle_days == 30


def test_v3_prefs_migrate_contracted_speed_into_a_profile(monkeypatch, tmp_path):
    path = tmp_path / "prefs.json"
    path.write_text(
        json.dumps(
            {
                "network": {
                    "network_schema_version": 3,
                    "target_onboarding_completed": True,
                    "selected_target_ids": ["cloudflare_ipv4"],
                    "primary_target_id": "cloudflare_ipv4",
                    "contracted_down": 300.0,
                    "contracted_up": 150.0,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ui_shared, "PREFS_FILE", path)
    config = ui_shared.load_network_config()
    # A migração v4 não pode reabrir o onboarding nem apagar os alvos.
    assert config["selected_target_ids"] == ["cloudflare_ipv4"]
    assert config["target_onboarding_completed"] is True
    (profile,) = profiles_from_prefs(config["plan_profiles"])
    assert (profile.down_mbps, profile.up_mbps) == (300.0, 150.0)

    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "missing.json")
    assert ui_shared.load_network_config()["plan_profiles"] == []


def test_parse_route_and_netsh_outputs():
    assert netinfo.parse_route_get(
        "1.1.1.1 via 192.168.18.1 dev wlan0 table 1046 src 192.168.18.242 uid 10341"
    ) == ("wlan0", "192.168.18.1")
    assert netinfo.parse_route_get("1.1.1.1 dev rmnet0 src 10.11.12.13") == (
        "rmnet0",
        "",
    )
    netsh_pt = (
        "    Nome                   : Wi-Fi\n"
        "    Estado                 : conectado\n"
        "    SSID                   : Casa 5G\n"
        "    BSSID                  : aa:bb:cc:dd:ee:ff\n"
    )
    assert netinfo.parse_netsh_wlan(netsh_pt) == "Casa 5G"
    assert netinfo.parse_netsh_wlan(netsh_pt.replace("conectado", "desconectado")) == ""


def test_detect_active_network_on_android_mobile_and_hidden_ssid(monkeypatch):
    monkeypatch.setattr(netinfo.platform, "system", lambda: "Android")
    outputs = {
        "ip": "1.1.1.1 via 192.168.18.1 dev wlan0 src 192.168.18.242",
        "termux-wifi-connectioninfo": json.dumps({"ssid": "<unknown ssid>"}),
    }
    monkeypatch.setattr(netinfo, "_run", lambda cmd: outputs.get(cmd[0], ""))
    wifi = real_detect_active_network()
    assert (wifi.kind, wifi.ssid, wifi.gateway) == (
        NetworkKind.WIFI,
        "",
        "192.168.18.1",
    )

    outputs["ip"] = "1.1.1.1 via 10.64.64.64 dev rmnet0 src 10.11.12.13"
    mobile = real_detect_active_network()
    assert (mobile.kind, mobile.gateway) == (NetworkKind.MOBILE, "")
