# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 100 files · ~128,603 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2671 nodes · 6871 edges · 189 communities (78 shown, 111 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 536 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4a9e42ea`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ._compose_settings
- VareduraTextualApp
- league_detector.py
- test_textual_app.py
- Detection
- CameraBridge
- stalker.py
- WSLDockerCleaner
- PingScheduler
- compute_health_score
- ping_targets.py
- network_repairs.py
- test_rtsp_modules.py
- RepairConfirmationScreen
- main
- network_diagnostics.py
- CamerasMixin
- test_network_diagnostics.py
- Event
- ContinuousSpeedTester
- test_camera_bridge.py
- test_network_repairs.py
- AIStreamProcessor
- _load_camera_backend
- textual_app.py
- CommandResult
- PlansMixin
- scanner.py
- textual_cameras.py
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
- platform
- WSLDockerCleaner
- os
- install.ps1
- install.sh
- UnifiedCameraSource
- DataUsageTracker
- termux_env.py
- camera_bridge.py
- regioes.py
- handle_key
- current_cycle
- port_scanner.py
- _validate_app_ca
- FastComProvider
- mapa.py
- TermuxMixin
- LocationStore
- TargetPickerScreen
- time
- test_textual_cameras.py
- camera_bridge.py
- SpeedTestProvider
- obter_logger
- DailyLogWriter
- test_textual_cleanup_worker_uses_fake_cleaner
- test_textual_docker_reward_and_achievement
- SpeedtestNetProvider
- core.py
- TargetSelection
- PingProbeResult
- paths.py
- get_usage_tracker
- quick_cleanup
- camera_engine.py
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- is_termux
- test_textual_termux.py
- get_export_status
- test_i18n_parity.py
- test_android_adaptations.py
- .on_button_pressed
- test_shutdown_close_resources_terminates_players
- BridgeAlreadyRunning
- _escolher_arquivo_txt
- SimetProvider
- _ManualFuture
- ._compose_cameras
- os
- varedura
- termux_install.sh
- steps
- textual_plans.py
- run_textual_app
- test_termux_api_helpers
- PlanProfile

## God Nodes (most connected - your core abstractions)
1. `t()` - 204 edges
2. `VareduraTextualApp` - 174 edges
3. `WSLDockerCleaner` - 71 edges
4. `CamerasMixin` - 69 edges
5. `CameraBridge` - 52 edges
6. `PingTarget` - 47 edges
7. `_load_camera_backend()` - 38 edges
8. `PlanProfile` - 37 edges
9. `main()` - 37 edges
10. `PingScheduler` - 37 edges

## Surprising Connections (you probably didn't know these)
- `test_network_cards_reflow_for_any_terminal_size()` --uses--> `TargetPingCard`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `VareduraTextualApp` --uses--> `NetworkSessionHistory`  [INFERRED]
  cli/textual_app.py → monitor/network_history.py
- `VareduraTextualApp` --uses--> `PingStats`  [INFERRED]
  cli/textual_app.py → monitor/stalker.py
- `test_capture_screenshot_saves_svg_and_txt()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `test_diagnosis_renders_repair_actions_inside_responsive_grid()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py

## Import Cycles
- 2-file cycle: `cli/textual_app.py -> cli/textual_cameras.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_plans.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_termux.py -> cli/textual_app.py`

## Communities (189 total, 111 thin omitted)

### Community 0 - "._compose_settings"
Cohesion: 0.15
Nodes (4): build_settings_status_table(), load_git_autoupdate_pref(), get_language(), get_supported_languages()

### Community 1 - "VareduraTextualApp"
Cohesion: 0.05
Nodes (7): VareduraTextualApp, stop_continuous_testing(), test_additional_targets_do_not_update_primary_health_sparkline(), test_callback_from_previous_network_run_is_discarded(), test_late_league_callback_cannot_reenable_disabled_detector(), test_shutdown_stop_monitors_sets_events(), test_target_card_statistics_include_jitter_trend_and_live_league_ip()

### Community 2 - "league_detector.py"
Cohesion: 0.05
Nodes (42): _valid_legacy_host(), _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, LeagueDetectionResult, LeagueDetectorState (+34 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.08
Nodes (28): ShutdownScreen, PortInfo, PortScannerState, ProcessConnections, _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring() (+20 more)

### Community 4 - "Detection"
Cohesion: 0.10
Nodes (10): test_line_crossing_rule(), test_nms_suppression(), test_zone_intrusion_rule(), Detection, nms(), EventSeverity, GeometricRule, LineCrossingRule (+2 more)

### Community 5 - "CameraBridge"
Cohesion: 0.11
Nodes (7): _atomic_write_json(), CameraBridge, order(), CaptureResult, _iso_now(), _read_json(), _replace_with_retry()

### Community 6 - "stalker.py"
Cohesion: 0.06
Nodes (15): check_keyboard(), ContractInfo, _draw_extra_pages(), _draw_text_page(), _flush_stdin(), get_ping_command(), get_top_network_hogs(), _get_top_network_hogs_fallback() (+7 more)

### Community 7 - "WSLDockerCleaner"
Cohesion: 0.10
Nodes (4): main(), WSLDockerCleaner, test_parse_wsl_distros_drops_shell_metacharacters(), test_stop_docker_wsl_uses_elevated_batch_without_process_errors()

### Community 8 - "PingScheduler"
Cohesion: 0.10
Nodes (24): PingScheduler, loop(), TargetRole, _TargetState, _Clock, _gateway(), _league(), _ManualExecutor (+16 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.06
Nodes (24): _Flight, build_ping_command(), _failure_status(), HostKind, _is_android_env(), parse_ping_latency(), PingStatus, probe_ping() (+16 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.07
Nodes (24): DiagnosisReport, ProbeKind, _action_id(), _disruptive_block_reason(), _flush_preview(), _kill_process(), list_repair_actions(), list_repair_guidance() (+16 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.13
Nodes (15): carregar_lista(), combinar_credenciais(), hosts_da_faixa(), normalizar_faixa(), test_carregar_lista_arquivo_ausente(), test_carregar_lista_ignora_branco_e_comentarios(), test_combinar_credenciais_apenas_uma_lista(), test_combinar_credenciais_produto() (+7 more)

### Community 15 - "main"
Cohesion: 0.09
Nodes (13): run_full_scan(), analyze_lag_source(), is_android(), main(), _initial_port_scan(), make_connections_panel(), make_header(), make_help_panel() (+5 more)

### Community 16 - "network_diagnostics.py"
Cohesion: 0.18
Nodes (8): classify_diagnosis(), collect_network_snapshot(), Evidence, _evidence_for_snapshot(), _failure_probe(), _local_probes(), NetworkSnapshot, ProbeResult

### Community 17 - "CamerasMixin"
Cohesion: 0.08
Nodes (3): CamerasMixin, _worker(), t()

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.08
Nodes (31): DiagnosticOptions, NetworkDiagnosticEngine, ProxyConfiguration, run_network_diagnosis(), SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner (+23 more)

### Community 19 - "Event"
Cohesion: 0.07
Nodes (13): _bounded_daemon_call(), _collect_linux_dhcp_configuration(), CommandRunner, _http_failure_cause(), HttpObservation, _parse_nm_active_uuid(), _parse_nm_ipv4_method(), ProbeBackend (+5 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.06
Nodes (10): ContinuousSpeedTester, SpeedStats, SpeedTestConfig, test_bandwidth_worker_cancellation_is_observed_promptly(), test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers(), test_prepared_bandwidth_test_honors_cancel_before_worker_starts(), fail_if_provider_runs() (+2 more)

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.18
Nodes (32): command(), FakeRunner, make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic() (+24 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.19
Nodes (34): Confidence, FailureCause, NetworkInterface, NetworkState, ProbeStatus, RepairExecutor, RepairKind, RepairStatus (+26 more)

### Community 25 - "AIStreamProcessor"
Cohesion: 0.11
Nodes (6): test_motion_heatmap(), test_stream_processor_pipeline(), MotionHeatmap, SpatialEvent, AIStreamProcessor, VideoFrame

### Community 26 - "_load_camera_backend"
Cohesion: 0.08
Nodes (23): monta(), monta(), _load_camera_backend(), adicionar_par(), carregar_conhecidos(), carregar_vault(), CredencialIP, esquecer_ip() (+15 more)

### Community 28 - "textual_app.py"
Cohesion: 0.05
Nodes (28): RichRenderable, _add_common_status_rows(), anatel_minimums(), build_cleanup_status_panel(), build_cleanup_steps_table(), build_dashboard_status(), build_ports_summary(), build_scanner_tables() (+20 more)

### Community 29 - "CommandResult"
Cohesion: 0.17
Nodes (9): CommandResult, RepairAction, RepairResult, RepairRunner, run(), run(), run(), run() (+1 more)

### Community 30 - "PlansMixin"
Cohesion: 0.13
Nodes (5): _fmt_number(), _fmt_speed(), PlansMixin, find_profile(), profiles_to_prefs()

### Community 31 - "scanner.py"
Cohesion: 0.12
Nodes (9): _base24(), detectar_redes(), _eh_privado_utilizavel(), _ip_primario(), _ips_hostname(), RedeLocal, _build_rtsp_request(), ResultadoRTSP (+1 more)

### Community 32 - "textual_cameras.py"
Cohesion: 0.10
Nodes (6): _format_bytes(), _detect_system_language(), init(), _load_preference(), _load_translations(), save_preference()

### Community 33 - "server.py"
Cohesion: 0.11
Nodes (15): _confirmation_required(), docker_full_cleanup(), docker_quick_cleanup(), docker_status(), _dry_run_preview(), get_logs(), _is_docker_running(), port_scan() (+7 more)

### Community 34 - "load_network_config"
Cohesion: 0.17
Nodes (14): load_network_config(), _verified_stored_app_ca(), encrypt_xiongmai_digest(), encrypt_xiongmai_password(), _set_prefs(), test_clean_install_requires_target_onboarding(), test_corrupt_numeric_preferences_fall_back_before_first_compose(), test_corrupt_schema_and_invalid_legacy_host_return_to_onboarding() (+6 more)

### Community 35 - "data_usage.py"
Cohesion: 0.26
Nodes (6): _atomic_write(), load_speed_samples(), record_speed_sample(), samples_for_report(), SpeedSample, test_speed_history_roundtrip_filters_by_profile_and_cycle()

### Community 36 - "PingTarget"
Cohesion: 0.13
Nodes (13): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingTarget, TargetCategory, _result(), test_csv_rows_are_contiguous_by_target_generation() (+5 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.14
Nodes (4): test_hls_h264_uses_remux_without_audio(), test_snapshot_failure_is_reduced_to_safe_enum(), FFmpegRunner, HlsProcess

### Community 40 - "MultiProviderSpeedTester"
Cohesion: 0.13
Nodes (3): get_multi_provider(), MultiProviderSpeedTester, ProgressState

### Community 41 - "network_diagnostics.py"
Cohesion: 0.09
Nodes (28): _collect_proxy_configuration(), _default_route_command(), DiagnosticCancelled, _interface_addresses(), _parse_macos_dhcp_configuration(), _parse_macos_network_services(), _parse_resolv_lines(), _parse_route() (+20 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.10
Nodes (7): NetIPPacket, XiongmaiNetIPClient, _delayed_stop(), MockNetIPServer, test_netip_client_workflow(), test_netip_packet_incomplete_buffer(), test_netip_packet_serialization()

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.15
Nodes (8): BrasilBandaLargaProvider, _safe_quit(), FakeDriver, test_provider_cleanup_quits_and_clears_driver(), test_provider_cleanup_without_driver_is_safe(), test_safe_quit_calls_quit(), test_safe_quit_fallback_kills_process(), test_safe_quit_handles_none()

### Community 49 - "test_docker_cleanup.py"
Cohesion: 0.08
Nodes (16): CleanupStepResult, test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers() (+8 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.10
Nodes (12): sort_key(), classify_exposure(), describe_port(), is_exposed(), _load(), test_catalog_keys_translated(), test_classify_exposure(), test_describe_port_ephemeral() (+4 more)

### Community 51 - "shutil"
Cohesion: 0.09
Nodes (19): abrir_stream(), _achar_exe(), capturar_e_abrir_snapshot(), comando_mpv_terminal(), detectar_player(), erro_se_morreu(), _ffplay_disponivel(), _ffprobe_disponivel() (+11 more)

### Community 52 - "platform"
Cohesion: 0.18
Nodes (12): detect_default_gateway(), _detect_unix(), _detect_windows(), _patch_run(), test_detect_default_gateway_dispatches_by_platform(), test_detect_default_gateway_returns_none_on_total_failure(), test_detect_unix_falls_back_through_android_strategies(), test_detect_unix_falls_back_to_netstat() (+4 more)

### Community 53 - "WSLDockerCleaner"
Cohesion: 0.13
Nodes (4): _strip_powershell_clixml(), _drain_and_wait(), stream_reader(), test_powershell_clixml_progress_is_removed_from_stderr()

### Community 54 - "os"
Cohesion: 0.12
Nodes (15): get_speed_tester(), SpeedTestResult, start_continuous_testing(), export_combined_report(), _generate_combined_pdf_worker(), prompt_export_report(), snapshot_ping_history(), _pdf_text() (+7 more)

### Community 55 - "install.ps1"
Cohesion: 0.27
Nodes (18): Add-ToUserPath(), Get-CmdVersion(), Ask-Action(), Check-Dependencies(), Confirm-Yes(), Detect-OS(), Do-Check(), Do-Install() (+10 more)

### Community 56 - "install.sh"
Cohesion: 0.28
Nodes (20): cmd_exists(), get_version(), is_installed(), main(), refresh_path(), install.sh script, ask_action(), check_dependencies() (+12 more)

### Community 58 - "UnifiedCameraSource"
Cohesion: 0.12
Nodes (4): CameraMetadata, UnifiedCameraSource, SofiaP2PClient, test_unified_camera_source_netip()

### Community 60 - "termux_env.py"
Cohesion: 0.08
Nodes (28): test_collect_android_telemetry_battery_api_fallback_and_never_raises(), test_discover_termux_tools_builtins_claro_shortcuts_and_custom(), test_discover_termux_tools_ignores_invalid_custom_json(), test_env_detection_flags(), test_root_and_claro_suite_detection(), test_termux_services_list_and_toggle(), AndroidTelemetry, collect_android_telemetry() (+20 more)

### Community 61 - "camera_bridge.py"
Cohesion: 0.12
Nodes (10): test_inventory_id_survives_password_change_inside_vendor_path(), test_inventory_ids_are_stable_and_private_state_has_no_endpoint(), test_inventory_never_uses_ip_as_default_name(), _canonical_rtsp_identity(), IdentityStore, load_private_inventory(), _resolution_parts(), _rtsp_without_auth() (+2 more)

### Community 62 - "regioes.py"
Cohesion: 0.17
Nodes (6): adicionar_regiao(), carregar_regioes(), Regiao, remover_regiao(), _salvar_json(), salvar_regioes()

### Community 63 - "handle_key"
Cohesion: 0.13
Nodes (12): handle_key(), load_prefs(), prompt_change_contracted_speed(), prompt_change_external(), prompt_change_gateway(), prompt_change_interval(), prompt_change_threshold(), save_prefs() (+4 more)

### Community 64 - "current_cycle"
Cohesion: 0.18
Nodes (5): current_cycle(), CycleWindow, quota_status(), QuotaStatus, test_cycle_rolls_forward_and_quota_projection()

### Community 66 - "port_scanner.py"
Cohesion: 0.13
Nodes (17): get_listening_ports(), get_process_connections_count(), get_system_network_stats(), _read_proc_meminfo(), _read_proc_net_totals(), _safe_net_connections(), search_port(), _conn() (+9 more)

### Community 67 - "_validate_app_ca"
Cohesion: 0.21
Nodes (8): _system_ssl_context(), _certificate_is_ca(), visit(), _der_tlvs(), _normalized_ca_pem(), _store_app_ca(), _validate_app_ca(), test_fortinet_untrusted_ca_marker_is_explicitly_rejected()

### Community 68 - "FastComProvider"
Cohesion: 0.23
Nodes (3): FastComProvider, main(), run_provider()

### Community 69 - "mapa.py"
Cohesion: 0.16
Nodes (9): _widget(), cor_para(), _eh_terra(), _gerar_bitmap(), _interp(), Pino, projetar_celula(), _px_para_latlon() (+1 more)

### Community 71 - "TermuxMixin"
Cohesion: 0.12
Nodes (3): TermuxMixin, list_termux_services(), is_cron_update_enabled()

### Community 72 - "LocationStore"
Cohesion: 0.18
Nodes (5): CameraLocation, LocationStore, _parse_iso(), _utc_now(), _valid_uuid()

### Community 74 - "TargetPickerScreen"
Cohesion: 0.15
Nodes (5): TargetPickerScreen, on, pull_request, push, branches

### Community 75 - "time"
Cohesion: 0.10
Nodes (9): test_geometric_line_intersection(), test_iou_calculation(), test_point_in_polygon(), compute_iou(), ObjectDetector, YOLONanoDetector, ccw(), point_in_polygon() (+1 more)

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.29
Nodes (13): isolated_state(), open_cameras(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input(), test_cameras_credential_add_and_remove(), test_cameras_import_credential_lists(), test_cameras_open_port_saved_without_credential(), test_cameras_port_scan_populates_table() (+5 more)

### Community 77 - "camera_bridge.py"
Cohesion: 0.09
Nodes (15): configurar(), _redact_arg(), redact_sensitive(), RedactingFilter, RedactingFormatter, test_redacting_formatter_covers_exception_text(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth(), ActiveSession (+7 more)

### Community 79 - "obter_logger"
Cohesion: 0.24
Nodes (3): Geo, geolocalizar(), obter_logger()

### Community 80 - "DailyLogWriter"
Cohesion: 0.12
Nodes (3): DailyLogWriter, cleanup_label(), run_cleanup_steps()

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.11
Nodes (6): SpeedtestNetProvider, FakeProcess, test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "core.py"
Cohesion: 0.11
Nodes (8): main(), parse_args(), run_cmd(), get_docker_vhdx_paths(), _powershell_encoded_command(), _ps_single_quoted(), _temp_file_path(), test_get_docker_vhdx_paths_discovers_disk_layout()

### Community 86 - "TargetSelection"
Cohesion: 0.12
Nodes (9): merge_visible_selection(), create_custom_target(), target_by_id(), target_catalog(), TargetSelection, test_filtered_target_changes_preserve_hidden_selections(), test_catalog_has_stable_ids_and_unique_entries(), test_probe_ping_returns_structured_success() (+1 more)

### Community 87 - "PingProbeResult"
Cohesion: 0.18
Nodes (4): SchedulerTargetSnapshot, PingProbeResult, PingSample, fake_probe()

### Community 91 - "camera_engine.py"
Cohesion: 0.08
Nodes (10): CameraCapabilities, CameraFleetManager, CameraProtocol, parse_camera_url(), DiscoveredCamera, NetIPMsgId, PTZCommand, XiongmaiDiscovery (+2 more)

### Community 94 - "test_textual_termux.py"
Cohesion: 0.20
Nodes (11): isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard(), wait_until() (+3 more)

### Community 96 - "test_i18n_parity.py"
Cohesion: 0.39
Nodes (5): _field_names(), _load_locale(), test_i18n_all_values_non_empty_strings(), test_i18n_placeholder_parity(), test_i18n_pt_en_key_parity()

### Community 97 - "test_android_adaptations.py"
Cohesion: 0.13
Nodes (8): __getattr__(), StalkerConfig, _render(), test_dashboard_hides_docker_and_mcp_rows_without_docker_tab(), test_dashboard_traffic_uses_android_wifi_counters(), test_interfaces_fall_back_to_sysfs_when_stats_are_denied(), test_legacy_defaults_never_restore_speculative_external_target(), test_legacy_monitor_returns_without_ping_when_onboarding_is_incomplete()

### Community 98 - ".on_button_pressed"
Cohesion: 0.08
Nodes (4): save_network_config(), set_language(), PingStats, isolated_ui_prefs()

### Community 104 - "SimetProvider"
Cohesion: 0.22
Nodes (3): _chrome_service(), SimetProvider, test_chrome_service_suppresses_console_window()

### Community 116 - "os"
Cohesion: 0.09
Nodes (21): test_cli_status_and_check_json(), test_cron_toggle_preserves_other_entries(), test_resolve_github_token_precedence_and_no_secret_in_label(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run(), test_save_token_file_rejects_empty_or_multiline(), test_update_repository_states_and_cooldown(), send_termux_notification() (+13 more)

### Community 144 - "steps"
Cohesion: 0.10
Nodes (23): concurrency, cancel-in-progress, group, jobs, lint, test, name, runs-on (+15 more)

### Community 146 - "textual_plans.py"
Cohesion: 0.13
Nodes (10): _clean_ssid(), detect_active_network(), _kind_from_interface(), parse_netsh_wlan(), parse_route_get(), _run(), NetworkKind, _isolated_plan_storage() (+2 more)

### Community 183 - "test_termux_api_helpers"
Cohesion: 0.29
Nodes (4): test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_termux_api_helpers(), toggle_keyboard_page()

### Community 193 - "PlanProfile"
Cohesion: 0.09
Nodes (24): number(), text(), ActiveNetwork, apply_profile(), bind_to_network(), describe_binding(), evaluate_speed(), _iso_date() (+16 more)

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 939 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **111 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `CamerasMixin` to `._compose_settings`, `VareduraTextualApp`, `test_textual_app.py`, `stalker.py`, `WSLDockerCleaner`, `main`, `textual_plans.py`, `_load_camera_backend`, `textual_app.py`, `PlansMixin`, `textual_cameras.py`, `PingTarget`, `test_port_catalog.py`, `WSLDockerCleaner`, `os`, `handle_key`, `PlanProfile`, `TermuxMixin`, `TargetPickerScreen`, `DailyLogWriter`, `core.py`, `TargetSelection`, `quick_cleanup`, `is_termux`, `test_android_adaptations.py`, `.on_button_pressed`, `.compose`, `.cleanup_temp_files_async`, `._compose_cameras`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `VareduraTextualApp` (e.g. with `NetworkSessionHistory` and `PingStats`) actually correct?**
  _`VareduraTextualApp` has 44 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `VareduraTextualApp` be split into smaller, more focused modules?**
  _Cohesion score 0.051106639839034206 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `._compose_settings`, `test_textual_app.py`, `RepairConfirmationScreen`, `network_diagnostics.py`, `CamerasMixin`, `ContinuousSpeedTester`, `textual_app.py`, `PlansMixin`, `load_network_config`, `PingTarget`, `test_port_catalog.py`, `run_textual_app`, `.on_main_tab_activated`, `TermuxMixin`, `TargetPickerScreen`, `test_textual_cameras.py`, `DailyLogWriter`, `test_textual_cleanup_worker_uses_fake_cleaner`, `test_textual_docker_reward_and_achievement`, `is_termux`, `test_textual_termux.py`, `get_export_status`, `.on_button_pressed`, `test_shutdown_close_resources_terminates_players`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `league_detector.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05078855920876771 - nodes in this community are weakly interconnected._