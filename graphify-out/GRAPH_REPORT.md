# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 104 files · ~131,774 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2741 nodes · 7025 edges · 214 communities (84 shown, 130 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 522 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3a10fffb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- VareduraTextualApp
- league_detector.py
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
- test_netinfo.py
- main
- textual_app.py
- CamerasMixin
- test_network_diagnostics.py
- Event
- ContinuousSpeedTester
- test_camera_bridge.py
- test_network_repairs.py
- credenciais.py
- ._compose_dashboard
- CommandResult
- PlansMixin
- ._accept_ping_result
- set_language
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
- WSLDockerCleaner
- os
- install.ps1
- install.sh
- camera_engine.py
- DataUsageTracker
- termux_env.py
- camera_bridge.py
- pathlib
- handle_key
- current_cycle
- port_scanner.py
- FastComProvider
- mapa.py
- TermuxMixin
- LocationStore
- TargetPickerScreen
- ._worker_camera
- test_textual_cameras.py
- redact_sensitive
- load_prefs
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
- steps
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- is_android
- test_textual_termux.py
- TargetSelection
- json
- monitor/__init__.py
- .from_config
- scanner.py
- test_shutdown_close_resources_terminates_players
- PingProbeResult
- SimetProvider
- textual_app.py
- _ManualFuture
- test
- ._compose_settings
- xiongmai.py
- ._compose_cameras
- os
- varedura
- termux_install.sh
- ci.yml
- run_textual_app
- _require_safe_child
- ._browse_arquivo
- segments_intersect
- merge_visible_selection
- ShutdownScreen
- save_network_config
- on
- PlanProfile
- RepairConfirmationScreen
- PingStats
- _HangingPopen
- Par
- EventSeverity
- get_docker_vhdx_paths
- .start
- check_keyboard
- export_combined_report
- _CompletedPopen
- DiagnosticCancelled

## God Nodes (most connected - your core abstractions)
1. `t()` - 208 edges
2. `VareduraTextualApp` - 177 edges
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
- `test_quit_shows_shutdown_screen_when_busy()` --uses--> `ShutdownScreen`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `test_compact_mode_only_on_narrow_screens()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_layout.py → cli/textual_app.py
- `test_theme_toggle_persists_and_narrow_header_has_no_subtitle()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_layout.py → cli/textual_app.py
- `test_capture_screenshot_saves_svg_and_txt()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py

## Import Cycles
- 2-file cycle: `cli/textual_app.py -> cli/textual_cameras.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_plans.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_termux.py -> cli/textual_app.py`

## Communities (214 total, 130 thin omitted)

### Community 2 - "league_detector.py"
Cohesion: 0.05
Nodes (41): _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, LeagueDetectionResult, LeagueDetectorState, LeagueEndpoint (+33 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.12
Nodes (26): get_language(), PortScannerState, ProcessConnections, _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring(), test_hidden_tabs_are_composed_only_when_opened() (+18 more)

### Community 4 - "time"
Cohesion: 0.06
Nodes (21): test_iou_calculation(), test_line_crossing_rule(), test_motion_heatmap(), test_nms_suppression(), test_point_in_polygon(), test_stream_processor_pipeline(), test_zone_intrusion_rule(), compute_iou() (+13 more)

### Community 5 - "CameraBridge"
Cohesion: 0.13
Nodes (6): _atomic_write_json(), CameraBridge, order(), _iso_now(), _parse_iso(), _read_json()

### Community 6 - "stalker.py"
Cohesion: 0.07
Nodes (12): ContractInfo, _draw_extra_pages(), _draw_text_page(), get_last_export_path(), get_ping_command(), get_top_network_hogs(), _get_top_network_hogs_fallback(), parse_ping() (+4 more)

### Community 7 - "t"
Cohesion: 0.12
Nodes (4): main(), _ps_single_quoted(), _temp_file_path(), t()

### Community 8 - "PingScheduler"
Cohesion: 0.13
Nodes (22): PingScheduler, TargetRole, PingStatus, _Clock, _gateway(), _ManualExecutor, _result(), _selection() (+14 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.08
Nodes (26): _windows_proxy_metadata(), _is_windows_admin(), build_ping_command(), create_custom_target(), _failure_status(), _is_android_env(), parse_ping_latency(), probe_ping() (+18 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.08
Nodes (26): _powershell_encoded_command(), DiagnosisReport, ProbeKind, _system_ssl_context(), _action_id(), _certificate_is_ca(), visit(), _der_tlvs() (+18 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.13
Nodes (15): carregar_lista(), combinar_credenciais(), hosts_da_faixa(), normalizar_faixa(), test_carregar_lista_arquivo_ausente(), test_carregar_lista_ignora_branco_e_comentarios(), test_combinar_credenciais_apenas_uma_lista(), test_combinar_credenciais_produto() (+7 more)

### Community 14 - "test_netinfo.py"
Cohesion: 0.18
Nodes (12): detect_default_gateway(), _detect_unix(), _detect_windows(), _patch_run(), test_detect_default_gateway_dispatches_by_platform(), test_detect_default_gateway_returns_none_on_total_failure(), test_detect_unix_falls_back_through_android_strategies(), test_detect_unix_falls_back_to_netstat() (+4 more)

### Community 15 - "main"
Cohesion: 0.08
Nodes (13): stop_continuous_testing(), analyze_lag_source(), get_export_status(), is_android(), main(), make_connections_panel(), make_header(), make_help_panel() (+5 more)

### Community 16 - "textual_app.py"
Cohesion: 0.10
Nodes (5): _detect_system_language(), init(), _load_preference(), _load_translations(), _load_custom_termux_tools()

### Community 17 - "CamerasMixin"
Cohesion: 0.08
Nodes (3): CamerasMixin, _worker(), remover_regiao()

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.09
Nodes (30): _collect_proxy_configuration(), ProxyConfiguration, _sanitize_pac_url(), _sanitize_proxy_url(), SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner (+22 more)

### Community 19 - "Event"
Cohesion: 0.08
Nodes (12): _bounded_daemon_call(), _collect_linux_dhcp_configuration(), CommandRunner, HttpObservation, _parse_nm_active_uuid(), _parse_nm_ipv4_method(), ProbeBackend, _redact_text() (+4 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.06
Nodes (10): ContinuousSpeedTester, SpeedStats, SpeedTestConfig, test_bandwidth_worker_cancellation_is_observed_promptly(), test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers(), test_prepared_bandwidth_test_honors_cancel_before_worker_starts(), fail_if_provider_runs() (+2 more)

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.21
Nodes (30): command(), make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic(), test_clear_location_is_idempotent_and_keeps_camera_in_catalog() (+22 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.21
Nodes (31): NetworkInterface, NetworkState, RepairExecutor, RepairKind, RepairStatus, _action(), _fake_der_certificate(), FakeRunner (+23 more)

### Community 26 - "credenciais.py"
Cohesion: 0.15
Nodes (12): carregar_conhecidos(), CredencialIP, esquecer_ip(), lembrar_ip(), resolver_ip(), _sucesso(), salvar_conhecidos(), _salvar_json() (+4 more)

### Community 28 - "._compose_dashboard"
Cohesion: 0.12
Nodes (6): _cleanup_checkbox_id(), RichRenderable, build_cleanup_status_panel(), build_scanner_tables(), build_tool_option(), cleanup_label_key()

### Community 29 - "CommandResult"
Cohesion: 0.17
Nodes (9): CommandResult, RepairAction, RepairResult, RepairRunner, run(), run(), run(), run() (+1 more)

### Community 30 - "PlansMixin"
Cohesion: 0.13
Nodes (5): _fmt_number(), PlansMixin, get_usage_tracker(), find_profile(), profiles_to_prefs()

### Community 33 - "server.py"
Cohesion: 0.09
Nodes (11): _confirmation_required(), docker_full_cleanup(), docker_quick_cleanup(), docker_status(), _dry_run_preview(), get_logs(), _is_docker_running(), port_scan() (+3 more)

### Community 34 - "load_network_config"
Cohesion: 0.19
Nodes (12): load_network_config(), _valid_legacy_host(), _verified_stored_app_ca(), _set_prefs(), test_clean_install_requires_target_onboarding(), test_corrupt_numeric_preferences_fall_back_before_first_compose(), test_corrupt_schema_and_invalid_legacy_host_return_to_onboarding(), test_legacy_automatic_default_does_not_start_external_ping() (+4 more)

### Community 35 - "data_usage.py"
Cohesion: 0.26
Nodes (6): _atomic_write(), load_speed_samples(), record_speed_sample(), samples_for_report(), SpeedSample, test_speed_history_roundtrip_filters_by_profile_and_cycle()

### Community 36 - "PingTarget"
Cohesion: 0.12
Nodes (14): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingTarget, TargetCategory, _result(), test_csv_rows_are_contiguous_by_target_generation() (+6 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.08
Nodes (8): FakeProcess, FakeRunner, test_hls_h264_uses_remux_without_audio(), test_snapshot_failure_is_reduced_to_safe_enum(), CaptureResult, FFmpegRunner, HlsProcess, _replace_with_retry()

### Community 40 - "MultiProviderSpeedTester"
Cohesion: 0.09
Nodes (4): get_multi_provider(), MultiProviderSpeedTester, SpeedTestProvider, SpeedTestResult

### Community 41 - "network_diagnostics.py"
Cohesion: 0.07
Nodes (38): classify_diagnosis(), collect_network_snapshot(), Confidence, _default_route_command(), DiagnosticOptions, Evidence, _evidence_for_snapshot(), _failure_probe() (+30 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.12
Nodes (6): NetIPPacket, XiongmaiNetIPClient, _delayed_stop(), test_netip_client_workflow(), test_netip_packet_incomplete_buffer(), test_netip_packet_serialization()

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.12
Nodes (11): BrasilBandaLargaProvider, _chrome_service(), _safe_quit(), _sane_ping(), FakeDriver, test_chrome_service_suppresses_console_window(), test_provider_cleanup_quits_and_clears_driver(), test_safe_quit_calls_quit() (+3 more)

### Community 49 - "test_docker_cleanup.py"
Cohesion: 0.10
Nodes (15): CleanupStepResult, test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers() (+7 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.12
Nodes (13): sort_key(), build_ports_summary(), classify_exposure(), describe_port(), is_exposed(), _load(), test_catalog_keys_translated(), test_classify_exposure() (+5 more)

### Community 51 - "shutil"
Cohesion: 0.09
Nodes (18): _load_camera_backend(), abrir_stream(), _achar_exe(), capturar_e_abrir_snapshot(), comando_mpv_terminal(), detectar_player(), erro_se_morreu(), _ffplay_disponivel() (+10 more)

### Community 52 - "test_plan_profiles.py"
Cohesion: 0.12
Nodes (17): _clean_ssid(), detect_active_network(), _kind_from_interface(), parse_netsh_wlan(), parse_route_get(), _run(), ActiveNetwork, NetworkKind (+9 more)

### Community 53 - "WSLDockerCleaner"
Cohesion: 0.11
Nodes (4): WSLDockerCleaner, _drain_and_wait(), stream_reader(), test_parse_wsl_distros_drops_shell_metacharacters()

### Community 54 - "os"
Cohesion: 0.15
Nodes (12): get_speed_tester(), SpeedTestResult, start_continuous_testing(), _generate_combined_pdf_worker(), _pdf_text(), test_report_uses_active_profile_and_consumer_wording(), cleanup_exports(), test_generate_small_pdf() (+4 more)

### Community 55 - "install.ps1"
Cohesion: 0.27
Nodes (18): Add-ToUserPath(), Get-CmdVersion(), Ask-Action(), Check-Dependencies(), Confirm-Yes(), Detect-OS(), Do-Check(), Do-Install() (+10 more)

### Community 56 - "install.sh"
Cohesion: 0.28
Nodes (20): cmd_exists(), get_version(), is_installed(), main(), refresh_path(), install.sh script, ask_action(), check_dependencies() (+12 more)

### Community 58 - "camera_engine.py"
Cohesion: 0.07
Nodes (9): CameraCapabilities, CameraFleetManager, CameraMetadata, CameraProtocol, UnifiedCameraSource, DiscoveredCamera, SofiaP2PClient, XiongmaiDiscovery (+1 more)

### Community 60 - "termux_env.py"
Cohesion: 0.06
Nodes (37): test_collect_android_telemetry_battery_api_fallback_and_never_raises(), test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_discover_termux_tools_builtins_claro_shortcuts_and_custom(), test_discover_termux_tools_ignores_invalid_custom_json(), test_extra_keys_macros_and_temporary_keyboard_key(), test_native_text_dialog_parses_ok_and_cancel(), test_root_and_claro_suite_detection() (+29 more)

### Community 61 - "camera_bridge.py"
Cohesion: 0.08
Nodes (17): test_inventory_id_survives_password_change_inside_vendor_path(), test_inventory_ids_are_stable_and_private_state_has_no_endpoint(), test_inventory_never_uses_ip_as_default_name(), ActiveSession, BridgeAlreadyRunning, build_parser(), _canonical_rtsp_identity(), _finite_real() (+9 more)

### Community 62 - "pathlib"
Cohesion: 0.09
Nodes (8): Geo, geolocalizar(), obter_logger(), adicionar_regiao(), carregar_regioes(), Regiao, _salvar_json(), salvar_regioes()

### Community 63 - "handle_key"
Cohesion: 0.12
Nodes (13): handle_key(), load_prefs(), prompt_change_contracted_speed(), prompt_change_external(), prompt_change_gateway(), prompt_change_interval(), prompt_change_threshold(), prompt_export_report() (+5 more)

### Community 64 - "current_cycle"
Cohesion: 0.14
Nodes (6): current_cycle(), CycleWindow, quota_status(), QuotaStatus, _quota_lines(), test_cycle_rolls_forward_and_quota_projection()

### Community 66 - "port_scanner.py"
Cohesion: 0.07
Nodes (26): get_listening_ports(), get_process_connections_count(), get_system_network_stats(), PortInfo, _read_proc_meminfo(), _read_proc_net_totals(), run_full_scan(), _safe_net_connections() (+18 more)

### Community 68 - "FastComProvider"
Cohesion: 0.23
Nodes (3): FastComProvider, main(), run_provider()

### Community 69 - "mapa.py"
Cohesion: 0.16
Nodes (9): _widget(), cor_para(), _eh_terra(), _gerar_bitmap(), _interp(), Pino, projetar_celula(), _px_para_latlon() (+1 more)

### Community 71 - "TermuxMixin"
Cohesion: 0.10
Nodes (5): _format_bytes(), TermuxMixin, list_termux_services(), _pgrep_active(), is_cron_update_enabled()

### Community 72 - "LocationStore"
Cohesion: 0.22
Nodes (3): CameraLocation, LocationStore, _valid_uuid()

### Community 75 - "._worker_camera"
Cohesion: 0.22
Nodes (5): monta(), monta(), escanear_portas_camera(), escanear_rede(), testar_porta()

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.40
Nodes (12): open_cameras(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input(), test_cameras_credential_add_and_remove(), test_cameras_import_credential_lists(), test_cameras_open_port_saved_without_credential(), test_cameras_port_scan_populates_table(), test_cameras_rede_action_bar_and_empty_selection() (+4 more)

### Community 77 - "redact_sensitive"
Cohesion: 0.15
Nodes (8): configurar(), _redact_arg(), redact_sensitive(), RedactingFilter, RedactingFormatter, test_redacting_formatter_covers_exception_text(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth(), configure_logging()

### Community 78 - "load_prefs"
Cohesion: 0.15
Nodes (8): load_cleanup_steps(), load_git_last_check(), load_prefs(), save_cleanup_steps(), save_dark_theme_pref(), save_git_autoupdate_pref(), save_git_last_check(), save_prefs()

### Community 80 - "DailyLogWriter"
Cohesion: 0.12
Nodes (3): DailyLogWriter, cleanup_label(), run_cleanup_steps()

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.16
Nodes (5): SpeedtestNetProvider, test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "core.py"
Cohesion: 0.14
Nodes (5): main(), parse_args(), run_cmd(), _strip_powershell_clixml(), test_powershell_clixml_progress_is_removed_from_stderr()

### Community 87 - "SubprocessRepairRunner"
Cohesion: 0.14
Nodes (7): _kill_process(), _powershell_single_quote(), SubprocessRepairRunner, _windows_elevated_script(), test_networkmanager_checkpoint_receives_explicit_restore_answer(), test_windows_helper_script_accepts_only_enumerated_operations(), test_windows_renew_script_rejects_wildcards_and_checks_ipv6_exit()

### Community 89 - "test_android_adaptations.py"
Cohesion: 0.12
Nodes (10): build_dashboard_status(), _fmt_android_battery(), _fmt_data_mb(), _fmt_memory(), _fmt_ping(), _fmt_traffic(), _render(), test_dashboard_hides_docker_and_mcp_rows_without_docker_tab() (+2 more)

### Community 91 - "steps"
Cohesion: 0.36
Nodes (8): steps, continue-on-error, name, run, uses, with, steps, enable-cache

### Community 93 - "is_android"
Cohesion: 0.16
Nodes (4): test_env_detection_flags(), is_android(), is_termux(), should_show_docker_tab()

### Community 94 - "test_textual_termux.py"
Cohesion: 0.22
Nodes (12): isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard(), wait_until() (+4 more)

### Community 95 - "TargetSelection"
Cohesion: 0.31
Nodes (3): TargetSelection, test_selection_enforces_five_persistent_and_primary(), test_selection_round_trip_and_legacy_migration()

### Community 96 - "json"
Cohesion: 0.17
Nodes (12): test_graphify_artifact_excludes_private_runtime_sources(), _field_names(), _load_locale(), test_i18n_all_values_non_empty_strings(), test_i18n_placeholder_parity(), test_i18n_pt_en_key_parity(), _probe_modules(), test_entrypoint_import_is_a_lightweight_dispatcher() (+4 more)

### Community 97 - "monitor/__init__.py"
Cohesion: 0.24
Nodes (4): __getattr__(), StalkerConfig, test_legacy_defaults_never_restore_speculative_external_target(), test_legacy_monitor_returns_without_ping_when_onboarding_is_incomplete()

### Community 99 - "scanner.py"
Cohesion: 0.28
Nodes (3): _build_rtsp_request(), ResultadoRTSP, testar_rtsp()

### Community 102 - "PingProbeResult"
Cohesion: 0.13
Nodes (7): _Flight, SchedulerTargetSnapshot, _TargetState, HostKind, PingProbeResult, PingSample, fake_probe()

### Community 104 - "SimetProvider"
Cohesion: 0.16
Nodes (3): ProgressState, SimetProvider, test_provider_cleanup_without_driver_is_safe()

### Community 105 - "textual_app.py"
Cohesion: 0.09
Nodes (9): columns_for(), layout_tier(), theme_name(), anatel_minimums(), format_duration(), load_dark_theme_pref(), get_supported_languages(), test_layout_tiers_and_columns() (+1 more)

### Community 108 - "test"
Cohesion: 0.29
Nodes (7): test, os, fail-fast, matrix, name, runs-on, strategy

### Community 109 - "._compose_settings"
Cohesion: 0.12
Nodes (9): _add_common_status_rows(), build_cleanup_steps_table(), build_settings_status_table(), cleanup_summary(), get_cleanup_steps(), is_mcp_configured(), load_git_autoupdate_pref(), selected_cleanup_keys() (+1 more)

### Community 111 - "xiongmai.py"
Cohesion: 0.08
Nodes (9): parse_camera_url(), encrypt_xiongmai_digest(), encrypt_xiongmai_password(), NetIPMsgId, PTZCommand, test_parse_camera_url(), test_unified_camera_source_netip(), MockNetIPServer (+1 more)

### Community 116 - "os"
Cohesion: 0.09
Nodes (20): test_cron_toggle_preserves_other_entries(), test_resolve_github_token_precedence_and_no_secret_in_label(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run(), test_save_token_file_rejects_empty_or_multiline(), test_update_repository_states_and_cooldown(), send_termux_notification(), _alt_token_file_path() (+12 more)

### Community 144 - "ci.yml"
Cohesion: 0.22
Nodes (8): concurrency, cancel-in-progress, group, jobs, lint, name, runs-on, name

### Community 181 - "_require_safe_child"
Cohesion: 0.33
Nodes (3): test_runtime_subdirectory_link_is_rejected(), _is_link_like(), _require_safe_child()

### Community 183 - "segments_intersect"
Cohesion: 0.40
Nodes (3): test_geometric_line_intersection(), ccw(), segments_intersect()

### Community 186 - "ShutdownScreen"
Cohesion: 0.12
Nodes (3): ShutdownScreen, TargetPingCard, test_quit_exits_immediately_when_idle()

### Community 187 - "save_network_config"
Cohesion: 0.22
Nodes (4): save_network_config(), _prefs(), isolated_ui_prefs(), isolated_state()

### Community 191 - "on"
Cohesion: 0.16
Nodes (4): on, pull_request, push, branches

### Community 193 - "PlanProfile"
Cohesion: 0.11
Nodes (18): _fmt_speed(), number(), text(), apply_profile(), bind_to_network(), describe_binding(), evaluate_speed(), _iso_date() (+10 more)

### Community 195 - "PingStats"
Cohesion: 0.29
Nodes (3): make_ascii_graph(), make_graph_panel(), PingStats

### Community 197 - "Par"
Cohesion: 0.16
Nodes (5): adicionar_par(), carregar_vault(), Par, remover_par(), salvar_vault()

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 966 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **130 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `t` to `VareduraTextualApp`, `stalker.py`, `main`, `textual_app.py`, `CamerasMixin`, `._compose_dashboard`, `PlansMixin`, `._accept_ping_result`, `PingTarget`, `test_port_catalog.py`, `shutil`, `WSLDockerCleaner`, `._browse_arquivo`, `os`, `ShutdownScreen`, `handle_key`, `PlanProfile`, `RepairConfirmationScreen`, `PingStats`, `Par`, `TermuxMixin`, `TargetPickerScreen`, `._worker_camera`, `load_prefs`, `.docker_cleanup`, `DailyLogWriter`, `export_combined_report`, `core.py`, `TermuxKeysMixin`, `test_android_adaptations.py`, `quick_cleanup`, `is_android`, `.from_config`, `._scan_faixa`, `textual_app.py`, `._compose_settings`, `._compose_cameras`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `VareduraTextualApp` (e.g. with `test_compact_mode_only_on_narrow_screens()` and `test_theme_toggle_persists_and_narrow_header_has_no_subtitle()`) actually correct?**
  _`VareduraTextualApp` has 44 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `VareduraTextualApp` be split into smaller, more focused modules?**
  _Cohesion score 0.06019871420222092 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `test_textual_app.py`, `t`, `ping_targets.py`, `main`, `CamerasMixin`, `ContinuousSpeedTester`, `._compose_dashboard`, `PlansMixin`, `._accept_ping_result`, `PingTarget`, `network_diagnostics.py`, `test_port_catalog.py`, `run_textual_app`, `ShutdownScreen`, `on`, `.on_main_tab_activated`, `TermuxMixin`, `test_textual_cameras.py`, `load_prefs`, `DailyLogWriter`, `test_textual_cleanup_worker_uses_fake_cleaner`, `test_textual_docker_reward_and_achievement`, `TermuxKeysMixin`, `is_android`, `test_textual_termux.py`, `.from_config`, `test_shutdown_close_resources_terminates_players`, `textual_app.py`, `._compose_settings`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `league_detector.py` be split into smaller, more focused modules?**
  _Cohesion score 0.050543637966500146 - nodes in this community are weakly interconnected._