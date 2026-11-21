# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 93 files · ~119,915 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2481 nodes · 6323 edges · 180 communities (77 shown, 103 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 509 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1d5a59bb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- t
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
- run_textual_app
- time
- network_diagnostics.py
- CamerasMixin
- test_network_diagnostics.py
- Event
- ContinuousSpeedTester
- test_camera_bridge.py
- test_network_repairs.py
- AIStreamProcessor
- _load_camera_backend
- load_network_config
- CommandResult
- network_ui.py
- _load_camera_backend
- i18n/__init__.py
- server.py
- redact_sensitive
- ._render_ports_table
- PingTarget
- FFmpegRunner
- speed_providers.py
- network_diagnostics.py
- NetIPPacket
- test_speed_cleanup.py
- test_docker_cleanup.py
- test_port_catalog.py
- shutil
- platform
- .compact_vhdx_files
- speed_tester.py
- install.ps1
- install.sh
- UnifiedCameraSource
- xiongmai.py
- termux_env.py
- camera_bridge.py
- json
- handle_key
- Par
- port_scanner.py
- NetIPPacket
- FastComProvider
- mapa.py
- TermuxMixin
- main
- TargetPickerScreen
- .run_command_async
- test_textual_cameras.py
- camera_engine.py
- FakeProcess
- CameraFleetManager
- DailyLogWriter
- load_private_inventory
- test_ai_vision.py
- SpeedtestNetProvider
- quick_cleanup.py
- TargetSelection
- PingProbeResult
- ._compose_cameras
- is_termux
- quick_cleanup
- MotionHeatmap
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- is_termux
- test_textual_termux.py
- Par
- json
- monitor/__init__.py
- PingStats
- test_termux_env.py
- ._refresh_live_settings_status
- _HangingPopen
- paths.py
- ._browse_arquivo
- SimetProvider
- EventSeverity
- _ManualFuture
- .start
- _require_safe_child
- _CompletedPopen
- RepairConfirmationScreen
- stop_continuous_testing
- os
- varedura
- termux_install.sh

## God Nodes (most connected - your core abstractions)
1. `t()` - 191 edges
2. `VareduraTextualApp` - 175 edges
3. `WSLDockerCleaner` - 71 edges
4. `CamerasMixin` - 69 edges
5. `CameraBridge` - 52 edges
6. `PingTarget` - 47 edges
7. `_load_camera_backend()` - 38 edges
8. `PingScheduler` - 37 edges
9. `CommandResult` - 34 edges
10. `CameraSource` - 33 edges

## Surprising Connections (you probably didn't know these)
- `VareduraTextualApp` --uses--> `DiagnosticOptions`  [INFERRED]
  cli/textual_app.py → monitor/network_diagnostics.py
- `VareduraTextualApp` --uses--> `NetworkState`  [INFERRED]
  cli/textual_app.py → monitor/network_diagnostics.py
- `VareduraTextualApp` --uses--> `ProbeKind`  [INFERRED]
  cli/textual_app.py → monitor/network_diagnostics.py
- `VareduraTextualApp` --uses--> `NetworkSessionHistory`  [INFERRED]
  cli/textual_app.py → monitor/network_history.py
- `VareduraTextualApp` --uses--> `PingStats`  [INFERRED]
  cli/textual_app.py → monitor/stalker.py

## Import Cycles
- 2-file cycle: `cli/textual_app.py -> cli/textual_cameras.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_termux.py -> cli/textual_app.py`

## Communities (180 total, 103 thin omitted)

### Community 0 - "t"
Cohesion: 0.05
Nodes (27): RichRenderable, _add_common_status_rows(), anatel_minimums(), build_cleanup_status_panel(), build_cleanup_steps_table(), build_dashboard_status(), build_ports_summary(), build_scanner_tables() (+19 more)

### Community 1 - "VareduraTextualApp"
Cohesion: 0.04
Nodes (10): VareduraTextualApp, save_cleanup_steps(), t(), get_export_status(), test_additional_targets_do_not_update_primary_health_sparkline(), test_callback_from_previous_network_run_is_discarded(), test_late_league_callback_cannot_reenable_disabled_detector(), test_shutdown_close_resources_terminates_players() (+2 more)

### Community 2 - "league_detector.py"
Cohesion: 0.06
Nodes (37): _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, LeagueDetectionResult, LeagueDetectorState, LeagueEndpoint (+29 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.06
Nodes (29): ShutdownScreen, PortInfo, PortScannerState, ProcessConnections, _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring() (+21 more)

### Community 4 - "Detection"
Cohesion: 0.13
Nodes (5): test_line_crossing_rule(), Detection, GeometricRule, LineCrossingRule, LoiteringRule

### Community 5 - "CameraBridge"
Cohesion: 0.13
Nodes (5): _atomic_write_json(), CameraBridge, _iso_now(), _read_json(), _replace_with_retry()

### Community 6 - "stalker.py"
Cohesion: 0.08
Nodes (10): check_keyboard(), ContractInfo, _flush_stdin(), get_ping_command(), get_top_network_hogs(), _get_top_network_hogs_fallback(), parse_ping(), record_ping_sample() (+2 more)

### Community 7 - "WSLDockerCleaner"
Cohesion: 0.10
Nodes (5): main(), parse_args(), main(), WSLDockerCleaner, test_parse_wsl_distros_drops_shell_metacharacters()

### Community 8 - "PingScheduler"
Cohesion: 0.12
Nodes (24): PingScheduler, TargetRole, _TargetState, PingStatus, _Clock, _gateway(), _league(), _ManualExecutor (+16 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.10
Nodes (20): build_ping_command(), create_custom_target(), _failure_status(), parse_ping_latency(), probe_ping(), target_by_id(), target_catalog(), _terminate_process() (+12 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.07
Nodes (29): DiagnosisReport, ProbeKind, _system_ssl_context(), _action_id(), _certificate_is_ca(), visit(), _der_tlvs(), _disruptive_block_reason() (+21 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.13
Nodes (15): carregar_lista(), combinar_credenciais(), hosts_da_faixa(), normalizar_faixa(), test_carregar_lista_arquivo_ausente(), test_carregar_lista_ignora_branco_e_comentarios(), test_combinar_credenciais_apenas_uma_lista(), test_combinar_credenciais_produto() (+7 more)

### Community 16 - "network_diagnostics.py"
Cohesion: 0.12
Nodes (12): classify_diagnosis(), collect_network_snapshot(), DiagnosticOptions, Evidence, _evidence_for_snapshot(), _failure_probe(), _local_probes(), NetworkSnapshot (+4 more)

### Community 17 - "CamerasMixin"
Cohesion: 0.07
Nodes (4): CamerasMixin, _worker(), remover_regiao(), comando_mpv_terminal()

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.10
Nodes (27): NetworkDiagnosticEngine, ProxyConfiguration, SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner, _interface(), _snapshot() (+19 more)

### Community 19 - "Event"
Cohesion: 0.09
Nodes (10): _bounded_daemon_call(), CommandRunner, _http_failure_cause(), HttpObservation, ProbeBackend, _redact_text(), SubprocessCommandRunner, SystemProbeBackend (+2 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.06
Nodes (10): ContinuousSpeedTester, SpeedStats, SpeedTestConfig, test_bandwidth_worker_cancellation_is_observed_promptly(), test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers(), test_prepared_bandwidth_test_honors_cancel_before_worker_starts(), fail_if_provider_runs() (+2 more)

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.22
Nodes (30): command(), make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic(), test_clear_location_is_idempotent_and_keeps_camera_in_catalog() (+22 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.19
Nodes (33): Confidence, FailureCause, NetworkInterface, NetworkState, ProbeStatus, RepairExecutor, RepairKind, RepairStatus (+25 more)

### Community 25 - "AIStreamProcessor"
Cohesion: 0.16
Nodes (4): test_stream_processor_pipeline(), SpatialEvent, AIStreamProcessor, VideoFrame

### Community 26 - "_load_camera_backend"
Cohesion: 0.15
Nodes (9): carregar_conhecidos(), carregar_vault(), CredencialIP, esquecer_ip(), lembrar_ip(), _sucesso(), salvar_conhecidos(), _salvar_json() (+1 more)

### Community 28 - "load_network_config"
Cohesion: 0.08
Nodes (19): load_git_last_check(), load_network_config(), load_prefs(), save_git_autoupdate_pref(), save_git_last_check(), save_network_config(), save_prefs(), _verified_stored_app_ca() (+11 more)

### Community 29 - "CommandResult"
Cohesion: 0.10
Nodes (12): CommandResult, RepairAction, RepairResult, RepairRunner, SubprocessRepairRunner, run(), run(), run() (+4 more)

### Community 31 - "_load_camera_backend"
Cohesion: 0.15
Nodes (7): _load_camera_backend(), _build_rtsp_request(), escanear_portas_camera(), escanear_rede(), ResultadoRTSP, testar_porta(), testar_rtsp()

### Community 32 - "i18n/__init__.py"
Cohesion: 0.18
Nodes (6): _detect_system_language(), init(), _load_preference(), _load_translations(), save_preference(), set_language()

### Community 33 - "server.py"
Cohesion: 0.09
Nodes (11): _confirmation_required(), docker_full_cleanup(), docker_quick_cleanup(), docker_status(), _dry_run_preview(), get_logs(), _is_docker_running(), port_scan() (+3 more)

### Community 34 - "redact_sensitive"
Cohesion: 0.15
Nodes (8): configurar(), _redact_arg(), redact_sensitive(), RedactingFilter, RedactingFormatter, test_redacting_formatter_covers_exception_text(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth(), configure_logging()

### Community 36 - "PingTarget"
Cohesion: 0.16
Nodes (13): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingTarget, TargetCategory, _result(), test_csv_rows_are_contiguous_by_target_generation() (+5 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.14
Nodes (4): test_hls_h264_uses_remux_without_audio(), test_snapshot_failure_is_reduced_to_safe_enum(), FFmpegRunner, HlsProcess

### Community 40 - "speed_providers.py"
Cohesion: 0.08
Nodes (5): get_multi_provider(), MultiProviderSpeedTester, ProgressState, SpeedTestProvider, SpeedTestResult

### Community 41 - "network_diagnostics.py"
Cohesion: 0.08
Nodes (32): _valid_legacy_host(), _collect_linux_dhcp_configuration(), _collect_proxy_configuration(), _default_route_command(), DiagnosticCancelled, _interface_addresses(), _parse_macos_dhcp_configuration(), _parse_macos_network_services() (+24 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.18
Nodes (3): XiongmaiNetIPClient, _delayed_stop(), test_netip_client_workflow()

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.14
Nodes (9): BrasilBandaLargaProvider, _chrome_service(), _safe_quit(), FakeDriver, test_chrome_service_suppresses_console_window(), test_provider_cleanup_quits_and_clears_driver(), test_safe_quit_calls_quit(), test_safe_quit_fallback_kills_process() (+1 more)

### Community 49 - "test_docker_cleanup.py"
Cohesion: 0.10
Nodes (15): CleanupStepResult, test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers() (+7 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.15
Nodes (10): classify_exposure(), describe_port(), _load(), test_catalog_keys_translated(), test_classify_exposure(), test_describe_port_ephemeral(), test_describe_port_known(), test_describe_port_unknown_low() (+2 more)

### Community 51 - "shutil"
Cohesion: 0.11
Nodes (13): abrir_stream(), _achar_exe(), capturar_e_abrir_snapshot(), detectar_player(), erro_se_morreu(), _ffplay_disponivel(), _ffprobe_disponivel(), _montar_comando() (+5 more)

### Community 52 - "platform"
Cohesion: 0.15
Nodes (14): detect_default_gateway(), _detect_unix(), _detect_windows(), _run(), _is_windows_admin(), _patch_run(), test_detect_default_gateway_dispatches_by_platform(), test_detect_default_gateway_returns_none_on_total_failure() (+6 more)

### Community 54 - "speed_tester.py"
Cohesion: 0.18
Nodes (11): get_speed_tester(), SpeedTestResult, start_continuous_testing(), export_combined_report(), _generate_combined_pdf_worker(), cleanup_exports(), test_generate_small_pdf(), test_large_history_downsampling_and_full_flag() (+3 more)

### Community 55 - "install.ps1"
Cohesion: 0.27
Nodes (18): Add-ToUserPath(), Get-CmdVersion(), Ask-Action(), Check-Dependencies(), Confirm-Yes(), Detect-OS(), Do-Check(), Do-Install() (+10 more)

### Community 56 - "install.sh"
Cohesion: 0.28
Nodes (20): cmd_exists(), get_version(), is_installed(), main(), refresh_path(), install.sh script, ask_action(), check_dependencies() (+12 more)

### Community 58 - "UnifiedCameraSource"
Cohesion: 0.10
Nodes (5): CameraMetadata, UnifiedCameraSource, SofiaP2PClient, test_unified_camera_source_netip(), MockNetIPServer

### Community 59 - "xiongmai.py"
Cohesion: 0.18
Nodes (5): encrypt_xiongmai_digest(), encrypt_xiongmai_password(), NetIPMsgId, PTZCommand, test_xiongmai_password_encryption()

### Community 60 - "termux_env.py"
Cohesion: 0.10
Nodes (23): test_discover_termux_tools_builtins_claro_shortcuts_and_custom(), test_discover_termux_tools_ignores_invalid_custom_json(), test_root_and_claro_suite_detection(), test_termux_services_list_and_toggle(), AndroidTelemetry, collect_android_telemetry(), _collect_battery(), _collect_ips() (+15 more)

### Community 61 - "camera_bridge.py"
Cohesion: 0.09
Nodes (12): ActiveSession, BridgeAlreadyRunning, build_parser(), order(), CameraLocation, _finite_real(), LocationStore, main() (+4 more)

### Community 62 - "json"
Cohesion: 0.07
Nodes (9): _format_bytes(), Geo, geolocalizar(), obter_logger(), adicionar_regiao(), carregar_regioes(), Regiao, _salvar_json() (+1 more)

### Community 63 - "handle_key"
Cohesion: 0.14
Nodes (12): handle_key(), load_prefs(), prompt_change_contracted_speed(), prompt_change_gateway(), prompt_change_interval(), prompt_change_threshold(), prompt_export_report(), save_prefs() (+4 more)

### Community 64 - "Par"
Cohesion: 0.23
Nodes (6): monta(), monta(), resolver_ip(), descobrir_stream(), InfoStream, validar_stream()

### Community 66 - "port_scanner.py"
Cohesion: 0.08
Nodes (24): get_listening_ports(), get_process_connections_count(), get_system_network_stats(), _read_proc_meminfo(), _read_proc_net_totals(), run_full_scan(), _safe_net_connections(), search_port() (+16 more)

### Community 67 - "NetIPPacket"
Cohesion: 0.17
Nodes (4): DiscoveredCamera, NetIPPacket, test_netip_packet_incomplete_buffer(), test_netip_packet_serialization()

### Community 68 - "FastComProvider"
Cohesion: 0.23
Nodes (3): FastComProvider, main(), run_provider()

### Community 69 - "mapa.py"
Cohesion: 0.16
Nodes (9): _widget(), cor_para(), _eh_terra(), _gerar_bitmap(), _interp(), Pino, projetar_celula(), _px_para_latlon() (+1 more)

### Community 71 - "TermuxMixin"
Cohesion: 0.09
Nodes (8): TermuxMixin, test_cron_toggle_preserves_other_entries(), copy_to_clipboard(), list_termux_services(), _pgrep_active(), is_cron_update_enabled(), _read_crontab(), set_cron_update_enabled()

### Community 72 - "main"
Cohesion: 0.09
Nodes (12): analyze_lag_source(), is_android(), main(), _initial_port_scan(), make_connections_panel(), make_header(), make_help_panel(), make_log_panel() (+4 more)

### Community 74 - "TargetPickerScreen"
Cohesion: 0.06
Nodes (28): TargetPickerScreen, concurrency, cancel-in-progress, group, jobs, lint, test, name (+20 more)

### Community 75 - ".run_command_async"
Cohesion: 0.14
Nodes (4): _strip_powershell_clixml(), _drain_and_wait(), stream_reader(), test_powershell_clixml_progress_is_removed_from_stderr()

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.25
Nodes (13): isolated_state(), open_cameras(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input(), test_cameras_credential_add_and_remove(), test_cameras_import_credential_lists(), test_cameras_open_port_saved_without_credential(), test_cameras_port_scan_populates_table() (+5 more)

### Community 77 - "camera_engine.py"
Cohesion: 0.19
Nodes (4): CameraCapabilities, CameraProtocol, parse_camera_url(), test_parse_camera_url()

### Community 78 - "FakeProcess"
Cohesion: 0.18
Nodes (3): FakeProcess, FakeRunner, CaptureResult

### Community 79 - "CameraFleetManager"
Cohesion: 0.25
Nodes (3): CameraFleetManager, XiongmaiDiscovery, test_camera_fleet_manager()

### Community 80 - "DailyLogWriter"
Cohesion: 0.10
Nodes (3): DailyLogWriter, cleanup_label(), run_cleanup_steps()

### Community 81 - "load_private_inventory"
Cohesion: 0.13
Nodes (8): test_inventory_id_survives_password_change_inside_vendor_path(), test_inventory_ids_are_stable_and_private_state_has_no_endpoint(), test_inventory_never_uses_ip_as_default_name(), _canonical_rtsp_identity(), IdentityStore, load_private_inventory(), _safe_display_name(), _with_credentials()

### Community 83 - "test_ai_vision.py"
Cohesion: 0.17
Nodes (9): test_geometric_line_intersection(), test_iou_calculation(), test_nms_suppression(), test_point_in_polygon(), compute_iou(), nms(), ccw(), point_in_polygon() (+1 more)

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.16
Nodes (5): SpeedtestNetProvider, test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "quick_cleanup.py"
Cohesion: 0.10
Nodes (8): run_cmd(), get_docker_vhdx_paths(), _powershell_encoded_command(), buscar_prefixos_por_asn(), obter_amostra_aleatoria(), obter_blocos_rede(), obter_espaco_amostral_completo(), test_get_docker_vhdx_paths_discovers_disk_layout()

### Community 86 - "TargetSelection"
Cohesion: 0.29
Nodes (3): TargetSelection, test_selection_enforces_five_persistent_and_primary(), test_selection_round_trip_and_legacy_migration()

### Community 87 - "PingProbeResult"
Cohesion: 0.12
Nodes (6): _Flight, SchedulerTargetSnapshot, HostKind, PingProbeResult, PingSample, fake_probe()

### Community 89 - "is_termux"
Cohesion: 0.16
Nodes (5): test_env_detection_flags(), has_docker(), is_android(), is_termux(), should_show_docker_tab()

### Community 94 - "test_textual_termux.py"
Cohesion: 0.20
Nodes (11): isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard(), wait_until() (+3 more)

### Community 95 - "Par"
Cohesion: 0.20
Nodes (4): adicionar_par(), Par, remover_par(), salvar_vault()

### Community 96 - "json"
Cohesion: 0.20
Nodes (11): test_graphify_artifact_excludes_private_runtime_sources(), _field_names(), _load_locale(), test_i18n_all_values_non_empty_strings(), test_i18n_placeholder_parity(), test_i18n_pt_en_key_parity(), _probe_modules(), test_entrypoint_import_is_a_lightweight_dispatcher() (+3 more)

### Community 97 - "monitor/__init__.py"
Cohesion: 0.24
Nodes (4): __getattr__(), StalkerConfig, test_legacy_defaults_never_restore_speculative_external_target(), test_legacy_monitor_returns_without_ping_when_onboarding_is_incomplete()

### Community 98 - "PingStats"
Cohesion: 0.29
Nodes (3): make_ascii_graph(), make_graph_panel(), PingStats

### Community 99 - "test_termux_env.py"
Cohesion: 0.15
Nodes (5): test_collect_android_telemetry_battery_api_fallback_and_never_raises(), test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_termux_api_helpers(), toggle_keyboard_page()

### Community 105 - "EventSeverity"
Cohesion: 0.27
Nodes (3): test_zone_intrusion_rule(), EventSeverity, ZoneIntrusionRule

### Community 109 - "_require_safe_child"
Cohesion: 0.33
Nodes (3): test_runtime_subdirectory_link_is_rejected(), _is_link_like(), _require_safe_child()

### Community 116 - "os"
Cohesion: 0.10
Nodes (20): test_cli_status_and_check_json(), test_resolve_github_token_precedence_and_no_secret_in_label(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run(), test_save_token_file_rejects_empty_or_multiline(), test_update_repository_states_and_cooldown(), send_termux_notification(), _alt_token_file_path() (+12 more)

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 872 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **103 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `VareduraTextualApp` to `t`, `stalker.py`, `WSLDockerCleaner`, `CamerasMixin`, `_load_camera_backend`, `load_network_config`, `network_ui.py`, `_load_camera_backend`, `i18n/__init__.py`, `._render_ports_table`, `shutil`, `.compact_vhdx_files`, `speed_tester.py`, `json`, `handle_key`, `Par`, `TermuxMixin`, `main`, `TargetPickerScreen`, `.run_command_async`, `DailyLogWriter`, `quick_cleanup.py`, `._compose_cameras`, `quick_cleanup`, `is_termux`, `Par`, `PingStats`, `._browse_arquivo`, `RepairConfirmationScreen`?**
  _High betweenness centrality (0.149) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `VareduraTextualApp` (e.g. with `DiagnosticOptions` and `NetworkState`) actually correct?**
  _`VareduraTextualApp` has 46 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `t` be split into smaller, more focused modules?**
  _Cohesion score 0.05150905432595573 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `t`, `test_textual_app.py`, `network_repairs.py`, `run_textual_app`, `network_diagnostics.py`, `CamerasMixin`, `ContinuousSpeedTester`, `test_network_repairs.py`, `load_network_config`, `._render_ports_table`, `PingTarget`, `shutil`, `TermuxMixin`, `TargetPickerScreen`, `test_textual_cameras.py`, `DailyLogWriter`, `is_termux`, `is_termux`, `test_textual_termux.py`, `PingStats`, `._refresh_live_settings_status`, `stop_continuous_testing`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `VareduraTextualApp` be split into smaller, more focused modules?**
  _Cohesion score 0.04397222806648433 - nodes in this community are weakly interconnected._