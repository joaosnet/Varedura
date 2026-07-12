import hashlib
import json

from cli import ui_shared
from monitor.ping_targets import TargetSelection


def _set_prefs(monkeypatch, tmp_path, payload):
    path = tmp_path / "prefs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(ui_shared, "PREFS_FILE", path)
    return path


def test_clean_install_requires_target_onboarding(monkeypatch, tmp_path):
    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "missing.json")
    config = ui_shared.load_network_config()
    assert config["network_schema_version"] == 3
    assert config["selected_target_ids"] == []
    assert not config["target_onboarding_completed"]


def test_stored_app_ca_must_match_immutable_fingerprint(monkeypatch, tmp_path):
    monkeypatch.setattr(ui_shared.Path, "home", classmethod(lambda cls: tmp_path))
    material = b"immutable app CA test material"
    digest = hashlib.sha256(material).hexdigest()
    store = tmp_path / ".varedura" / "certs"
    store.mkdir(parents=True)
    candidate = store / f"{digest}.pem"
    candidate.write_bytes(material)

    assert ui_shared._verified_stored_app_ca(str(candidate)) == str(candidate)
    candidate.write_bytes(b"changed after consent")
    assert ui_shared._verified_stored_app_ca(str(candidate)) == ""


def test_legacy_automatic_default_does_not_start_external_ping(monkeypatch, tmp_path):
    _set_prefs(
        monkeypatch,
        tmp_path,
        {"network": {"external_host": "ec2.sa-east-1.amazonaws.com"}},
    )
    config = ui_shared.load_network_config()
    assert config["selected_target_ids"] == []
    assert not config["target_onboarding_completed"]


def test_legacy_explicit_host_becomes_primary_custom_target(monkeypatch, tmp_path):
    _set_prefs(
        monkeypatch,
        tmp_path,
        {"network": {"external_host": "intranet.example.org"}},
    )
    config = ui_shared.load_network_config()
    selection = TargetSelection.from_config(config)
    assert selection.onboarding_completed
    assert selection.primary_target.host == "intranet.example.org"
    assert selection.selected_target_ids == (selection.primary_target_id,)


def test_corrupt_schema_and_invalid_legacy_host_return_to_onboarding(
    monkeypatch, tmp_path
):
    _set_prefs(
        monkeypatch,
        tmp_path,
        {
            "network": {
                "network_schema_version": "not-a-number",
                "external_host": "https://bad.example/path",
            }
        },
    )
    config = ui_shared.load_network_config()
    selection = TargetSelection.from_config(config)
    assert not config["target_onboarding_completed"]
    assert not selection.targets
    assert not selection.onboarding_completed


def test_v3_unknown_ids_do_not_count_as_completed_selection():
    selection = TargetSelection.from_config(
        {
            "network_schema_version": 3,
            "target_onboarding_completed": True,
            "selected_target_ids": ["does_not_exist"],
            "primary_target_id": "does_not_exist",
        }
    )
    assert not selection.targets
    assert not selection.onboarding_completed


def test_corrupt_numeric_preferences_fall_back_before_first_compose(
    monkeypatch, tmp_path
):
    _set_prefs(
        monkeypatch,
        tmp_path,
        {
            "network": {
                "network_schema_version": 3,
                "target_onboarding_completed": True,
                "selected_target_ids": ["cloudflare_ipv4"],
                "primary_target_id": "cloudflare_ipv4",
                "lag_threshold_ms": "broken",
                "contracted_down": {},
                "contracted_up": -1,
            }
        },
    )
    config = ui_shared.load_network_config()
    assert config["lag_threshold_ms"] == 100
    assert config["contracted_down"] == 500.0
    assert config["contracted_up"] == 100.0


def test_v3_save_removes_legacy_scalar_and_preserves_privacy_flags(
    monkeypatch, tmp_path
):
    path = _set_prefs(
        monkeypatch,
        tmp_path,
        {"network": {"external_host": "old.example"}},
    )
    ui_shared.save_network_config(
        {
            "network_schema_version": 3,
            "target_onboarding_completed": True,
            "selected_target_ids": ["lol_br1_api", "cloudflare_ipv4"],
            "primary_target_id": "lol_br1_api",
            "custom_targets": [],
            "league_auto_detect": True,
            "include_full_ip_exports": False,
            "app_ca_file": "corp.pem",
        }
    )
    stored = json.loads(path.read_text(encoding="utf-8"))["network"]
    assert "external_host" not in stored
    assert stored["selected_target_ids"] == ["lol_br1_api", "cloudflare_ipv4"]
    assert stored["include_full_ip_exports"] is False
    assert stored["app_ca_file"] == "corp.pem"
