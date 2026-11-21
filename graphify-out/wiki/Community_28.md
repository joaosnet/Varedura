# Community 28

> 32 nodes · cohesion 0.12

## Key Concepts

- **TargetSelection** (32 connections) — `monitor/ping_targets.py`
- **load_network_config()** (21 connections) — `cli/ui_shared.py`
- **.from_config()** (19 connections) — `monitor/ping_targets.py`
- **test_network_config_v3.py** (15 connections) — `tests/test_network_config_v3.py`
- **_ensure_legacy_network_targets()** (11 connections) — `cli/legacy_app.py`
- **target_catalog()** (9 connections) — `monitor/ping_targets.py`
- **prompt_change_external()** (8 connections) — `monitor/stalker.py`
- **.to_config()** (6 connections) — `monitor/ping_targets.py`
- **_set_prefs()** (6 connections) — `tests/test_network_config_v3.py`
- **test_selection_round_trip_and_legacy_migration()** (6 connections) — `tests/test_ping_targets.py`
- **_verified_stored_app_ca()** (5 connections) — `cli/ui_shared.py`
- **test_corrupt_schema_and_invalid_legacy_host_return_to_onboarding()** (5 connections) — `tests/test_network_config_v3.py`
- **test_legacy_explicit_host_becomes_primary_custom_target()** (5 connections) — `tests/test_network_config_v3.py`
- **._from_legacy_config()** (4 connections) — `monitor/ping_targets.py`
- **.__init__()** (3 connections) — `cli/network_ui.py`
- **Any** (3 connections)
- **.selected_target_ids()** (3 connections) — `monitor/ping_targets.py`
- **test_corrupt_numeric_preferences_fall_back_before_first_compose()** (3 connections) — `tests/test_network_config_v3.py`
- **test_legacy_automatic_default_does_not_start_external_ping()** (3 connections) — `tests/test_network_config_v3.py`
- **test_v3_save_removes_legacy_scalar_and_preserves_privacy_flags()** (3 connections) — `tests/test_network_config_v3.py`
- **test_v3_unknown_ids_do_not_count_as_completed_selection()** (3 connections) — `tests/test_network_config_v3.py`
- **test_catalog_has_stable_ids_and_unique_entries()** (3 connections) — `tests/test_ping_targets.py`
- **.primary_target()** (2 connections) — `monitor/ping_targets.py`
- **test_clean_install_requires_target_onboarding()** (2 connections) — `tests/test_network_config_v3.py`
- **test_stored_app_ca_must_match_immutable_fingerprint()** (2 connections) — `tests/test_network_config_v3.py`
- *... and 7 more nodes in this community*

## Relationships

- [Community 11](Community_11.md) (11 shared connections)
- [Community 8](Community_8.md) (9 shared connections)
- [Community 0](Community_0.md) (7 shared connections)
- [Community 1](Community_1.md) (7 shared connections)
- [Community 6](Community_6.md) (6 shared connections)
- [Community 14](Community_14.md) (5 shared connections)
- [Community 36](Community_36.md) (5 shared connections)
- [Community 74](Community_74.md) (4 shared connections)
- [Community 30](Community_30.md) (4 shared connections)
- [Community 94](Community_94.md) (3 shared connections)
- [Community 59](Community_59.md) (3 shared connections)
- [Community 9](Community_9.md) (2 shared connections)

## Source Files

- `cli/legacy_app.py`
- `cli/network_ui.py`
- `cli/ui_shared.py`
- `monitor/ping_targets.py`
- `monitor/stalker.py`
- `tests/test_network_config_v3.py`
- `tests/test_ping_targets.py`

## Audit Trail

- EXTRACTED: 118 (91%)
- INFERRED: 12 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*