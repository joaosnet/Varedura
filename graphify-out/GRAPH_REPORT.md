# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 107 files · ~136,533 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2838 nodes · 7323 edges · 203 communities (84 shown, 119 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 545 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `83fd8f66`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_auto_speed.py
- VareduraTextualApp
- test_league_detector.py
- test_textual_app.py
- time
- CameraBridge
- stalker.py
- t
- PingScheduler
- compute_health_score
- ping_targets.py
- network_repairs.py
- test_rtsp_modules.py
- re
- main
- textual_app.py
- CamerasMixin
- test_network_diagnostics.py
- Event
- ContinuousSpeedTester
- test_camera_bridge.py
- test_network_repairs.py
- native_text_dialog
- credenciais.py
- work
- CommandResult
- PlansMixin
- set_keyboard_key
- server.py
- TargetSelection
- data_usage.py
- PingTarget
- FFmpegRunner
- speed_providers.py
- NetworkSnapshot
- NetIPPacket
- test_speed_cleanup.py
- test_docker_cleanup.py
- test_port_catalog.py
- abrir_stream
- save_network_config
- WSLDockerCleaner
- os
- install.ps1
- install.sh
- UnifiedCameraSource
- test_android_adaptations.py
- termux_env.py
- camera_bridge.py
- regioes.py
- handle_key
- port_scanner.py
- ._compose_settings
- FastComProvider
- mapa.py
- TermuxMixin
- LocationStore
- TargetPickerScreen
- socket
- test_textual_cameras.py
- redact_sensitive
- MLabNdt7Provider
- MotionHeatmap
- DailyLogWriter
- test_textual_cleanup_worker_uses_fake_cleaner
- test_textual_docker_reward_and_achievement
- SpeedtestNetProvider
- core.py
- TermuxKeysMixin
- camera_engine.py
- SubprocessRepairRunner
- ui_shared.py
- quick_cleanup
- test_layout.py
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- is_android
- test_textual_termux.py
- LeagueMatchDetector
- subprocess
- monitor/__init__.py
- json
- log.py
- ._importar_credenciais
- test_shutdown_close_resources_terminates_players
- ._accept_ping_result
- LeagueEndpoint
- SimetProvider
- check_keyboard
- export_combined_report
- _CompletedPopen
- textual_cameras.py
- os
- varedura
- termux_install.sh
- run_textual_app
- CaptureResult
- time
- ShutdownScreen
- speed_providers_http.py
- .on_button_pressed
- textual_plans.py
- _HangingPopen
- league_detector.py
- get_docker_vhdx_paths
- .start

## God Nodes (most connected - your core abstractions)
1. `t()` - 211 edges
2. `VareduraTextualApp` - 181 edges
3. `WSLDockerCleaner` - 71 edges
4. `CamerasMixin` - 69 edges
5. `CameraBridge` - 52 edges
6. `PingTarget` - 47 edges
7. `PlansMixin` - 40 edges
8. `PlanProfile` - 38 edges
9. `_load_camera_backend()` - 38 edges
10. `main()` - 37 edges

## Surprising Connections (you probably didn't know these)
- `test_network_cards_reflow_for_any_terminal_size()` --uses--> `TargetPingCard`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `test_quit_shows_shutdown_screen_when_busy()` --uses--> `ShutdownScreen`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `VareduraTextualApp` --uses--> `PingStats`  [INFERRED]
  cli/textual_app.py → monitor/stalker.py
- `test_settings_saves_auto_speed_interval()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_auto_speed.py → cli/textual_app.py
- `test_compact_mode_only_on_narrow_screens()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_layout.py → cli/textual_app.py

## Import Cycles
- 2-file cycle: `cli/textual_app.py -> cli/textual_cameras.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_plans.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_termux.py -> cli/textual_app.py`

## Communities (203 total, 119 thin omitted)

### Community 0 - "test_auto_speed.py"
Cohesion: 0.11
Nodes (22): _command(), is_cron_enabled(), is_due(), last_run(), _load_state(), main(), network_block_reason(), normalize_minutes() (+14 more)

### Community 1 - "VareduraTextualApp"
Cohesion: 0.07
Nodes (6): VareduraTextualApp, format_duration(), test_additional_targets_do_not_update_primary_health_sparkline(), test_late_league_callback_cannot_reenable_disabled_detector(), test_shutdown_stop_monitors_sets_events(), test_target_card_statistics_include_jitter_trend_and_live_league_ip()

### Community 2 - "test_league_detector.py"
Cohesion: 0.26
Nodes (17): LeagueDetectorState, _detector(), _Process, _tcp(), test_active_endpoint_is_removed_when_socket_disappears_or_is_ambiguous(), test_ambiguous_public_endpoints_are_never_guessed(), test_endpoint_requires_two_stable_readings_and_becomes_ephemeral_target(), test_incomplete_socket_scan_never_accepts_partial_single_candidate() (+9 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.11
Nodes (26): PortInfo, PortScannerState, ProcessConnections, _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring(), test_hidden_tabs_are_composed_only_when_opened() (+18 more)

### Community 4 - "time"
Cohesion: 0.09
Nodes (12): test_line_crossing_rule(), test_stream_processor_pipeline(), test_zone_intrusion_rule(), Detection, EventSeverity, GeometricRule, LineCrossingRule, LoiteringRule (+4 more)

### Community 5 - "CameraBridge"
Cohesion: 0.12
Nodes (6): CameraBridge, order(), _iso_now(), _parse_iso(), _read_json(), _utc_now()

### Community 6 - "stalker.py"
Cohesion: 0.07
Nodes (13): ContractInfo, _draw_extra_pages(), _draw_text_page(), get_last_export_path(), get_ping_command(), get_top_network_hogs(), _get_top_network_hogs_fallback(), make_ascii_graph() (+5 more)

### Community 8 - "PingScheduler"
Cohesion: 0.09
Nodes (28): PingScheduler, SchedulerTargetSnapshot, TargetRole, _TargetState, PingProbeResult, PingStatus, _Clock, _gateway() (+20 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.07
Nodes (27): _Flight, build_ping_command(), create_custom_target(), _failure_status(), HostKind, _is_android_env(), parse_ping_latency(), PingSample (+19 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.09
Nodes (25): DiagnosisReport, _action_id(), _certificate_is_ca(), visit(), _der_tlvs(), _disruptive_block_reason(), _flush_preview(), _is_windows_admin() (+17 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.09
Nodes (22): _load_camera_backend(), carregar_lista(), combinar_credenciais(), _build_rtsp_request(), escanear_portas_camera(), escanear_rede(), hosts_da_faixa(), normalizar_faixa() (+14 more)

### Community 14 - "re"
Cohesion: 0.11
Nodes (21): _clean_ssid(), detect_active_network(), detect_default_gateway(), _detect_unix(), _detect_windows(), _kind_from_interface(), parse_netsh_wlan(), parse_route_get() (+13 more)

### Community 15 - "main"
Cohesion: 0.07
Nodes (16): run_full_scan(), stop_continuous_testing(), analyze_lag_source(), get_export_status(), is_android(), main(), _initial_port_scan(), make_connections_panel() (+8 more)

### Community 16 - "textual_app.py"
Cohesion: 0.07
Nodes (9): merge_visible_selection(), _detect_system_language(), get_supported_languages(), init(), _load_preference(), _load_translations(), save_preference(), set_language() (+1 more)

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.11
Nodes (25): ProxyConfiguration, SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner, _interface(), _snapshot(), test_active_link_without_default_route_is_local_only() (+17 more)

### Community 19 - "Event"
Cohesion: 0.05
Nodes (41): _bounded_daemon_call(), _collect_linux_dhcp_configuration(), _collect_proxy_configuration(), CommandRunner, _default_route_command(), DiagnosticCancelled, _http_failure_cause(), HttpObservation (+33 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.06
Nodes (11): ContinuousSpeedTester, SpeedStats, SpeedTestConfig, test_websocket_client_frame_header_and_worker_registry(), test_bandwidth_worker_cancellation_is_observed_promptly(), test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers(), test_prepared_bandwidth_test_honors_cancel_before_worker_starts() (+3 more)

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.22
Nodes (30): command(), make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic(), test_clear_location_is_idempotent_and_keeps_camera_in_catalog() (+22 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.14
Nodes (38): Confidence, Evidence, _failure_probe(), FailureCause, NetworkInterface, NetworkState, ProbeKind, ProbeStatus (+30 more)

### Community 25 - "native_text_dialog"
Cohesion: 0.29
Nodes (4): test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_native_text_dialog_parses_ok_and_cancel(), native_text_dialog()

### Community 26 - "credenciais.py"
Cohesion: 0.11
Nodes (15): monta(), monta(), carregar_conhecidos(), carregar_vault(), CredencialIP, esquecer_ip(), lembrar_ip(), Par (+7 more)

### Community 28 - "work"
Cohesion: 0.07
Nodes (3): get_system_network_stats(), _read_proc_meminfo(), _read_proc_net_totals()

### Community 29 - "CommandResult"
Cohesion: 0.22
Nodes (7): CommandResult, RepairAction, run(), run(), run(), run(), run()

### Community 30 - "PlansMixin"
Cohesion: 0.10
Nodes (4): _fmt_number(), PlansMixin, get_usage_tracker(), find_profile()

### Community 32 - "set_keyboard_key"
Cohesion: 0.16
Nodes (10): test_extra_keys_macros_and_temporary_keyboard_key(), test_publish_export_copies_to_shared_documents(), extra_key_macros(), visit(), get_termux_prefix(), publish_export(), _read_extra_keys(), set_keyboard_key() (+2 more)

### Community 33 - "server.py"
Cohesion: 0.09
Nodes (11): _confirmation_required(), docker_full_cleanup(), docker_quick_cleanup(), docker_status(), _dry_run_preview(), get_logs(), _is_docker_running(), port_scan() (+3 more)

### Community 34 - "TargetSelection"
Cohesion: 0.15
Nodes (12): TargetSelection, _set_prefs(), test_clean_install_requires_target_onboarding(), test_corrupt_numeric_preferences_fall_back_before_first_compose(), test_corrupt_schema_and_invalid_legacy_host_return_to_onboarding(), test_legacy_automatic_default_does_not_start_external_ping(), test_legacy_explicit_host_becomes_primary_custom_target(), test_stored_app_ca_must_match_immutable_fingerprint() (+4 more)

### Community 35 - "data_usage.py"
Cohesion: 0.12
Nodes (10): _atomic_write(), DataUsageTracker, load_speed_samples(), record_speed_sample(), samples_for_report(), SpeedSample, _pdf_text(), test_report_uses_active_profile_and_consumer_wording() (+2 more)

### Community 36 - "PingTarget"
Cohesion: 0.12
Nodes (13): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingTarget, TargetCategory, _result(), test_csv_rows_are_contiguous_by_target_generation() (+5 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.11
Nodes (8): test_hls_h264_uses_remux_without_audio(), test_snapshot_failure_is_reduced_to_safe_enum(), _atomic_write_json(), FFmpegRunner, HlsProcess, _is_link_like(), _replace_with_retry(), _require_safe_child()

### Community 40 - "speed_providers.py"
Cohesion: 0.09
Nodes (4): get_multi_provider(), MultiProviderSpeedTester, ProgressState, SpeedTestProvider

### Community 41 - "NetworkSnapshot"
Cohesion: 0.15
Nodes (12): classify_diagnosis(), collect_network_snapshot(), DiagnosticOptions, _evidence_for_snapshot(), _local_probes(), NetworkDiagnosticEngine, NetworkSnapshot, ProbeResult (+4 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.09
Nodes (10): encrypt_xiongmai_digest(), encrypt_xiongmai_password(), NetIPPacket, XiongmaiNetIPClient, _delayed_stop(), MockNetIPServer, test_netip_client_workflow(), test_netip_packet_incomplete_buffer() (+2 more)

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.12
Nodes (11): BrasilBandaLargaProvider, _chrome_service(), _safe_quit(), _sane_ping(), FakeDriver, test_chrome_service_suppresses_console_window(), test_provider_cleanup_quits_and_clears_driver(), test_safe_quit_calls_quit() (+3 more)

### Community 49 - "test_docker_cleanup.py"
Cohesion: 0.10
Nodes (15): CleanupStepResult, test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers() (+7 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.12
Nodes (13): sort_key(), build_ports_summary(), classify_exposure(), describe_port(), is_exposed(), _load(), test_catalog_keys_translated(), test_classify_exposure() (+5 more)

### Community 51 - "abrir_stream"
Cohesion: 0.12
Nodes (9): abrir_stream(), _achar_exe(), comando_mpv_terminal(), detectar_player(), erro_se_morreu(), _ffprobe_disponivel(), _montar_comando(), test_video_android_player_priority_and_commands() (+1 more)

### Community 52 - "save_network_config"
Cohesion: 0.22
Nodes (5): save_network_config(), _isolated_plan_storage(), test_settings_saves_auto_speed_interval(), _prefs(), isolated_ui_prefs()

### Community 53 - "WSLDockerCleaner"
Cohesion: 0.09
Nodes (6): _ps_single_quoted(), _temp_file_path(), WSLDockerCleaner, _drain_and_wait(), stream_reader(), test_parse_wsl_distros_drops_shell_metacharacters()

### Community 54 - "os"
Cohesion: 0.19
Nodes (10): get_speed_tester(), SpeedTestResult, start_continuous_testing(), _generate_combined_pdf_worker(), cleanup_exports(), test_generate_small_pdf(), test_large_history_downsampling_and_full_flag(), cleanup_exports() (+2 more)

### Community 55 - "install.ps1"
Cohesion: 0.27
Nodes (18): Add-ToUserPath(), Get-CmdVersion(), Ask-Action(), Check-Dependencies(), Confirm-Yes(), Detect-OS(), Do-Check(), Do-Install() (+10 more)

### Community 56 - "install.sh"
Cohesion: 0.28
Nodes (20): cmd_exists(), get_version(), is_installed(), main(), refresh_path(), install.sh script, ask_action(), check_dependencies() (+12 more)

### Community 58 - "UnifiedCameraSource"
Cohesion: 0.12
Nodes (4): CameraMetadata, UnifiedCameraSource, SofiaP2PClient, test_unified_camera_source_netip()

### Community 59 - "test_android_adaptations.py"
Cohesion: 0.12
Nodes (10): build_dashboard_status(), _fmt_android_battery(), _fmt_data_mb(), _fmt_memory(), _fmt_ping(), _fmt_traffic(), _render(), test_dashboard_hides_docker_and_mcp_rows_without_docker_tab() (+2 more)

### Community 60 - "termux_env.py"
Cohesion: 0.11
Nodes (22): test_collect_android_telemetry_battery_api_fallback_and_never_raises(), test_discover_termux_tools_builtins_claro_shortcuts_and_custom(), test_discover_termux_tools_ignores_invalid_custom_json(), test_root_and_claro_suite_detection(), AndroidTelemetry, collect_android_telemetry(), _collect_battery(), _collect_ips() (+14 more)

### Community 61 - "camera_bridge.py"
Cohesion: 0.07
Nodes (20): RedactingFilter, RedactingFormatter, test_inventory_id_survives_password_change_inside_vendor_path(), test_inventory_ids_are_stable_and_private_state_has_no_endpoint(), test_inventory_never_uses_ip_as_default_name(), test_redacting_formatter_covers_exception_text(), ActiveSession, BridgeAlreadyRunning (+12 more)

### Community 62 - "regioes.py"
Cohesion: 0.13
Nodes (6): adicionar_regiao(), carregar_regioes(), Regiao, remover_regiao(), _salvar_json(), salvar_regioes()

### Community 63 - "handle_key"
Cohesion: 0.12
Nodes (13): handle_key(), load_prefs(), prompt_change_contracted_speed(), prompt_change_external(), prompt_change_gateway(), prompt_change_interval(), prompt_change_threshold(), prompt_export_report() (+5 more)

### Community 66 - "port_scanner.py"
Cohesion: 0.16
Nodes (14): get_listening_ports(), get_process_connections_count(), _safe_net_connections(), search_port(), _conn(), _patch_processes(), test_get_listening_ports_access_denied_label(), test_get_listening_ports_filters_dedups_and_sorts() (+6 more)

### Community 67 - "._compose_settings"
Cohesion: 0.12
Nodes (6): RichRenderable, build_settings_status_table(), is_mcp_configured(), load_git_autoupdate_pref(), toggle_mcp_config(), get_language()

### Community 68 - "FastComProvider"
Cohesion: 0.23
Nodes (3): FastComProvider, main(), run_provider()

### Community 69 - "mapa.py"
Cohesion: 0.15
Nodes (9): _widget(), cor_para(), _eh_terra(), _gerar_bitmap(), _interp(), Pino, projetar_celula(), _px_para_latlon() (+1 more)

### Community 71 - "TermuxMixin"
Cohesion: 0.11
Nodes (4): _format_bytes(), TermuxMixin, list_termux_services(), is_cron_update_enabled()

### Community 72 - "LocationStore"
Cohesion: 0.24
Nodes (3): CameraLocation, LocationStore, _valid_uuid()

### Community 74 - "TargetPickerScreen"
Cohesion: 0.05
Nodes (29): RepairConfirmationScreen, TargetPickerScreen, concurrency, cancel-in-progress, group, jobs, lint, test (+21 more)

### Community 75 - "socket"
Cohesion: 0.21
Nodes (6): _base24(), detectar_redes(), _eh_privado_utilizavel(), _ip_primario(), _ips_hostname(), RedeLocal

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.29
Nodes (13): isolated_state(), open_cameras(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input(), test_cameras_credential_add_and_remove(), test_cameras_import_credential_lists(), test_cameras_open_port_saved_without_credential(), test_cameras_port_scan_populates_table() (+5 more)

### Community 77 - "redact_sensitive"
Cohesion: 0.31
Nodes (3): _redact_arg(), redact_sensitive(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth()

### Community 78 - "MLabNdt7Provider"
Cohesion: 0.12
Nodes (3): MLabNdt7Provider, _WebSocket, SpeedTestResult

### Community 80 - "DailyLogWriter"
Cohesion: 0.12
Nodes (3): DailyLogWriter, cleanup_label(), run_cleanup_steps()

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.11
Nodes (6): SpeedtestNetProvider, FakeProcess, test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "core.py"
Cohesion: 0.09
Nodes (10): main(), parse_args(), run_cmd(), _powershell_encoded_command(), _strip_powershell_clixml(), buscar_prefixos_por_asn(), obter_amostra_aleatoria(), obter_blocos_rede() (+2 more)

### Community 87 - "camera_engine.py"
Cohesion: 0.08
Nodes (10): CameraCapabilities, CameraFleetManager, CameraProtocol, parse_camera_url(), DiscoveredCamera, NetIPMsgId, PTZCommand, XiongmaiDiscovery (+2 more)

### Community 88 - "SubprocessRepairRunner"
Cohesion: 0.13
Nodes (7): _kill_process(), _powershell_single_quote(), SubprocessRepairRunner, _windows_elevated_script(), test_networkmanager_checkpoint_receives_explicit_restore_answer(), test_windows_helper_script_accepts_only_enumerated_operations(), test_windows_renew_script_rejects_wildcards_and_checks_ipv6_exit()

### Community 89 - "ui_shared.py"
Cohesion: 0.06
Nodes (25): theme_name(), _add_common_status_rows(), build_cleanup_status_panel(), build_cleanup_steps_table(), build_scanner_tables(), build_tool_option(), cleanup_label_key(), cleanup_summary() (+17 more)

### Community 91 - "test_layout.py"
Cohesion: 0.18
Nodes (3): columns_for(), layout_tier(), test_layout_tiers_and_columns()

### Community 93 - "is_android"
Cohesion: 0.18
Nodes (5): test_env_detection_flags(), has_docker(), is_android(), is_termux(), should_show_docker_tab()

### Community 94 - "test_textual_termux.py"
Cohesion: 0.28
Nodes (10): isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard(), wait_until() (+2 more)

### Community 95 - "LeagueMatchDetector"
Cohesion: 0.21
Nodes (7): LeagueDetectionResult, LeagueMatchDetector, loop(), test_absolute_poll_cadence_ends_session_promptly_after_three_failures(), test_live_api_mapping_must_contain_numeric_game_time(), test_three_live_api_failures_end_and_remove_session(), live_probe()

### Community 96 - "subprocess"
Cohesion: 0.08
Nodes (21): _worker(), capturar_e_abrir_snapshot(), _ffplay_disponivel(), salvar_snapshot(), _probe_modules(), test_entrypoint_import_is_a_lightweight_dispatcher(), test_first_textual_frame_does_not_import_monitor_backends(), test_idle_speed_tester_does_not_materialize_providers() (+13 more)

### Community 97 - "monitor/__init__.py"
Cohesion: 0.24
Nodes (4): __getattr__(), StalkerConfig, test_legacy_defaults_never_restore_speculative_external_target(), test_legacy_monitor_returns_without_ping_when_onboarding_is_incomplete()

### Community 98 - "json"
Cohesion: 0.21
Nodes (7): _salvar_json(), test_graphify_artifact_excludes_private_runtime_sources(), _field_names(), _load_locale(), test_i18n_all_values_non_empty_strings(), test_i18n_placeholder_parity(), test_i18n_pt_en_key_parity()

### Community 99 - "log.py"
Cohesion: 0.19
Nodes (4): Geo, geolocalizar(), configurar(), obter_logger()

### Community 100 - "._importar_credenciais"
Cohesion: 0.27
Nodes (3): adicionar_par(), remover_par(), salvar_vault()

### Community 103 - "LeagueEndpoint"
Cohesion: 0.32
Nodes (3): LeagueEndpoint, mask_endpoint_ip(), test_privacy_mask_defaults_to_network_prefixes()

### Community 112 - "textual_cameras.py"
Cohesion: 0.12
Nodes (4): _campo(), ClickOpenDataTable, caminhos(), _dedup()

### Community 116 - "os"
Cohesion: 0.10
Nodes (21): test_cli_status_and_check_json(), test_cron_toggle_preserves_other_entries(), test_resolve_github_token_precedence_and_no_secret_in_label(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run(), test_save_token_file_rejects_empty_or_multiline(), test_update_repository_states_and_cooldown(), send_termux_notification() (+13 more)

### Community 181 - "CaptureResult"
Cohesion: 0.27
Nodes (3): FakeRunner, test_runtime_subdirectory_link_is_rejected(), CaptureResult

### Community 183 - "time"
Cohesion: 0.10
Nodes (11): test_geometric_line_intersection(), test_iou_calculation(), test_nms_suppression(), test_point_in_polygon(), compute_iou(), nms(), ObjectDetector, YOLONanoDetector (+3 more)

### Community 186 - "ShutdownScreen"
Cohesion: 0.12
Nodes (3): ShutdownScreen, TargetPingCard, test_quit_exits_immediately_when_idle()

### Community 188 - "speed_providers_http.py"
Cohesion: 0.09
Nodes (9): _ChunkStream, CloudflareProvider, http_download_worker(), worker(), http_upload_worker(), worker(), measure_parallel(), add() (+1 more)

### Community 193 - "textual_plans.py"
Cohesion: 0.07
Nodes (31): _fmt_speed(), number(), text(), ActiveNetwork, apply_profile(), bind_to_network(), current_cycle(), CycleWindow (+23 more)

### Community 198 - "league_detector.py"
Cohesion: 0.11
Nodes (10): _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, _RejectLiveClientRedirects, _remote_address(), _validate_live_client_url() (+2 more)

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1000 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **119 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `t` to `test_auto_speed.py`, `VareduraTextualApp`, `stalker.py`, `main`, `textual_app.py`, `CamerasMixin`, `credenciais.py`, `work`, `PlansMixin`, `test_port_catalog.py`, `abrir_stream`, `save_network_config`, `WSLDockerCleaner`, `os`, `ShutdownScreen`, `test_android_adaptations.py`, `regioes.py`, `.on_button_pressed`, `handle_key`, `textual_plans.py`, `._compose_settings`, `TermuxMixin`, `TargetPickerScreen`, `DailyLogWriter`, `core.py`, `TermuxKeysMixin`, `ui_shared.py`, `quick_cleanup`, `test_layout.py`, `is_android`, `subprocess`, `._importar_credenciais`, `._accept_ping_result`, `export_combined_report`, `textual_cameras.py`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `VareduraTextualApp` (e.g. with `PingStats` and `test_settings_saves_auto_speed_interval()`) actually correct?**
  _`VareduraTextualApp` has 46 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `test_auto_speed.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10953058321479374 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `test_auto_speed.py`, `test_textual_app.py`, `t`, `ping_targets.py`, `main`, `textual_app.py`, `CamerasMixin`, `ContinuousSpeedTester`, `work`, `PlansMixin`, `test_port_catalog.py`, `run_textual_app`, `save_network_config`, `ShutdownScreen`, `.on_button_pressed`, `._compose_settings`, `.on_main_tab_activated`, `TermuxMixin`, `TargetPickerScreen`, `test_textual_cameras.py`, `DailyLogWriter`, `test_textual_cleanup_worker_uses_fake_cleaner`, `test_textual_docker_reward_and_achievement`, `TermuxKeysMixin`, `ui_shared.py`, `test_layout.py`, `is_android`, `test_textual_termux.py`, `subprocess`, `test_shutdown_close_resources_terminates_players`, `._accept_ping_result`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `VareduraTextualApp` be split into smaller, more focused modules?**
  _Cohesion score 0.06821480406386067 - nodes in this community are weakly interconnected._