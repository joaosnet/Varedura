# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 104 files · ~132,294 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2750 nodes · 7052 edges · 204 communities (77 shown, 127 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 526 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `33727c88`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
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
- test_termux_env.py
- credenciais.py
- ._accept_ping_result
- CommandResult
- PlansMixin
- ._render_ping_update
- set_keyboard_key
- server.py
- load_network_config
- data_usage.py
- PingTarget
- FFmpegRunner
- MultiProviderSpeedTester
- NetworkSnapshot
- NetIPPacket
- test_speed_cleanup.py
- test_docker_cleanup.py
- test_port_catalog.py
- abrir_stream
- PlanProfile
- WSLDockerCleaner
- os
- install.ps1
- install.sh
- UnifiedCameraSource
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
- socket
- test_textual_cameras.py
- redact_sensitive
- MultiProviderSpeedTester
- MotionHeatmap
- DailyLogWriter
- test_textual_cleanup_worker_uses_fake_cleaner
- test_textual_docker_reward_and_achievement
- SpeedtestNetProvider
- core.py
- TermuxKeysMixin
- CameraFleetManager
- paths.py
- ui_shared.py
- quick_cleanup
- BrasilBandaLargaProvider
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- is_android
- test_textual_termux.py
- TargetSelection
- subprocess
- monitor/__init__.py
- .from_config
- test_camera_engine.py
- .to_bytes
- test_shutdown_close_resources_terminates_players
- PingProbeResult
- YOLONanoDetector
- SimetProvider
- load_dark_theme_pref
- _ManualFuture
- ProgressState
- test_update_repository_states_and_cooldown
- test_xiongmai_p2p.py
- ._compose_cameras
- os
- varedura
- termux_install.sh
- test_cron_toggle_preserves_other_entries
- run_textual_app
- _require_safe_child
- time
- ShutdownScreen
- get_language
- PlanProfile
- PingStats
- _HangingPopen
- league_detector.py
- get_docker_vhdx_paths
- .start

## God Nodes (most connected - your core abstractions)
1. `t()` - 209 edges
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

## Communities (204 total, 127 thin omitted)

### Community 2 - "test_league_detector.py"
Cohesion: 0.14
Nodes (24): LeagueDetectionResult, LeagueDetectorState, LeagueMatchDetector, loop(), _detector(), _Process, _tcp(), test_absolute_poll_cadence_ends_session_promptly_after_three_failures() (+16 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.10
Nodes (28): PortInfo, PortScannerState, ProcessConnections, isolated_ui_prefs(), _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring() (+20 more)

### Community 4 - "time"
Cohesion: 0.09
Nodes (17): test_iou_calculation(), test_line_crossing_rule(), test_nms_suppression(), test_point_in_polygon(), test_stream_processor_pipeline(), test_zone_intrusion_rule(), compute_iou(), Detection (+9 more)

### Community 5 - "CameraBridge"
Cohesion: 0.13
Nodes (6): _atomic_write_json(), CameraBridge, order(), _iso_now(), _parse_iso(), _read_json()

### Community 6 - "stalker.py"
Cohesion: 0.06
Nodes (14): check_keyboard(), ContractInfo, _draw_extra_pages(), _draw_text_page(), _flush_stdin(), get_last_export_path(), get_ping_command(), get_top_network_hogs() (+6 more)

### Community 7 - "t"
Cohesion: 0.11
Nodes (4): main(), parse_args(), main(), t()

### Community 8 - "PingScheduler"
Cohesion: 0.13
Nodes (22): PingScheduler, TargetRole, PingStatus, _Clock, _gateway(), _ManualExecutor, _result(), _selection() (+14 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.08
Nodes (25): build_ping_command(), create_custom_target(), _failure_status(), _is_android_env(), parse_ping_latency(), probe_ping(), target_by_id(), target_catalog() (+17 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.07
Nodes (30): DiagnosisReport, ProbeKind, _system_ssl_context(), _action_id(), _certificate_is_ca(), visit(), _der_tlvs(), _disruptive_block_reason() (+22 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.08
Nodes (22): _load_camera_backend(), carregar_lista(), combinar_credenciais(), _build_rtsp_request(), escanear_portas_camera(), escanear_rede(), hosts_da_faixa(), normalizar_faixa() (+14 more)

### Community 14 - "re"
Cohesion: 0.09
Nodes (23): _clean_ssid(), detect_active_network(), detect_default_gateway(), _detect_unix(), _detect_windows(), _kind_from_interface(), parse_netsh_wlan(), parse_route_get() (+15 more)

### Community 15 - "main"
Cohesion: 0.07
Nodes (14): stop_continuous_testing(), analyze_lag_source(), get_export_status(), is_android(), main(), _initial_port_scan(), make_connections_panel(), make_header() (+6 more)

### Community 16 - "textual_app.py"
Cohesion: 0.05
Nodes (13): columns_for(), layout_tier(), anatel_minimums(), format_duration(), _detect_system_language(), get_supported_languages(), init(), _load_preference() (+5 more)

### Community 17 - "CamerasMixin"
Cohesion: 0.06
Nodes (7): CamerasMixin, _worker(), _escolher_arquivo_txt(), adicionar_par(), remover_par(), salvar_vault(), remover_regiao()

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.09
Nodes (29): DiagnosticOptions, NetworkDiagnosticEngine, ProxyConfiguration, run_network_diagnosis(), SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner (+21 more)

### Community 19 - "Event"
Cohesion: 0.05
Nodes (38): _bounded_daemon_call(), _collect_linux_dhcp_configuration(), _collect_proxy_configuration(), CommandRunner, _default_route_command(), DiagnosticCancelled, HttpObservation, _interface_addresses() (+30 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.07
Nodes (10): ContinuousSpeedTester, SpeedTestConfig, test_bandwidth_worker_cancellation_is_observed_promptly(), test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers(), test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_prepared_bandwidth_test_honors_cancel_before_worker_starts() (+2 more)

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.21
Nodes (30): command(), make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic(), test_clear_location_is_idempotent_and_keeps_camera_in_catalog() (+22 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.21
Nodes (31): NetworkInterface, NetworkState, RepairExecutor, RepairKind, RepairStatus, _action(), _fake_der_certificate(), FakeRunner (+23 more)

### Community 25 - "test_termux_env.py"
Cohesion: 0.09
Nodes (12): test_collect_android_telemetry_battery_api_fallback_and_never_raises(), test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_discover_termux_tools_builtins_claro_shortcuts_and_custom(), test_discover_termux_tools_ignores_invalid_custom_json(), test_native_text_dialog_parses_ok_and_cancel(), test_termux_api_helpers(), discover_termux_tools() (+4 more)

### Community 26 - "credenciais.py"
Cohesion: 0.09
Nodes (17): monta(), monta(), carregar_conhecidos(), carregar_vault(), CredencialIP, esquecer_ip(), lembrar_ip(), Par (+9 more)

### Community 29 - "CommandResult"
Cohesion: 0.11
Nodes (11): CommandResult, RepairAction, RepairResult, SubprocessRepairRunner, run(), run(), run(), run() (+3 more)

### Community 30 - "PlansMixin"
Cohesion: 0.15
Nodes (3): _fmt_number(), PlansMixin, find_profile()

### Community 32 - "set_keyboard_key"
Cohesion: 0.18
Nodes (9): test_extra_keys_macros_and_temporary_keyboard_key(), test_publish_export_copies_to_shared_documents(), extra_key_macros(), visit(), publish_export(), _read_extra_keys(), set_keyboard_key(), shared_documents_dir() (+1 more)

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
Cohesion: 0.12
Nodes (14): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingTarget, TargetCategory, _result(), test_csv_rows_are_contiguous_by_target_generation() (+6 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.08
Nodes (8): FakeProcess, FakeRunner, test_hls_h264_uses_remux_without_audio(), test_snapshot_failure_is_reduced_to_safe_enum(), CaptureResult, FFmpegRunner, HlsProcess, _replace_with_retry()

### Community 41 - "NetworkSnapshot"
Cohesion: 0.13
Nodes (14): classify_diagnosis(), collect_network_snapshot(), Confidence, Evidence, _evidence_for_snapshot(), _failure_probe(), FailureCause, _http_failure_cause() (+6 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.18
Nodes (4): NetIPPacket, XiongmaiNetIPClient, _delayed_stop(), test_netip_client_workflow()

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.18
Nodes (8): _safe_quit(), _sane_ping(), FakeDriver, test_provider_cleanup_quits_and_clears_driver(), test_safe_quit_calls_quit(), test_safe_quit_fallback_kills_process(), test_safe_quit_handles_none(), test_sane_ping_discards_absurd_latency()

### Community 49 - "test_docker_cleanup.py"
Cohesion: 0.10
Nodes (11): test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers(), fake_run_command() (+3 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.13
Nodes (11): sort_key(), classify_exposure(), describe_port(), _load(), test_catalog_keys_translated(), test_classify_exposure(), test_describe_port_ephemeral(), test_describe_port_known() (+3 more)

### Community 51 - "abrir_stream"
Cohesion: 0.11
Nodes (8): abrir_stream(), _achar_exe(), comando_mpv_terminal(), detectar_player(), erro_se_morreu(), _montar_comando(), test_video_android_player_priority_and_commands(), test_video_erro_se_morreu_and_capturar_e_abrir_snapshot()

### Community 52 - "PlanProfile"
Cohesion: 0.15
Nodes (11): ActiveNetwork, bind_to_network(), evaluate_speed(), PlanProfile, select_profile(), _isolated_plan_storage(), _sample(), test_bind_to_network_prefers_ssid_then_gateway() (+3 more)

### Community 53 - "WSLDockerCleaner"
Cohesion: 0.10
Nodes (4): WSLDockerCleaner, _drain_and_wait(), stream_reader(), test_parse_wsl_distros_drops_shell_metacharacters()

### Community 54 - "os"
Cohesion: 0.14
Nodes (13): get_speed_tester(), SpeedStats, SpeedTestResult, start_continuous_testing(), export_combined_report(), _generate_combined_pdf_worker(), snapshot_ping_history(), cleanup_exports() (+5 more)

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
Cohesion: 0.19
Nodes (14): test_root_and_claro_suite_detection(), AndroidTelemetry, collect_android_telemetry(), _collect_battery(), _collect_ips(), _collect_memory(), _collect_proc_net_dev(), _collect_uptime() (+6 more)

### Community 61 - "camera_bridge.py"
Cohesion: 0.08
Nodes (17): test_inventory_id_survives_password_change_inside_vendor_path(), test_inventory_ids_are_stable_and_private_state_has_no_endpoint(), test_inventory_never_uses_ip_as_default_name(), ActiveSession, BridgeAlreadyRunning, build_parser(), _canonical_rtsp_identity(), _finite_real() (+9 more)

### Community 62 - "pathlib"
Cohesion: 0.08
Nodes (15): Geo, geolocalizar(), obter_logger(), adicionar_regiao(), carregar_regioes(), Regiao, _salvar_json(), salvar_regioes() (+7 more)

### Community 63 - "handle_key"
Cohesion: 0.12
Nodes (13): handle_key(), load_prefs(), prompt_change_contracted_speed(), prompt_change_external(), prompt_change_gateway(), prompt_change_interval(), prompt_change_threshold(), prompt_export_report() (+5 more)

### Community 64 - "current_cycle"
Cohesion: 0.14
Nodes (6): current_cycle(), CycleWindow, quota_status(), QuotaStatus, _quota_lines(), test_cycle_rolls_forward_and_quota_projection()

### Community 66 - "port_scanner.py"
Cohesion: 0.12
Nodes (18): get_listening_ports(), get_process_connections_count(), get_system_network_stats(), _read_proc_meminfo(), _read_proc_net_totals(), run_full_scan(), _safe_net_connections(), search_port() (+10 more)

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
Cohesion: 0.22
Nodes (3): CameraLocation, LocationStore, _valid_uuid()

### Community 74 - "TargetPickerScreen"
Cohesion: 0.05
Nodes (31): merge_visible_selection(), RepairConfirmationScreen, TargetPickerScreen, concurrency, cancel-in-progress, group, jobs, lint (+23 more)

### Community 75 - "socket"
Cohesion: 0.21
Nodes (6): _base24(), detectar_redes(), _eh_privado_utilizavel(), _ip_primario(), _ips_hostname(), RedeLocal

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.29
Nodes (13): isolated_state(), open_cameras(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input(), test_cameras_credential_add_and_remove(), test_cameras_import_credential_lists(), test_cameras_open_port_saved_without_credential(), test_cameras_port_scan_populates_table() (+5 more)

### Community 77 - "redact_sensitive"
Cohesion: 0.15
Nodes (8): configurar(), _redact_arg(), redact_sensitive(), RedactingFilter, RedactingFormatter, test_redacting_formatter_covers_exception_text(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth(), configure_logging()

### Community 80 - "DailyLogWriter"
Cohesion: 0.12
Nodes (3): DailyLogWriter, cleanup_label(), run_cleanup_steps()

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.24
Nodes (3): SpeedtestNetProvider, test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "core.py"
Cohesion: 0.08
Nodes (14): run_cmd(), CleanupStepResult, _powershell_encoded_command(), _ps_single_quoted(), _strip_powershell_clixml(), _temp_file_path(), buscar_prefixos_por_asn(), obter_amostra_aleatoria() (+6 more)

### Community 89 - "ui_shared.py"
Cohesion: 0.04
Nodes (35): RichRenderable, _add_common_status_rows(), build_cleanup_status_panel(), build_cleanup_steps_table(), build_dashboard_status(), build_ports_summary(), build_scanner_tables(), build_settings_status_table() (+27 more)

### Community 91 - "BrasilBandaLargaProvider"
Cohesion: 0.24
Nodes (3): BrasilBandaLargaProvider, _chrome_service(), test_chrome_service_suppresses_console_window()

### Community 93 - "is_android"
Cohesion: 0.18
Nodes (6): test_env_detection_flags(), get_termux_prefix(), has_docker(), is_android(), is_termux(), should_show_docker_tab()

### Community 94 - "test_textual_termux.py"
Cohesion: 0.20
Nodes (12): isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard(), wait_until() (+4 more)

### Community 95 - "TargetSelection"
Cohesion: 0.29
Nodes (3): TargetSelection, test_selection_enforces_five_persistent_and_primary(), test_selection_round_trip_and_legacy_migration()

### Community 96 - "subprocess"
Cohesion: 0.10
Nodes (18): capturar_e_abrir_snapshot(), _ffplay_disponivel(), salvar_snapshot(), _probe_modules(), test_entrypoint_import_is_a_lightweight_dispatcher(), test_first_textual_frame_does_not_import_monitor_backends(), test_idle_speed_tester_does_not_materialize_providers(), test_textual_shell_defers_optional_backends_and_images() (+10 more)

### Community 97 - "monitor/__init__.py"
Cohesion: 0.24
Nodes (4): __getattr__(), StalkerConfig, test_legacy_defaults_never_restore_speculative_external_target(), test_legacy_monitor_returns_without_ping_when_onboarding_is_incomplete()

### Community 99 - "test_camera_engine.py"
Cohesion: 0.22
Nodes (3): parse_camera_url(), test_parse_camera_url(), MockNetIPServer

### Community 102 - "PingProbeResult"
Cohesion: 0.13
Nodes (7): _Flight, SchedulerTargetSnapshot, _TargetState, HostKind, PingProbeResult, PingSample, fake_probe()

### Community 105 - "load_dark_theme_pref"
Cohesion: 0.20
Nodes (3): theme_name(), load_dark_theme_pref(), test_theme_toggle_persists_and_narrow_header_has_no_subtitle()

### Community 111 - "test_xiongmai_p2p.py"
Cohesion: 0.18
Nodes (5): encrypt_xiongmai_digest(), encrypt_xiongmai_password(), NetIPMsgId, PTZCommand, test_xiongmai_password_encryption()

### Community 116 - "os"
Cohesion: 0.15
Nodes (16): test_resolve_github_token_precedence_and_no_secret_in_label(), test_save_token_file_rejects_empty_or_multiline(), send_termux_notification(), _alt_token_file_path(), _default_repo_dir(), get_repo_status(), main(), _prefs_file_path() (+8 more)

### Community 121 - "test_cron_toggle_preserves_other_entries"
Cohesion: 0.50
Nodes (3): test_cron_toggle_preserves_other_entries(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run()

### Community 181 - "_require_safe_child"
Cohesion: 0.33
Nodes (3): test_runtime_subdirectory_link_is_rejected(), _is_link_like(), _require_safe_child()

### Community 183 - "time"
Cohesion: 0.10
Nodes (8): CameraCapabilities, CameraProtocol, DiscoveredCamera, XiongmaiDiscovery, test_geometric_line_intersection(), ccw(), segments_intersect(), VideoFrame

### Community 193 - "PlanProfile"
Cohesion: 0.11
Nodes (15): _fmt_speed(), number(), text(), apply_profile(), describe_binding(), _iso_date(), new_profile_id(), _number() (+7 more)

### Community 195 - "PingStats"
Cohesion: 0.29
Nodes (3): make_ascii_graph(), make_graph_panel(), PingStats

### Community 198 - "league_detector.py"
Cohesion: 0.09
Nodes (13): _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, LeagueEndpoint, mask_endpoint_ip(), _RejectLiveClientRedirects (+5 more)

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 969 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **127 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `t` to `VareduraTextualApp`, `stalker.py`, `test_rtsp_modules.py`, `main`, `textual_app.py`, `CamerasMixin`, `test_termux_env.py`, `credenciais.py`, `._accept_ping_result`, `PlansMixin`, `._render_ping_update`, `PingTarget`, `test_port_catalog.py`, `abrir_stream`, `PlanProfile`, `WSLDockerCleaner`, `os`, `ShutdownScreen`, `handle_key`, `PlanProfile`, `PingStats`, `TermuxMixin`, `TargetPickerScreen`, `DailyLogWriter`, `core.py`, `TermuxKeysMixin`, `ui_shared.py`, `quick_cleanup`, `is_android`, `subprocess`, `.from_config`, `._compose_cameras`, `os`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `VareduraTextualApp` (e.g. with `test_compact_mode_only_on_narrow_screens()` and `test_theme_toggle_persists_and_narrow_header_has_no_subtitle()`) actually correct?**
  _`VareduraTextualApp` has 44 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `VareduraTextualApp` be split into smaller, more focused modules?**
  _Cohesion score 0.06412583182093164 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `test_textual_app.py`, `t`, `ping_targets.py`, `re`, `main`, `textual_app.py`, `CamerasMixin`, `test_termux_env.py`, `._accept_ping_result`, `PlansMixin`, `._render_ping_update`, `PingTarget`, `test_port_catalog.py`, `run_textual_app`, `ShutdownScreen`, `get_language`, `.on_main_tab_activated`, `TermuxMixin`, `TargetPickerScreen`, `test_textual_cameras.py`, `DailyLogWriter`, `test_textual_cleanup_worker_uses_fake_cleaner`, `test_textual_docker_reward_and_achievement`, `TermuxKeysMixin`, `ui_shared.py`, `is_android`, `test_textual_termux.py`, `subprocess`, `.from_config`, `test_shutdown_close_resources_terminates_players`, `load_dark_theme_pref`, `os`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_league_detector.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13765182186234817 - nodes in this community are weakly interconnected._