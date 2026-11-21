# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 102 files · ~129,324 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2685 nodes · 6899 edges · 211 communities (88 shown, 123 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 527 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e55f8cab`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- on
- VareduraTextualApp
- league_detector.py
- test_textual_app.py
- GeometricRule
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
- credenciais.py
- textual_app.py
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
- detect_active_network
- WSLDockerCleaner
- os
- install.ps1
- install.sh
- UnifiedCameraSource
- DataUsageTracker
- termux_env.py
- camera_bridge.py
- _load_camera_backend
- handle_key
- current_cycle
- port_scanner.py
- ._accept_ping_result
- FastComProvider
- mapa.py
- TermuxMixin
- LocationStore
- TargetPickerScreen
- rules.py
- test_textual_cameras.py
- redact_sensitive
- save_network_config
- textual_cameras.py
- DailyLogWriter
- test_textual_cleanup_worker_uses_fake_cleaner
- test_textual_docker_reward_and_achievement
- SpeedtestNetProvider
- core.py
- TargetSelection
- PingProbeResult
- paths.py
- test_android_adaptations.py
- quick_cleanup
- ping_targets.py
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- is_termux
- test_textual_termux.py
- json
- monitor/__init__.py
- ._render_target_cards
- Par
- SubprocessRepairRunner
- .compact_vhdx_files
- ._browse_arquivo
- SimetProvider
- test_layout.py
- _ManualFuture
- SpeedTestConfig
- get_cleanup_steps
- test_xiongmai_p2p.py
- ._compose_cameras
- os
- varedura
- termux_install.sh
- ci.yml
- PlanProfile
- Detection
- CameraFleetManager
- run_textual_app
- test_ai_vision.py
- .configure_wsl_sparse
- test_camera_engine.py
- MotionHeatmap
- .to_bytes
- LineCrossingRule
- PlanProfile
- steps
- LeagueEndpoint
- test
- PingStats
- _HangingPopen
- run_cleanup_steps
- build_scanner_tables
- stop_continuous_testing
- check_keyboard
- export_combined_report
- get_top_network_hogs

## God Nodes (most connected - your core abstractions)
1. `t()` - 204 edges
2. `VareduraTextualApp` - 174 edges
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
- `test_capture_screenshot_saves_svg_and_txt()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py

## Import Cycles
- 2-file cycle: `cli/textual_app.py -> cli/textual_cameras.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_plans.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_termux.py -> cli/textual_app.py`

## Communities (211 total, 123 thin omitted)

### Community 0 - "on"
Cohesion: 0.16
Nodes (4): on, pull_request, push, branches

### Community 1 - "VareduraTextualApp"
Cohesion: 0.06
Nodes (3): VareduraTextualApp, test_shutdown_close_resources_terminates_players(), test_shutdown_stop_monitors_sets_events()

### Community 2 - "league_detector.py"
Cohesion: 0.07
Nodes (33): _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, LeagueDetectionResult, LeagueDetectorState, LeagueMatchDetector (+25 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.11
Nodes (27): PortInfo, PortScannerState, ProcessConnections, _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring(), test_hidden_tabs_are_composed_only_when_opened() (+19 more)

### Community 4 - "GeometricRule"
Cohesion: 0.18
Nodes (5): test_zone_intrusion_rule(), EventSeverity, GeometricRule, LoiteringRule, ZoneIntrusionRule

### Community 5 - "CameraBridge"
Cohesion: 0.11
Nodes (8): _atomic_write_json(), CameraBridge, order(), _iso_now(), _parse_iso(), _read_json(), _utc_now(), _valid_uuid()

### Community 6 - "stalker.py"
Cohesion: 0.08
Nodes (10): ContractInfo, _draw_extra_pages(), _draw_text_page(), get_last_export_path(), get_ping_command(), parse_ping(), _pct_of(), record_ping_sample() (+2 more)

### Community 8 - "PingScheduler"
Cohesion: 0.11
Nodes (23): PingScheduler, loop(), TargetRole, PingStatus, _Clock, _gateway(), _ManualExecutor, _result() (+15 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.08
Nodes (23): build_ping_command(), create_custom_target(), _failure_status(), _is_android_env(), parse_ping_latency(), probe_ping(), target_by_id(), _terminate_process() (+15 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.08
Nodes (26): DiagnosisReport, ProbeKind, _system_ssl_context(), _action_id(), _certificate_is_ca(), visit(), _der_tlvs(), _disruptive_block_reason() (+18 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.13
Nodes (15): carregar_lista(), combinar_credenciais(), hosts_da_faixa(), normalizar_faixa(), test_carregar_lista_arquivo_ausente(), test_carregar_lista_ignora_branco_e_comentarios(), test_combinar_credenciais_apenas_uma_lista(), test_combinar_credenciais_produto() (+7 more)

### Community 15 - "main"
Cohesion: 0.09
Nodes (13): analyze_lag_source(), get_export_status(), is_android(), main(), _initial_port_scan(), make_connections_panel(), make_header(), make_help_panel() (+5 more)

### Community 16 - "network_diagnostics.py"
Cohesion: 0.13
Nodes (13): classify_diagnosis(), Confidence, Evidence, _evidence_for_snapshot(), _failure_probe(), FailureCause, _http_failure_cause(), _local_probes() (+5 more)

### Community 17 - "CamerasMixin"
Cohesion: 0.09
Nodes (4): CamerasMixin, _worker(), t(), salvar_regioes()

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.09
Nodes (29): DiagnosticOptions, NetworkDiagnosticEngine, ProxyConfiguration, run_network_diagnosis(), SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner (+21 more)

### Community 19 - "Event"
Cohesion: 0.07
Nodes (13): _bounded_daemon_call(), _collect_linux_dhcp_configuration(), collect_network_snapshot(), CommandRunner, HttpObservation, _parse_nm_active_uuid(), _parse_nm_ipv4_method(), ProbeBackend (+5 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.09
Nodes (6): ContinuousSpeedTester, SpeedStats, test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers(), test_prepared_bandwidth_test_honors_cancel_before_worker_starts(), fail_if_provider_runs()

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.21
Nodes (30): command(), make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic(), test_clear_location_is_idempotent_and_keeps_camera_in_catalog() (+22 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.21
Nodes (31): NetworkInterface, NetworkState, RepairExecutor, RepairKind, RepairStatus, _action(), _fake_der_certificate(), FakeRunner (+23 more)

### Community 25 - "AIStreamProcessor"
Cohesion: 0.16
Nodes (4): test_stream_processor_pipeline(), SpatialEvent, AIStreamProcessor, VideoFrame

### Community 26 - "credenciais.py"
Cohesion: 0.12
Nodes (11): adicionar_par(), carregar_conhecidos(), CredencialIP, esquecer_ip(), lembrar_ip(), remover_par(), _sucesso(), salvar_conhecidos() (+3 more)

### Community 28 - "textual_app.py"
Cohesion: 0.10
Nodes (10): _cleanup_checkbox_id(), RichRenderable, build_cleanup_status_panel(), build_settings_status_table(), cleanup_label_key(), format_duration(), is_mcp_configured(), load_git_autoupdate_pref() (+2 more)

### Community 29 - "CommandResult"
Cohesion: 0.19
Nodes (8): CommandResult, RepairAction, RepairResult, run(), run(), run(), run(), run()

### Community 30 - "PlansMixin"
Cohesion: 0.15
Nodes (4): _fmt_number(), PlansMixin, find_profile(), profiles_to_prefs()

### Community 31 - "scanner.py"
Cohesion: 0.17
Nodes (6): _build_rtsp_request(), escanear_portas_camera(), escanear_rede(), ResultadoRTSP, testar_porta(), testar_rtsp()

### Community 32 - "i18n/__init__.py"
Cohesion: 0.18
Nodes (6): _detect_system_language(), init(), _load_preference(), _load_translations(), save_preference(), set_language()

### Community 33 - "server.py"
Cohesion: 0.09
Nodes (11): _confirmation_required(), docker_full_cleanup(), docker_quick_cleanup(), docker_status(), _dry_run_preview(), get_logs(), _is_docker_running(), port_scan() (+3 more)

### Community 34 - "load_network_config"
Cohesion: 0.19
Nodes (12): load_network_config(), _valid_legacy_host(), _verified_stored_app_ca(), legacy_fixed_profile(), _set_prefs(), test_clean_install_requires_target_onboarding(), test_corrupt_numeric_preferences_fall_back_before_first_compose(), test_corrupt_schema_and_invalid_legacy_host_return_to_onboarding() (+4 more)

### Community 35 - "data_usage.py"
Cohesion: 0.17
Nodes (9): _atomic_write(), get_usage_tracker(), load_speed_samples(), record_speed_sample(), samples_for_report(), SpeedSample, _pdf_text(), test_report_uses_active_profile_and_consumer_wording() (+1 more)

### Community 36 - "PingTarget"
Cohesion: 0.11
Nodes (17): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingTarget, TargetCategory, _result(), test_csv_rows_are_contiguous_by_target_generation() (+9 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.08
Nodes (8): FakeProcess, FakeRunner, test_hls_h264_uses_remux_without_audio(), test_snapshot_failure_is_reduced_to_safe_enum(), test_snapshot_is_published_atomically_with_subprocess_mock(), CaptureResult, FFmpegRunner, HlsProcess

### Community 40 - "MultiProviderSpeedTester"
Cohesion: 0.08
Nodes (5): get_multi_provider(), MultiProviderSpeedTester, ProgressState, SpeedTestProvider, SpeedTestResult

### Community 41 - "network_diagnostics.py"
Cohesion: 0.09
Nodes (27): _collect_proxy_configuration(), _default_route_command(), DiagnosticCancelled, _interface_addresses(), _parse_macos_dhcp_configuration(), _parse_macos_network_services(), _parse_resolv_lines(), _parse_route() (+19 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.18
Nodes (4): NetIPPacket, XiongmaiNetIPClient, _delayed_stop(), test_netip_client_workflow()

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.14
Nodes (9): BrasilBandaLargaProvider, _chrome_service(), _safe_quit(), FakeDriver, test_chrome_service_suppresses_console_window(), test_provider_cleanup_quits_and_clears_driver(), test_safe_quit_calls_quit(), test_safe_quit_fallback_kills_process() (+1 more)

### Community 49 - "test_docker_cleanup.py"
Cohesion: 0.11
Nodes (14): CleanupStepResult, test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers() (+6 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.12
Nodes (13): sort_key(), build_ports_summary(), classify_exposure(), describe_port(), is_exposed(), _load(), test_catalog_keys_translated(), test_classify_exposure() (+5 more)

### Community 51 - "shutil"
Cohesion: 0.11
Nodes (16): abrir_stream(), _achar_exe(), capturar_e_abrir_snapshot(), comando_mpv_terminal(), detectar_player(), _ffplay_disponivel(), _ffprobe_disponivel(), _montar_comando() (+8 more)

### Community 52 - "detect_active_network"
Cohesion: 0.09
Nodes (22): _clean_ssid(), detect_active_network(), detect_default_gateway(), _detect_unix(), _detect_windows(), _kind_from_interface(), parse_netsh_wlan(), parse_route_get() (+14 more)

### Community 53 - "WSLDockerCleaner"
Cohesion: 0.08
Nodes (6): _powershell_encoded_command(), _strip_powershell_clixml(), _drain_and_wait(), stream_reader(), test_parse_wsl_distros_drops_shell_metacharacters(), test_powershell_clixml_progress_is_removed_from_stderr()

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

### Community 60 - "termux_env.py"
Cohesion: 0.08
Nodes (27): test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_root_and_claro_suite_detection(), test_termux_api_helpers(), test_termux_services_list_and_toggle(), AndroidTelemetry, collect_android_telemetry(), _collect_memory() (+19 more)

### Community 61 - "camera_bridge.py"
Cohesion: 0.07
Nodes (20): parse_args(), test_inventory_id_survives_password_change_inside_vendor_path(), test_inventory_ids_are_stable_and_private_state_has_no_endpoint(), test_inventory_never_uses_ip_as_default_name(), ActiveSession, BridgeAlreadyRunning, build_parser(), _canonical_rtsp_identity() (+12 more)

### Community 62 - "_load_camera_backend"
Cohesion: 0.12
Nodes (8): _load_camera_backend(), carregar_vault(), adicionar_regiao(), carregar_regioes(), Regiao, remover_regiao(), erro_se_morreu(), test_video_erro_se_morreu_and_capturar_e_abrir_snapshot()

### Community 63 - "handle_key"
Cohesion: 0.14
Nodes (12): handle_key(), load_prefs(), prompt_change_contracted_speed(), prompt_change_gateway(), prompt_change_interval(), prompt_change_threshold(), prompt_export_report(), save_prefs() (+4 more)

### Community 64 - "current_cycle"
Cohesion: 0.14
Nodes (6): current_cycle(), CycleWindow, quota_status(), QuotaStatus, _quota_lines(), test_cycle_rolls_forward_and_quota_projection()

### Community 66 - "port_scanner.py"
Cohesion: 0.08
Nodes (24): get_listening_ports(), get_process_connections_count(), get_system_network_stats(), _read_proc_meminfo(), _read_proc_net_totals(), run_full_scan(), _safe_net_connections(), search_port() (+16 more)

### Community 67 - "._accept_ping_result"
Cohesion: 0.10
Nodes (3): anatel_minimums(), test_additional_targets_do_not_update_primary_health_sparkline(), test_callback_from_previous_network_run_is_discarded()

### Community 68 - "FastComProvider"
Cohesion: 0.23
Nodes (3): FastComProvider, main(), run_provider()

### Community 69 - "mapa.py"
Cohesion: 0.16
Nodes (9): _widget(), cor_para(), _eh_terra(), _gerar_bitmap(), _interp(), Pino, projetar_celula(), _px_para_latlon() (+1 more)

### Community 71 - "TermuxMixin"
Cohesion: 0.11
Nodes (4): _format_bytes(), TermuxMixin, list_termux_services(), is_cron_update_enabled()

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.40
Nodes (12): open_cameras(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input(), test_cameras_credential_add_and_remove(), test_cameras_import_credential_lists(), test_cameras_open_port_saved_without_credential(), test_cameras_port_scan_populates_table(), test_cameras_rede_action_bar_and_empty_selection() (+4 more)

### Community 77 - "redact_sensitive"
Cohesion: 0.15
Nodes (8): configurar(), _redact_arg(), redact_sensitive(), RedactingFilter, RedactingFormatter, test_redacting_formatter_covers_exception_text(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth(), configure_logging()

### Community 78 - "save_network_config"
Cohesion: 0.10
Nodes (11): load_git_last_check(), load_prefs(), save_cleanup_steps(), save_git_autoupdate_pref(), save_git_last_check(), save_network_config(), save_prefs(), prompt_change_external() (+3 more)

### Community 79 - "textual_cameras.py"
Cohesion: 0.12
Nodes (4): _parse_windows_adapter_ids(), Geo, geolocalizar(), obter_logger()

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.16
Nodes (5): SpeedtestNetProvider, test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "core.py"
Cohesion: 0.11
Nodes (7): run_cmd(), _temp_file_path(), buscar_prefixos_por_asn(), obter_amostra_aleatoria(), obter_blocos_rede(), obter_espaco_amostral_completo(), _salvar_json()

### Community 86 - "TargetSelection"
Cohesion: 0.13
Nodes (7): merge_visible_selection(), target_catalog(), TargetSelection, test_v3_unknown_ids_do_not_count_as_completed_selection(), test_filtered_target_changes_preserve_hidden_selections(), test_selection_enforces_five_persistent_and_primary(), test_selection_round_trip_and_legacy_migration()

### Community 87 - "PingProbeResult"
Cohesion: 0.18
Nodes (5): SchedulerTargetSnapshot, _TargetState, PingProbeResult, PingSample, fake_probe()

### Community 89 - "test_android_adaptations.py"
Cohesion: 0.12
Nodes (10): build_dashboard_status(), _fmt_android_battery(), _fmt_data_mb(), _fmt_memory(), _fmt_ping(), _fmt_traffic(), _render(), test_dashboard_hides_docker_and_mcp_rows_without_docker_tab() (+2 more)

### Community 91 - "ping_targets.py"
Cohesion: 0.11
Nodes (7): _remote_address(), _Flight, HostKind, CameraCapabilities, CameraProtocol, DiscoveredCamera, XiongmaiDiscovery

### Community 93 - "is_termux"
Cohesion: 0.08
Nodes (3): ShutdownScreen, TargetPingCard, is_termux()

### Community 94 - "test_textual_termux.py"
Cohesion: 0.23
Nodes (10): isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard(), wait_until() (+2 more)

### Community 96 - "json"
Cohesion: 0.17
Nodes (13): test_graphify_artifact_excludes_private_runtime_sources(), _field_names(), _load_locale(), test_i18n_all_values_non_empty_strings(), test_i18n_placeholder_parity(), test_i18n_pt_en_key_parity(), _probe_modules(), test_entrypoint_import_is_a_lightweight_dispatcher() (+5 more)

### Community 97 - "monitor/__init__.py"
Cohesion: 0.24
Nodes (4): __getattr__(), StalkerConfig, test_legacy_defaults_never_restore_speculative_external_target(), test_legacy_monitor_returns_without_ping_when_onboarding_is_incomplete()

### Community 98 - "._render_target_cards"
Cohesion: 0.12
Nodes (3): get_language(), test_late_league_callback_cannot_reenable_disabled_detector(), test_target_card_statistics_include_jitter_trend_and_live_league_ip()

### Community 99 - "Par"
Cohesion: 0.18
Nodes (7): monta(), monta(), Par, resolver_ip(), descobrir_stream(), InfoStream, validar_stream()

### Community 101 - "SubprocessRepairRunner"
Cohesion: 0.13
Nodes (7): _kill_process(), _powershell_single_quote(), SubprocessRepairRunner, _windows_elevated_script(), test_networkmanager_checkpoint_receives_explicit_restore_answer(), test_windows_helper_script_accepts_only_enumerated_operations(), test_windows_renew_script_rejects_wildcards_and_checks_ipv6_exit()

### Community 102 - ".compact_vhdx_files"
Cohesion: 0.16
Nodes (3): get_docker_vhdx_paths(), _ps_single_quoted(), test_get_docker_vhdx_paths_discovers_disk_layout()

### Community 105 - "test_layout.py"
Cohesion: 0.17
Nodes (4): columns_for(), layout_tier(), test_compact_mode_only_on_narrow_screens(), test_layout_tiers_and_columns()

### Community 108 - "SpeedTestConfig"
Cohesion: 0.14
Nodes (4): SpeedTestConfig, test_bandwidth_worker_cancellation_is_observed_promptly(), test_rich_speed_key_can_cancel_before_its_thread_starts(), test_speed_worker_is_prepared_before_schedule_and_can_cancel_immediately()

### Community 109 - "get_cleanup_steps"
Cohesion: 0.17
Nodes (6): _add_common_status_rows(), build_cleanup_steps_table(), cleanup_summary(), get_cleanup_steps(), load_cleanup_steps(), selected_cleanup_keys()

### Community 111 - "test_xiongmai_p2p.py"
Cohesion: 0.18
Nodes (5): encrypt_xiongmai_digest(), encrypt_xiongmai_password(), NetIPMsgId, PTZCommand, test_xiongmai_password_encryption()

### Community 116 - "os"
Cohesion: 0.08
Nodes (23): test_cli_status_and_check_json(), test_cron_toggle_preserves_other_entries(), test_resolve_github_token_precedence_and_no_secret_in_label(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run(), test_save_token_file_rejects_empty_or_multiline(), test_update_repository_states_and_cooldown(), send_termux_notification() (+15 more)

### Community 144 - "ci.yml"
Cohesion: 0.22
Nodes (8): concurrency, cancel-in-progress, group, jobs, lint, name, runs-on, name

### Community 146 - "PlanProfile"
Cohesion: 0.16
Nodes (10): _fmt_speed(), ActiveNetwork, apply_profile(), bind_to_network(), describe_binding(), PlanProfile, select_profile(), test_bind_to_network_prefers_ssid_then_gateway() (+2 more)

### Community 182 - "test_ai_vision.py"
Cohesion: 0.25
Nodes (6): test_iou_calculation(), test_nms_suppression(), test_point_in_polygon(), compute_iou(), nms(), point_in_polygon()

### Community 185 - "test_camera_engine.py"
Cohesion: 0.22
Nodes (3): parse_camera_url(), test_parse_camera_url(), MockNetIPServer

### Community 191 - "LineCrossingRule"
Cohesion: 0.25
Nodes (5): test_geometric_line_intersection(), test_line_crossing_rule(), ccw(), LineCrossingRule, segments_intersect()

### Community 193 - "PlanProfile"
Cohesion: 0.12
Nodes (14): number(), text(), evaluate_speed(), _iso_date(), new_profile_id(), _number(), PlanKind, profiles_from_prefs() (+6 more)

### Community 194 - "steps"
Cohesion: 0.36
Nodes (8): steps, continue-on-error, name, run, uses, with, steps, enable-cache

### Community 195 - "LeagueEndpoint"
Cohesion: 0.32
Nodes (3): LeagueEndpoint, mask_endpoint_ip(), test_privacy_mask_defaults_to_network_prefixes()

### Community 196 - "test"
Cohesion: 0.29
Nodes (7): test, os, fail-fast, matrix, name, runs-on, strategy

### Community 197 - "PingStats"
Cohesion: 0.29
Nodes (3): make_ascii_graph(), make_graph_panel(), PingStats

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 945 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **123 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `CamerasMixin` to `VareduraTextualApp`, `stalker.py`, `WSLDockerCleaner`, `RepairConfirmationScreen`, `main`, `PlanProfile`, `credenciais.py`, `textual_app.py`, `PlansMixin`, `i18n/__init__.py`, `load_network_config`, `test_port_catalog.py`, `WSLDockerCleaner`, `os`, `.configure_wsl_sparse`, `_load_camera_backend`, `handle_key`, `PlanProfile`, `._accept_ping_result`, `PingStats`, `TermuxMixin`, `build_scanner_tables`, `run_cleanup_steps`, `TargetPickerScreen`, `export_combined_report`, `save_network_config`, `textual_cameras.py`, `core.py`, `TargetSelection`, `test_android_adaptations.py`, `quick_cleanup`, `is_termux`, `._network_log`, `._render_target_cards`, `Par`, `.compact_vhdx_files`, `._browse_arquivo`, `get_cleanup_steps`, `._compose_cameras`, `os`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `VareduraTextualApp` (e.g. with `test_compact_mode_only_on_narrow_screens()` and `test_capture_screenshot_saves_svg_and_txt()`) actually correct?**
  _`VareduraTextualApp` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `VareduraTextualApp` be split into smaller, more focused modules?**
  _Cohesion score 0.05625 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `on`, `test_textual_app.py`, `CamerasMixin`, `textual_app.py`, `PlansMixin`, `load_network_config`, `test_port_catalog.py`, `run_textual_app`, `.on_main_tab_activated`, `._accept_ping_result`, `TermuxMixin`, `stop_continuous_testing`, `test_textual_cameras.py`, `DailyLogWriter`, `test_textual_cleanup_worker_uses_fake_cleaner`, `test_textual_docker_reward_and_achievement`, `is_termux`, `test_textual_termux.py`, `._network_log`, `._render_target_cards`, `test_layout.py`, `SpeedTestConfig`, `os`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `league_detector.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07431693989071038 - nodes in this community are weakly interconnected._