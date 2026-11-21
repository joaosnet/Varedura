# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 104 files · ~131,589 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2741 nodes · 7029 edges · 208 communities (85 shown, 123 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 526 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `85ab1794`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- VareduraTextualApp
- league_detector.py
- test_textual_app.py
- test_ai_vision.py
- CameraBridge
- stalker.py
- t
- PingScheduler
- compute_health_score
- ping_targets.py
- network_repairs.py
- test_rtsp_modules.py
- detect_active_network
- main
- textual_app.py
- CamerasMixin
- test_network_diagnostics.py
- Event
- ContinuousSpeedTester
- test_camera_bridge.py
- test_network_repairs.py
- AIStreamProcessor
- credenciais.py
- ._compose_dashboard
- CommandResult
- PlansMixin
- scanner.py
- i18n/__init__.py
- server.py
- load_network_config
- data_usage.py
- PingTarget
- FFmpegRunner
- MultiProviderSpeedTester
- network_diagnostics.py
- NetIPPacket
- test_speed_cleanup.py
- test_docker_cleanup.py
- test_port_catalog.py
- shutil
- test_plan_profiles.py
- .run_command_async
- os
- install.ps1
- install.sh
- UnifiedCameraSource
- DataUsageTracker
- termux_env.py
- camera_bridge.py
- regioes.py
- handle_key
- QuotaStatus
- port_scanner.py
- FastComProvider
- mapa.py
- TermuxMixin
- LocationStore
- TargetPickerScreen
- subprocess
- test_textual_cameras.py
- redact_sensitive
- load_prefs
- obter_logger
- DailyLogWriter
- test_textual_cleanup_worker_uses_fake_cleaner
- test_textual_docker_reward_and_achievement
- SpeedtestNetProvider
- core.py
- TermuxKeysMixin
- SubprocessRepairRunner
- paths.py
- test_android_adaptations.py
- quick_cleanup
- camera_engine.py
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- .on_button_pressed
- test_textual_termux.py
- TargetSelection
- test_i18n_parity.py
- monitor/__init__.py
- _load_camera_backend
- test_termux_env.py
- test_shutdown_close_resources_terminates_players
- PingProbeResult
- Detection
- SimetProvider
- test_layout.py
- _ManualFuture
- time
- ._compose_settings
- test_xiongmai_p2p.py
- ._compose_cameras
- os
- varedura
- termux_install.sh
- ai_vision/__init__.py
- steps
- run_textual_app
- CameraFleetManager
- set_keyboard_key
- .to_bytes
- MotionHeatmap
- ShutdownScreen
- save_network_config
- PlanProfile
- RepairConfirmationScreen
- PingStats
- _HangingPopen
- ._importar_credenciais
- EventSeverity
- get_docker_vhdx_paths
- .start

## God Nodes (most connected - your core abstractions)
1. `t()` - 208 edges
2. `VareduraTextualApp` - 178 edges
3. `WSLDockerCleaner` - 71 edges
4. `CamerasMixin` - 69 edges
5. `CameraBridge` - 52 edges
6. `PingTarget` - 47 edges
7. `_load_camera_backend()` - 38 edges
8. `PingScheduler` - 37 edges
9. `main()` - 37 edges
10. `PlanProfile` - 36 edges

## Surprising Connections (you probably didn't know these)
- `test_network_cards_reflow_for_any_terminal_size()` --uses--> `TargetPingCard`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `test_quit_exits_immediately_when_idle()` --uses--> `ShutdownScreen`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `test_quit_shows_shutdown_screen_when_busy()` --uses--> `ShutdownScreen`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `test_compact_mode_only_on_narrow_screens()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_layout.py → cli/textual_app.py
- `test_theme_toggle_persists_and_narrow_header_has_no_subtitle()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_layout.py → cli/textual_app.py

## Import Cycles
- 2-file cycle: `cli/textual_app.py -> cli/textual_cameras.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_plans.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_termux.py -> cli/textual_app.py`

## Communities (208 total, 123 thin omitted)

### Community 1 - "VareduraTextualApp"
Cohesion: 0.06
Nodes (6): VareduraTextualApp, test_additional_targets_do_not_update_primary_health_sparkline(), test_callback_from_previous_network_run_is_discarded(), test_late_league_callback_cannot_reenable_disabled_detector(), test_shutdown_stop_monitors_sets_events(), test_target_card_statistics_include_jitter_trend_and_live_league_ip()

### Community 2 - "league_detector.py"
Cohesion: 0.07
Nodes (37): _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, LeagueDetectionResult, LeagueDetectorState, LeagueEndpoint (+29 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.12
Nodes (26): PortScannerState, ProcessConnections, _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring(), test_hidden_tabs_are_composed_only_when_opened(), test_network_cards_reflow_for_any_terminal_size() (+18 more)

### Community 4 - "test_ai_vision.py"
Cohesion: 0.14
Nodes (11): test_geometric_line_intersection(), test_iou_calculation(), test_line_crossing_rule(), test_nms_suppression(), test_point_in_polygon(), compute_iou(), nms(), ccw() (+3 more)

### Community 5 - "CameraBridge"
Cohesion: 0.10
Nodes (11): test_runtime_subdirectory_link_is_rejected(), _atomic_write_json(), CameraBridge, order(), _is_link_like(), _iso_now(), _parse_iso(), _read_json() (+3 more)

### Community 6 - "stalker.py"
Cohesion: 0.06
Nodes (14): check_keyboard(), ContractInfo, _draw_extra_pages(), _draw_text_page(), _flush_stdin(), get_last_export_path(), get_ping_command(), get_top_network_hogs() (+6 more)

### Community 7 - "t"
Cohesion: 0.11
Nodes (4): main(), main(), WSLDockerCleaner, t()

### Community 8 - "PingScheduler"
Cohesion: 0.12
Nodes (24): PingScheduler, TargetRole, PingStatus, TargetCategory, _Clock, _gateway(), _league(), _ManualExecutor (+16 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.08
Nodes (23): build_ping_command(), _failure_status(), _is_android_env(), parse_ping_latency(), probe_ping(), target_by_id(), _terminate_process(), validate_host() (+15 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.09
Nodes (25): DiagnosisReport, ProbeKind, _system_ssl_context(), _action_id(), _certificate_is_ca(), visit(), _der_tlvs(), _disruptive_block_reason() (+17 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.13
Nodes (15): carregar_lista(), combinar_credenciais(), hosts_da_faixa(), normalizar_faixa(), test_carregar_lista_arquivo_ausente(), test_carregar_lista_ignora_branco_e_comentarios(), test_combinar_credenciais_apenas_uma_lista(), test_combinar_credenciais_produto() (+7 more)

### Community 14 - "detect_active_network"
Cohesion: 0.10
Nodes (22): _clean_ssid(), detect_active_network(), detect_default_gateway(), _detect_unix(), _detect_windows(), _kind_from_interface(), parse_netsh_wlan(), parse_route_get() (+14 more)

### Community 15 - "main"
Cohesion: 0.07
Nodes (15): run_full_scan(), stop_continuous_testing(), analyze_lag_source(), get_export_status(), is_android(), main(), _initial_port_scan(), make_connections_panel() (+7 more)

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.10
Nodes (27): DiagnosticOptions, ProxyConfiguration, SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner, _interface(), _snapshot() (+19 more)

### Community 19 - "Event"
Cohesion: 0.08
Nodes (12): _bounded_daemon_call(), _collect_linux_dhcp_configuration(), CommandRunner, HttpObservation, _parse_nm_active_uuid(), _parse_nm_ipv4_method(), ProbeBackend, _redact_text() (+4 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.06
Nodes (10): ContinuousSpeedTester, SpeedStats, SpeedTestConfig, test_bandwidth_worker_cancellation_is_observed_promptly(), test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers(), test_prepared_bandwidth_test_honors_cancel_before_worker_starts(), fail_if_provider_runs() (+2 more)

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.24
Nodes (29): command(), make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic(), test_clear_location_is_idempotent_and_keeps_camera_in_catalog() (+21 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.21
Nodes (31): NetworkInterface, NetworkState, RepairExecutor, RepairKind, RepairStatus, _action(), _fake_der_certificate(), FakeRunner (+23 more)

### Community 25 - "AIStreamProcessor"
Cohesion: 0.16
Nodes (4): test_stream_processor_pipeline(), SpatialEvent, AIStreamProcessor, VideoFrame

### Community 26 - "credenciais.py"
Cohesion: 0.10
Nodes (16): monta(), monta(), CredencialIP, esquecer_ip(), lembrar_ip(), Par, remover_par(), resolver_ip() (+8 more)

### Community 28 - "._compose_dashboard"
Cohesion: 0.09
Nodes (7): _cleanup_checkbox_id(), RichRenderable, TargetPingCard, build_cleanup_status_panel(), build_scanner_tables(), build_tool_option(), cleanup_label_key()

### Community 29 - "CommandResult"
Cohesion: 0.16
Nodes (9): CommandResult, RepairAction, RepairResult, RepairRunner, run(), run(), run(), run() (+1 more)

### Community 30 - "PlansMixin"
Cohesion: 0.12
Nodes (3): _fmt_number(), _fmt_speed(), PlansMixin

### Community 31 - "scanner.py"
Cohesion: 0.21
Nodes (6): _base24(), detectar_redes(), _eh_privado_utilizavel(), _ip_primario(), _ips_hostname(), RedeLocal

### Community 32 - "i18n/__init__.py"
Cohesion: 0.18
Nodes (6): _detect_system_language(), init(), _load_preference(), _load_translations(), save_preference(), set_language()

### Community 33 - "server.py"
Cohesion: 0.09
Nodes (16): _confirmation_required(), docker_full_cleanup(), docker_quick_cleanup(), docker_status(), _dry_run_preview(), get_logs(), _is_docker_running(), port_scan() (+8 more)

### Community 34 - "load_network_config"
Cohesion: 0.28
Nodes (11): load_network_config(), _verified_stored_app_ca(), _set_prefs(), test_clean_install_requires_target_onboarding(), test_corrupt_numeric_preferences_fall_back_before_first_compose(), test_corrupt_schema_and_invalid_legacy_host_return_to_onboarding(), test_legacy_automatic_default_does_not_start_external_ping(), test_legacy_explicit_host_becomes_primary_custom_target() (+3 more)

### Community 35 - "data_usage.py"
Cohesion: 0.15
Nodes (10): _atomic_write(), get_usage_tracker(), load_speed_samples(), record_speed_sample(), samples_for_report(), SpeedSample, _quota_lines(), _pdf_text() (+2 more)

### Community 36 - "PingTarget"
Cohesion: 0.13
Nodes (12): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingTarget, _result(), test_csv_rows_are_contiguous_by_target_generation(), test_history_groups_targets_generations_and_sessions() (+4 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.08
Nodes (8): FakeProcess, FakeRunner, test_hls_h264_uses_remux_without_audio(), test_snapshot_failure_is_reduced_to_safe_enum(), test_snapshot_is_published_atomically_with_subprocess_mock(), CaptureResult, FFmpegRunner, HlsProcess

### Community 40 - "MultiProviderSpeedTester"
Cohesion: 0.10
Nodes (4): get_multi_provider(), MultiProviderSpeedTester, SpeedTestProvider, SpeedTestResult

### Community 41 - "network_diagnostics.py"
Cohesion: 0.06
Nodes (45): _valid_legacy_host(), classify_diagnosis(), collect_network_snapshot(), _collect_proxy_configuration(), Confidence, _default_route_command(), DiagnosticCancelled, Evidence (+37 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.16
Nodes (4): NetIPPacket, XiongmaiNetIPClient, _delayed_stop(), test_netip_client_workflow()

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.12
Nodes (11): BrasilBandaLargaProvider, _chrome_service(), _safe_quit(), _sane_ping(), FakeDriver, test_chrome_service_suppresses_console_window(), test_provider_cleanup_quits_and_clears_driver(), test_safe_quit_calls_quit() (+3 more)

### Community 49 - "test_docker_cleanup.py"
Cohesion: 0.08
Nodes (17): CleanupStepResult, test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers() (+9 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.12
Nodes (13): sort_key(), build_ports_summary(), classify_exposure(), describe_port(), is_exposed(), _load(), test_catalog_keys_translated(), test_classify_exposure() (+5 more)

### Community 51 - "shutil"
Cohesion: 0.10
Nodes (13): _worker(), abrir_stream(), _achar_exe(), capturar_e_abrir_snapshot(), comando_mpv_terminal(), detectar_player(), erro_se_morreu(), _ffplay_disponivel() (+5 more)

### Community 52 - "test_plan_profiles.py"
Cohesion: 0.15
Nodes (9): ActiveNetwork, evaluate_speed(), select_profile(), SpeedVerdict, _isolated_plan_storage(), _sample(), test_evaluate_speed_reference_thresholds(), test_mobile_network_never_falls_back_to_fixed_plan() (+1 more)

### Community 53 - ".run_command_async"
Cohesion: 0.16
Nodes (4): _strip_powershell_clixml(), _drain_and_wait(), stream_reader(), test_powershell_clixml_progress_is_removed_from_stderr()

### Community 54 - "os"
Cohesion: 0.18
Nodes (11): get_speed_tester(), SpeedTestResult, export_combined_report(), _generate_combined_pdf_worker(), snapshot_ping_history(), cleanup_exports(), test_generate_small_pdf(), test_large_history_downsampling_and_full_flag() (+3 more)

### Community 55 - "install.ps1"
Cohesion: 0.27
Nodes (18): Add-ToUserPath(), Get-CmdVersion(), Ask-Action(), Check-Dependencies(), Confirm-Yes(), Detect-OS(), Do-Check(), Do-Install() (+10 more)

### Community 56 - "install.sh"
Cohesion: 0.28
Nodes (20): cmd_exists(), get_version(), is_installed(), main(), refresh_path(), install.sh script, ask_action(), check_dependencies() (+12 more)

### Community 58 - "UnifiedCameraSource"
Cohesion: 0.10
Nodes (5): CameraMetadata, UnifiedCameraSource, SofiaP2PClient, test_unified_camera_source_netip(), MockNetIPServer

### Community 60 - "termux_env.py"
Cohesion: 0.14
Nodes (17): test_env_detection_flags(), AndroidTelemetry, collect_android_telemetry(), _collect_battery(), _collect_ips(), _collect_memory(), _collect_proc_net_dev(), _collect_uptime() (+9 more)

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
Cohesion: 0.12
Nodes (18): get_listening_ports(), get_process_connections_count(), get_system_network_stats(), PortInfo, _read_proc_meminfo(), _read_proc_net_totals(), _safe_net_connections(), search_port() (+10 more)

### Community 68 - "FastComProvider"
Cohesion: 0.23
Nodes (3): FastComProvider, main(), run_provider()

### Community 69 - "mapa.py"
Cohesion: 0.16
Nodes (9): _widget(), cor_para(), _eh_terra(), _gerar_bitmap(), _interp(), Pino, projetar_celula(), _px_para_latlon() (+1 more)

### Community 71 - "TermuxMixin"
Cohesion: 0.11
Nodes (4): _format_bytes(), TermuxMixin, list_termux_services(), is_cron_update_enabled()

### Community 72 - "LocationStore"
Cohesion: 0.24
Nodes (3): CameraLocation, LocationStore, _valid_uuid()

### Community 74 - "TargetPickerScreen"
Cohesion: 0.17
Nodes (5): TargetPickerScreen, on, pull_request, push, branches

### Community 75 - "subprocess"
Cohesion: 0.13
Nodes (11): test_termux_api_helpers(), copy_to_clipboard(), has_native_dialog(), _pgrep_active(), _run_service_cmd(), send_termux_notification(), share_file(), toggle_keyboard_page() (+3 more)

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.40
Nodes (12): open_cameras(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input(), test_cameras_credential_add_and_remove(), test_cameras_import_credential_lists(), test_cameras_open_port_saved_without_credential(), test_cameras_port_scan_populates_table(), test_cameras_rede_action_bar_and_empty_selection() (+4 more)

### Community 77 - "redact_sensitive"
Cohesion: 0.31
Nodes (3): _redact_arg(), redact_sensitive(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth()

### Community 78 - "load_prefs"
Cohesion: 0.08
Nodes (12): theme_name(), load_cleanup_steps(), load_dark_theme_pref(), load_git_last_check(), load_prefs(), save_cleanup_steps(), save_dark_theme_pref(), save_git_autoupdate_pref() (+4 more)

### Community 79 - "obter_logger"
Cohesion: 0.16
Nodes (4): Geo, geolocalizar(), configurar(), obter_logger()

### Community 80 - "DailyLogWriter"
Cohesion: 0.12
Nodes (3): DailyLogWriter, cleanup_label(), run_cleanup_steps()

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.16
Nodes (5): SpeedtestNetProvider, test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "core.py"
Cohesion: 0.09
Nodes (9): parse_args(), run_cmd(), _powershell_encoded_command(), _ps_single_quoted(), _temp_file_path(), buscar_prefixos_por_asn(), obter_amostra_aleatoria(), obter_blocos_rede() (+1 more)

### Community 87 - "SubprocessRepairRunner"
Cohesion: 0.13
Nodes (7): _kill_process(), _powershell_single_quote(), SubprocessRepairRunner, _windows_elevated_script(), test_networkmanager_checkpoint_receives_explicit_restore_answer(), test_windows_helper_script_accepts_only_enumerated_operations(), test_windows_renew_script_rejects_wildcards_and_checks_ipv6_exit()

### Community 89 - "test_android_adaptations.py"
Cohesion: 0.09
Nodes (12): anatel_minimums(), build_dashboard_status(), _fmt_android_battery(), _fmt_data_mb(), _fmt_memory(), _fmt_ping(), _fmt_traffic(), format_duration() (+4 more)

### Community 91 - "camera_engine.py"
Cohesion: 0.19
Nodes (4): CameraCapabilities, CameraProtocol, parse_camera_url(), test_parse_camera_url()

### Community 94 - "test_textual_termux.py"
Cohesion: 0.23
Nodes (11): test_compact_mode_only_on_narrow_screens(), isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard() (+3 more)

### Community 95 - "TargetSelection"
Cohesion: 0.14
Nodes (6): merge_visible_selection(), create_custom_target(), target_catalog(), TargetSelection, test_filtered_target_changes_preserve_hidden_selections(), test_selection_round_trip_and_legacy_migration()

### Community 96 - "test_i18n_parity.py"
Cohesion: 0.39
Nodes (5): _field_names(), _load_locale(), test_i18n_all_values_non_empty_strings(), test_i18n_placeholder_parity(), test_i18n_pt_en_key_parity()

### Community 97 - "monitor/__init__.py"
Cohesion: 0.33
Nodes (3): __getattr__(), StalkerConfig, test_legacy_defaults_never_restore_speculative_external_target()

### Community 99 - "_load_camera_backend"
Cohesion: 0.11
Nodes (10): _load_camera_backend(), carregar_conhecidos(), carregar_vault(), _build_rtsp_request(), escanear_portas_camera(), escanear_rede(), ResultadoRTSP, testar_porta() (+2 more)

### Community 100 - "test_termux_env.py"
Cohesion: 0.09
Nodes (15): test_collect_android_telemetry_battery_api_fallback_and_never_raises(), test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_discover_termux_tools_builtins_claro_shortcuts_and_custom(), test_discover_termux_tools_ignores_invalid_custom_json(), test_native_text_dialog_parses_ok_and_cancel(), test_root_and_claro_suite_detection(), test_termux_services_list_and_toggle() (+7 more)

### Community 102 - "PingProbeResult"
Cohesion: 0.13
Nodes (7): _Flight, SchedulerTargetSnapshot, _TargetState, HostKind, PingProbeResult, PingSample, fake_probe()

### Community 103 - "Detection"
Cohesion: 0.18
Nodes (5): test_zone_intrusion_rule(), Detection, GeometricRule, LoiteringRule, ZoneIntrusionRule

### Community 104 - "SimetProvider"
Cohesion: 0.16
Nodes (3): ProgressState, SimetProvider, test_provider_cleanup_without_driver_is_safe()

### Community 105 - "test_layout.py"
Cohesion: 0.24
Nodes (3): columns_for(), layout_tier(), test_layout_tiers_and_columns()

### Community 109 - "._compose_settings"
Cohesion: 0.13
Nodes (8): _add_common_status_rows(), build_cleanup_steps_table(), build_settings_status_table(), cleanup_summary(), get_cleanup_steps(), load_git_autoupdate_pref(), get_language(), get_supported_languages()

### Community 111 - "test_xiongmai_p2p.py"
Cohesion: 0.18
Nodes (5): encrypt_xiongmai_digest(), encrypt_xiongmai_password(), NetIPMsgId, PTZCommand, test_xiongmai_password_encryption()

### Community 116 - "os"
Cohesion: 0.10
Nodes (20): test_cli_status_and_check_json(), test_cron_toggle_preserves_other_entries(), test_resolve_github_token_precedence_and_no_secret_in_label(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run(), test_save_token_file_rejects_empty_or_multiline(), test_update_repository_states_and_cooldown(), _alt_token_file_path() (+12 more)

### Community 144 - "steps"
Cohesion: 0.10
Nodes (23): concurrency, cancel-in-progress, group, jobs, lint, test, name, runs-on (+15 more)

### Community 181 - "CameraFleetManager"
Cohesion: 0.22
Nodes (3): CameraFleetManager, DiscoveredCamera, test_camera_fleet_manager()

### Community 182 - "set_keyboard_key"
Cohesion: 0.31
Nodes (6): test_extra_keys_macros_and_temporary_keyboard_key(), extra_key_macros(), visit(), _read_extra_keys(), set_keyboard_key(), termux_properties_path()

### Community 183 - ".to_bytes"
Cohesion: 0.24
Nodes (3): XiongmaiDiscovery, test_netip_packet_incomplete_buffer(), test_netip_packet_serialization()

### Community 187 - "save_network_config"
Cohesion: 0.22
Nodes (4): save_network_config(), _prefs(), isolated_ui_prefs(), isolated_state()

### Community 193 - "PlanProfile"
Cohesion: 0.10
Nodes (22): number(), text(), apply_profile(), bind_to_network(), current_cycle(), CycleWindow, describe_binding(), find_profile() (+14 more)

### Community 195 - "PingStats"
Cohesion: 0.29
Nodes (3): make_ascii_graph(), make_graph_panel(), PingStats

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 965 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **123 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `t` to `VareduraTextualApp`, `stalker.py`, `main`, `textual_app.py`, `CamerasMixin`, `credenciais.py`, `._compose_dashboard`, `PlansMixin`, `i18n/__init__.py`, `PingTarget`, `test_port_catalog.py`, `shutil`, `.run_command_async`, `os`, `ShutdownScreen`, `regioes.py`, `handle_key`, `PlanProfile`, `RepairConfirmationScreen`, `PingStats`, `._importar_credenciais`, `TermuxMixin`, `TargetPickerScreen`, `subprocess`, `load_prefs`, `DailyLogWriter`, `core.py`, `TermuxKeysMixin`, `test_android_adaptations.py`, `quick_cleanup`, `.on_button_pressed`, `TargetSelection`, `.action_capture_screenshot`, `_load_camera_backend`, `test_layout.py`, `._compose_settings`, `._compose_cameras`, `os`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `VareduraTextualApp` (e.g. with `test_compact_mode_only_on_narrow_screens()` and `test_theme_toggle_persists_and_narrow_header_has_no_subtitle()`) actually correct?**
  _`VareduraTextualApp` has 44 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `VareduraTextualApp` be split into smaller, more focused modules?**
  _Cohesion score 0.055299539170506916 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `test_textual_app.py`, `main`, `textual_app.py`, `CamerasMixin`, `ContinuousSpeedTester`, `._compose_dashboard`, `CommandResult`, `PlansMixin`, `PingTarget`, `test_port_catalog.py`, `run_textual_app`, `ShutdownScreen`, `._refresh_live_settings_status`, `RepairConfirmationScreen`, `.on_main_tab_activated`, `TermuxMixin`, `subprocess`, `test_textual_cameras.py`, `load_prefs`, `DailyLogWriter`, `test_textual_cleanup_worker_uses_fake_cleaner`, `test_textual_docker_reward_and_achievement`, `TermuxKeysMixin`, `.on_button_pressed`, `test_textual_termux.py`, `.action_capture_screenshot`, `test_shutdown_close_resources_terminates_players`, `test_layout.py`, `._compose_settings`, `os`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `league_detector.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06533646322378717 - nodes in this community are weakly interconnected._