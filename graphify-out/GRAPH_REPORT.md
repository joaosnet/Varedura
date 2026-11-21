# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 103 files · ~129,700 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2697 nodes · 6926 edges · 194 communities (86 shown, 108 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 528 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6dcebf21`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
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
- test_netinfo.py
- main
- network_diagnostics.py
- CamerasMixin
- test_network_diagnostics.py
- Event
- ContinuousSpeedTester
- test_camera_bridge.py
- test_network_repairs.py
- time
- credenciais.py
- get_cleanup_steps
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
- current_cycle
- port_scanner.py
- ._accept_ping_result
- FastComProvider
- mapa.py
- TermuxMixin
- LocationStore
- TargetPickerScreen
- FakeProcess
- test_textual_cameras.py
- redact_sensitive
- save_network_config
- obter_logger
- DailyLogWriter
- test_textual_cleanup_worker_uses_fake_cleaner
- test_textual_docker_reward_and_achievement
- SpeedtestNetProvider
- core.py
- TargetSelection
- test_updater.py
- paths.py
- test_android_adaptations.py
- quick_cleanup
- camera_engine.py
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- is_termux
- test_textual_termux.py
- network_ui.py
- json
- monitor/__init__.py
- ._render_target_cards
- Par
- test_termux_api_helpers
- test_shutdown_close_resources_terminates_players
- WSLDockerCleaner
- SimetProvider
- textual_app.py
- _ManualFuture
- SpeedTestConfig
- build_settings_status_table
- test_xiongmai_p2p.py
- ._compose_cameras
- os
- varedura
- termux_install.sh
- steps
- run_textual_app
- .configure_wsl_sparse
- PlanProfile
- check_keyboard
- get_top_network_hogs

## God Nodes (most connected - your core abstractions)
1. `t()` - 206 edges
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
- `test_compact_mode_only_on_narrow_screens()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_layout.py → cli/textual_app.py
- `test_theme_toggle_persists_and_narrow_header_has_no_subtitle()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_layout.py → cli/textual_app.py
- `test_capture_screenshot_saves_svg_and_txt()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py
- `test_diagnosis_renders_repair_actions_inside_responsive_grid()` --uses--> `VareduraTextualApp`  [INFERRED]
  tests/test_textual_app.py → cli/textual_app.py

## Import Cycles
- 2-file cycle: `cli/textual_app.py -> cli/textual_cameras.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_plans.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_termux.py -> cli/textual_app.py`

## Communities (194 total, 108 thin omitted)

### Community 1 - "VareduraTextualApp"
Cohesion: 0.05
Nodes (3): VareduraTextualApp, PingStats, test_shutdown_stop_monitors_sets_events()

### Community 2 - "league_detector.py"
Cohesion: 0.06
Nodes (37): _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, LeagueDetectionResult, LeagueDetectorState, LeagueEndpoint (+29 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.10
Nodes (26): ShutdownScreen, PortScannerState, _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring(), test_hidden_tabs_are_composed_only_when_opened(), test_network_cards_reflow_for_any_terminal_size() (+18 more)

### Community 4 - "Detection"
Cohesion: 0.08
Nodes (16): test_geometric_line_intersection(), test_iou_calculation(), test_line_crossing_rule(), test_nms_suppression(), test_point_in_polygon(), test_zone_intrusion_rule(), compute_iou(), Detection (+8 more)

### Community 5 - "CameraBridge"
Cohesion: 0.11
Nodes (8): test_runtime_subdirectory_link_is_rejected(), _atomic_write_json(), CameraBridge, order(), _iso_now(), _parse_iso(), _read_json(), _utc_now()

### Community 6 - "stalker.py"
Cohesion: 0.07
Nodes (12): ContractInfo, _draw_extra_pages(), _draw_text_page(), get_last_export_path(), get_ping_command(), make_ascii_graph(), make_graph_panel(), parse_ping() (+4 more)

### Community 7 - "WSLDockerCleaner"
Cohesion: 0.13
Nodes (3): cleanup_label(), run_cleanup_steps(), t()

### Community 8 - "PingScheduler"
Cohesion: 0.10
Nodes (26): PingScheduler, loop(), TargetRole, _TargetState, PingStatus, target_by_id(), _Clock, _gateway() (+18 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.06
Nodes (26): _Flight, SchedulerTargetSnapshot, build_ping_command(), create_custom_target(), _failure_status(), HostKind, _is_android_env(), parse_ping_latency() (+18 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.08
Nodes (28): DiagnosisReport, ProbeKind, _action_id(), _certificate_is_ca(), visit(), _der_tlvs(), _disruptive_block_reason(), _flush_preview() (+20 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.13
Nodes (15): carregar_lista(), combinar_credenciais(), hosts_da_faixa(), normalizar_faixa(), test_carregar_lista_arquivo_ausente(), test_carregar_lista_ignora_branco_e_comentarios(), test_combinar_credenciais_apenas_uma_lista(), test_combinar_credenciais_produto() (+7 more)

### Community 14 - "test_netinfo.py"
Cohesion: 0.18
Nodes (12): detect_default_gateway(), _detect_unix(), _detect_windows(), _patch_run(), test_detect_default_gateway_dispatches_by_platform(), test_detect_default_gateway_returns_none_on_total_failure(), test_detect_unix_falls_back_through_android_strategies(), test_detect_unix_falls_back_to_netstat() (+4 more)

### Community 15 - "main"
Cohesion: 0.07
Nodes (14): stop_continuous_testing(), analyze_lag_source(), get_export_status(), is_android(), main(), _initial_port_scan(), make_connections_panel(), make_header() (+6 more)

### Community 16 - "network_diagnostics.py"
Cohesion: 0.18
Nodes (9): classify_diagnosis(), Evidence, _evidence_for_snapshot(), _failure_probe(), _local_probes(), NetworkSnapshot, ProbeResult, test_total_external_transport_failure_is_offline() (+1 more)

### Community 17 - "CamerasMixin"
Cohesion: 0.07
Nodes (4): CamerasMixin, _worker(), _escolher_arquivo_txt(), copy_to_clipboard()

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.07
Nodes (37): DiagnosticOptions, NetworkDiagnosticEngine, ProxyConfiguration, run_network_diagnosis(), SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner (+29 more)

### Community 19 - "Event"
Cohesion: 0.08
Nodes (12): _bounded_daemon_call(), collect_network_snapshot(), CommandRunner, _http_failure_cause(), HttpObservation, ProbeBackend, _redact_text(), SubprocessCommandRunner (+4 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.09
Nodes (5): ContinuousSpeedTester, SpeedStats, SpeedTestResult, test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers()

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.22
Nodes (30): command(), make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic(), test_clear_location_is_idempotent_and_keeps_camera_in_catalog() (+22 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.19
Nodes (34): Confidence, FailureCause, NetworkInterface, NetworkState, ProbeStatus, RepairExecutor, RepairKind, RepairStatus (+26 more)

### Community 25 - "time"
Cohesion: 0.07
Nodes (9): test_motion_heatmap(), test_stream_processor_pipeline(), ObjectDetector, YOLONanoDetector, ccw(), MotionHeatmap, SpatialEvent, AIStreamProcessor (+1 more)

### Community 26 - "credenciais.py"
Cohesion: 0.10
Nodes (13): _load_camera_backend(), adicionar_par(), carregar_conhecidos(), carregar_vault(), CredencialIP, esquecer_ip(), lembrar_ip(), remover_par() (+5 more)

### Community 28 - "get_cleanup_steps"
Cohesion: 0.12
Nodes (8): _cleanup_checkbox_id(), RichRenderable, build_cleanup_status_panel(), cleanup_label_key(), cleanup_summary(), get_cleanup_steps(), load_cleanup_steps(), selected_cleanup_keys()

### Community 29 - "CommandResult"
Cohesion: 0.13
Nodes (8): CommandResult, _kill_process(), RepairAction, RepairResult, SubprocessRepairRunner, test_networkmanager_checkpoint_receives_explicit_restore_answer(), run(), test_windows_helper_script_accepts_only_enumerated_operations()

### Community 30 - "PlansMixin"
Cohesion: 0.14
Nodes (4): _fmt_number(), _fmt_speed(), PlansMixin, find_profile()

### Community 31 - "scanner.py"
Cohesion: 0.11
Nodes (9): _base24(), detectar_redes(), _eh_privado_utilizavel(), _ip_primario(), _ips_hostname(), RedeLocal, _build_rtsp_request(), ResultadoRTSP (+1 more)

### Community 32 - "i18n/__init__.py"
Cohesion: 0.10
Nodes (7): _format_bytes(), _detect_system_language(), init(), _load_preference(), _load_translations(), save_preference(), set_language()

### Community 33 - "server.py"
Cohesion: 0.09
Nodes (11): _confirmation_required(), docker_full_cleanup(), docker_quick_cleanup(), docker_status(), _dry_run_preview(), get_logs(), _is_docker_running(), port_scan() (+3 more)

### Community 34 - "load_network_config"
Cohesion: 0.19
Nodes (13): load_network_config(), _valid_legacy_host(), _verified_stored_app_ca(), legacy_fixed_profile(), _set_prefs(), test_clean_install_requires_target_onboarding(), test_corrupt_numeric_preferences_fall_back_before_first_compose(), test_corrupt_schema_and_invalid_legacy_host_return_to_onboarding() (+5 more)

### Community 35 - "data_usage.py"
Cohesion: 0.17
Nodes (9): _atomic_write(), get_usage_tracker(), load_speed_samples(), record_speed_sample(), samples_for_report(), SpeedSample, _pdf_text(), test_report_uses_active_profile_and_consumer_wording() (+1 more)

### Community 36 - "PingTarget"
Cohesion: 0.09
Nodes (15): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingProbeResult, PingTarget, TargetCategory, _result() (+7 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.13
Nodes (5): test_snapshot_failure_is_reduced_to_safe_enum(), test_snapshot_is_published_atomically_with_subprocess_mock(), FFmpegRunner, HlsProcess, _replace_with_retry()

### Community 40 - "MultiProviderSpeedTester"
Cohesion: 0.09
Nodes (4): get_multi_provider(), MultiProviderSpeedTester, SpeedTestProvider, SpeedTestResult

### Community 41 - "network_diagnostics.py"
Cohesion: 0.09
Nodes (26): _collect_linux_dhcp_configuration(), _collect_proxy_configuration(), _default_route_command(), DiagnosticCancelled, _interface_addresses(), _parse_macos_dhcp_configuration(), _parse_macos_network_services(), _parse_nm_active_uuid() (+18 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.12
Nodes (6): NetIPPacket, XiongmaiNetIPClient, _delayed_stop(), test_netip_client_workflow(), test_netip_packet_incomplete_buffer(), test_netip_packet_serialization()

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.15
Nodes (8): BrasilBandaLargaProvider, _safe_quit(), FakeDriver, test_provider_cleanup_quits_and_clears_driver(), test_provider_cleanup_without_driver_is_safe(), test_safe_quit_calls_quit(), test_safe_quit_fallback_kills_process(), test_safe_quit_handles_none()

### Community 49 - "test_docker_cleanup.py"
Cohesion: 0.10
Nodes (15): CleanupStepResult, test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers() (+7 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.12
Nodes (13): sort_key(), build_ports_summary(), classify_exposure(), describe_port(), is_exposed(), _load(), test_catalog_keys_translated(), test_classify_exposure() (+5 more)

### Community 51 - "shutil"
Cohesion: 0.10
Nodes (15): abrir_stream(), _achar_exe(), capturar_e_abrir_snapshot(), comando_mpv_terminal(), detectar_player(), erro_se_morreu(), _ffplay_disponivel(), _ffprobe_disponivel() (+7 more)

### Community 52 - "test_plan_profiles.py"
Cohesion: 0.11
Nodes (19): _clean_ssid(), detect_active_network(), _kind_from_interface(), parse_netsh_wlan(), parse_route_get(), _run(), _is_windows_admin(), ActiveNetwork (+11 more)

### Community 53 - ".run_command_async"
Cohesion: 0.17
Nodes (4): _strip_powershell_clixml(), _drain_and_wait(), stream_reader(), test_powershell_clixml_progress_is_removed_from_stderr()

### Community 54 - "os"
Cohesion: 0.17
Nodes (12): get_speed_tester(), start_continuous_testing(), export_combined_report(), _generate_combined_pdf_worker(), prompt_export_report(), snapshot_ping_history(), cleanup_exports(), test_generate_small_pdf() (+4 more)

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
Cohesion: 0.09
Nodes (26): test_collect_android_telemetry_battery_api_fallback_and_never_raises(), test_discover_termux_tools_builtins_claro_shortcuts_and_custom(), test_discover_termux_tools_ignores_invalid_custom_json(), test_root_and_claro_suite_detection(), test_termux_services_list_and_toggle(), AndroidTelemetry, collect_android_telemetry(), _collect_battery() (+18 more)

### Community 61 - "camera_bridge.py"
Cohesion: 0.08
Nodes (18): test_inventory_id_survives_password_change_inside_vendor_path(), test_inventory_ids_are_stable_and_private_state_has_no_endpoint(), test_inventory_never_uses_ip_as_default_name(), ActiveSession, BridgeAlreadyRunning, build_parser(), _canonical_rtsp_identity(), _finite_real() (+10 more)

### Community 62 - "regioes.py"
Cohesion: 0.15
Nodes (6): adicionar_regiao(), carregar_regioes(), Regiao, remover_regiao(), _salvar_json(), salvar_regioes()

### Community 63 - "handle_key"
Cohesion: 0.14
Nodes (11): handle_key(), load_prefs(), prompt_change_contracted_speed(), prompt_change_gateway(), prompt_change_interval(), prompt_change_threshold(), save_prefs(), set_allow_full_history_export() (+3 more)

### Community 64 - "current_cycle"
Cohesion: 0.14
Nodes (6): current_cycle(), CycleWindow, quota_status(), QuotaStatus, _quota_lines(), test_cycle_rolls_forward_and_quota_projection()

### Community 66 - "port_scanner.py"
Cohesion: 0.11
Nodes (20): get_listening_ports(), get_process_connections_count(), get_system_network_stats(), PortInfo, ProcessConnections, _read_proc_meminfo(), _read_proc_net_totals(), run_full_scan() (+12 more)

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
Cohesion: 0.12
Nodes (3): TermuxMixin, list_termux_services(), is_cron_update_enabled()

### Community 72 - "LocationStore"
Cohesion: 0.22
Nodes (3): CameraLocation, LocationStore, _valid_uuid()

### Community 74 - "TargetPickerScreen"
Cohesion: 0.11
Nodes (6): RepairConfirmationScreen, TargetPickerScreen, on, pull_request, push, branches

### Community 75 - "FakeProcess"
Cohesion: 0.18
Nodes (3): FakeProcess, FakeRunner, CaptureResult

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.29
Nodes (13): isolated_state(), open_cameras(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input(), test_cameras_credential_add_and_remove(), test_cameras_import_credential_lists(), test_cameras_open_port_saved_without_credential(), test_cameras_port_scan_populates_table() (+5 more)

### Community 77 - "redact_sensitive"
Cohesion: 0.14
Nodes (8): configurar(), _redact_arg(), redact_sensitive(), RedactingFilter, RedactingFormatter, test_redacting_formatter_covers_exception_text(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth(), configure_logging()

### Community 78 - "save_network_config"
Cohesion: 0.10
Nodes (11): load_git_last_check(), load_prefs(), save_cleanup_steps(), save_dark_theme_pref(), save_git_autoupdate_pref(), save_git_last_check(), save_network_config(), save_prefs() (+3 more)

### Community 79 - "obter_logger"
Cohesion: 0.24
Nodes (3): Geo, geolocalizar(), obter_logger()

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.16
Nodes (5): SpeedtestNetProvider, test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "core.py"
Cohesion: 0.11
Nodes (8): run_cmd(), get_docker_vhdx_paths(), _powershell_encoded_command(), buscar_prefixos_por_asn(), obter_amostra_aleatoria(), obter_blocos_rede(), obter_espaco_amostral_completo(), test_get_docker_vhdx_paths_discovers_disk_layout()

### Community 86 - "TargetSelection"
Cohesion: 0.29
Nodes (3): TargetSelection, test_selection_enforces_five_persistent_and_primary(), test_selection_round_trip_and_legacy_migration()

### Community 87 - "test_updater.py"
Cohesion: 0.15
Nodes (6): test_cli_status_and_check_json(), test_cron_toggle_preserves_other_entries(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run(), test_save_token_file_rejects_empty_or_multiline(), test_update_repository_states_and_cooldown()

### Community 89 - "test_android_adaptations.py"
Cohesion: 0.09
Nodes (11): build_dashboard_status(), _fmt_android_battery(), _fmt_data_mb(), _fmt_memory(), _fmt_ping(), _fmt_traffic(), _render(), test_dashboard_hides_docker_and_mcp_rows_without_docker_tab() (+3 more)

### Community 91 - "camera_engine.py"
Cohesion: 0.10
Nodes (8): CameraCapabilities, CameraFleetManager, CameraProtocol, parse_camera_url(), DiscoveredCamera, XiongmaiDiscovery, test_camera_fleet_manager(), test_parse_camera_url()

### Community 93 - "is_termux"
Cohesion: 0.07
Nodes (7): TargetPingCard, get_language(), test_env_detection_flags(), has_docker(), is_android(), is_termux(), should_show_docker_tab()

### Community 94 - "test_textual_termux.py"
Cohesion: 0.20
Nodes (11): isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard(), wait_until() (+3 more)

### Community 95 - "network_ui.py"
Cohesion: 0.22
Nodes (4): merge_visible_selection(), target_catalog(), test_filtered_target_changes_preserve_hidden_selections(), test_catalog_has_stable_ids_and_unique_entries()

### Community 96 - "json"
Cohesion: 0.18
Nodes (12): test_graphify_artifact_excludes_private_runtime_sources(), _field_names(), _load_locale(), test_i18n_all_values_non_empty_strings(), test_i18n_placeholder_parity(), test_i18n_pt_en_key_parity(), _probe_modules(), test_entrypoint_import_is_a_lightweight_dispatcher() (+4 more)

### Community 97 - "monitor/__init__.py"
Cohesion: 0.33
Nodes (3): __getattr__(), StalkerConfig, test_legacy_defaults_never_restore_speculative_external_target()

### Community 99 - "Par"
Cohesion: 0.15
Nodes (8): monta(), monta(), Par, resolver_ip(), escanear_portas_camera(), escanear_rede(), testar_porta(), descobrir_stream()

### Community 100 - "test_termux_api_helpers"
Cohesion: 0.29
Nodes (4): test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_termux_api_helpers(), toggle_keyboard_page()

### Community 102 - "WSLDockerCleaner"
Cohesion: 0.11
Nodes (4): _ps_single_quoted(), _temp_file_path(), WSLDockerCleaner, test_parse_wsl_distros_drops_shell_metacharacters()

### Community 104 - "SimetProvider"
Cohesion: 0.14
Nodes (4): _chrome_service(), ProgressState, SimetProvider, test_chrome_service_suppresses_console_window()

### Community 105 - "textual_app.py"
Cohesion: 0.09
Nodes (9): columns_for(), layout_tier(), theme_name(), format_duration(), load_dark_theme_pref(), get_supported_languages(), test_compact_mode_only_on_narrow_screens(), test_layout_tiers_and_columns() (+1 more)

### Community 108 - "SpeedTestConfig"
Cohesion: 0.14
Nodes (6): SpeedTestConfig, test_bandwidth_worker_cancellation_is_observed_promptly(), test_prepared_bandwidth_test_honors_cancel_before_worker_starts(), fail_if_provider_runs(), test_rich_speed_key_can_cancel_before_its_thread_starts(), test_speed_worker_is_prepared_before_schedule_and_can_cancel_immediately()

### Community 109 - "build_settings_status_table"
Cohesion: 0.12
Nodes (8): _add_common_status_rows(), build_cleanup_steps_table(), build_scanner_tables(), build_settings_status_table(), build_tool_option(), is_mcp_configured(), load_git_autoupdate_pref(), toggle_mcp_config()

### Community 111 - "test_xiongmai_p2p.py"
Cohesion: 0.18
Nodes (5): encrypt_xiongmai_digest(), encrypt_xiongmai_password(), NetIPMsgId, PTZCommand, test_xiongmai_password_encryption()

### Community 116 - "os"
Cohesion: 0.14
Nodes (17): test_resolve_github_token_precedence_and_no_secret_in_label(), send_termux_notification(), _alt_token_file_path(), _default_repo_dir(), get_repo_status(), main(), _prefs_file_path(), _read_crontab() (+9 more)

### Community 144 - "steps"
Cohesion: 0.10
Nodes (23): concurrency, cancel-in-progress, group, jobs, lint, test, name, runs-on (+15 more)

### Community 183 - ".configure_wsl_sparse"
Cohesion: 0.19
Nodes (3): main(), parse_args(), main()

### Community 193 - "PlanProfile"
Cohesion: 0.11
Nodes (16): number(), text(), apply_profile(), describe_binding(), evaluate_speed(), _iso_date(), new_profile_id(), _number() (+8 more)

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 950 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **108 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `WSLDockerCleaner` to `VareduraTextualApp`, `stalker.py`, `main`, `CamerasMixin`, `credenciais.py`, `get_cleanup_steps`, `PlansMixin`, `i18n/__init__.py`, `load_network_config`, `PingTarget`, `test_port_catalog.py`, `shutil`, `.run_command_async`, `os`, `.configure_wsl_sparse`, `regioes.py`, `handle_key`, `PlanProfile`, `._accept_ping_result`, `TermuxMixin`, `TargetPickerScreen`, `save_network_config`, `core.py`, `test_android_adaptations.py`, `quick_cleanup`, `is_termux`, `network_ui.py`, `._render_target_cards`, `Par`, `WSLDockerCleaner`, `textual_app.py`, `build_settings_status_table`, `._compose_cameras`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `VareduraTextualApp` (e.g. with `test_compact_mode_only_on_narrow_screens()` and `test_theme_toggle_persists_and_narrow_header_has_no_subtitle()`) actually correct?**
  _`VareduraTextualApp` has 44 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `VareduraTextualApp` be split into smaller, more focused modules?**
  _Cohesion score 0.046620046620046623 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `test_textual_app.py`, `WSLDockerCleaner`, `main`, `CamerasMixin`, `get_cleanup_steps`, `PlansMixin`, `PingTarget`, `test_port_catalog.py`, `run_textual_app`, `._accept_ping_result`, `TermuxMixin`, `TargetPickerScreen`, `test_textual_cameras.py`, `save_network_config`, `DailyLogWriter`, `test_textual_cleanup_worker_uses_fake_cleaner`, `test_textual_docker_reward_and_achievement`, `is_termux`, `test_textual_termux.py`, `._render_target_cards`, `test_shutdown_close_resources_terminates_players`, `textual_app.py`, `SpeedTestConfig`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `league_detector.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06430745814307458 - nodes in this community are weakly interconnected._