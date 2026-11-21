# Graph Report - Varedura  (2026-11-21)

## Corpus Check
- 108 files · ~141,737 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 5)

## Summary
- 2917 nodes · 7525 edges · 209 communities (87 shown, 122 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 553 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5c3ce9df`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- t
- stalker.py
- data_usage.py
- test_textual_app.py
- ._accept_ping_result
- CameraBridge
- AIStreamProcessor
- load_network_config
- PingScheduler
- compute_health_score
- ping_targets.py
- network_repairs.py
- test_rtsp_modules.py
- re
- main
- redact_sensitive
- CamerasMixin
- test_network_diagnostics.py
- Event
- ContinuousSpeedTester
- test_camera_bridge.py
- test_network_repairs.py
- credenciais.py
- ai_vision/__init__.py
- QuotaStatus
- CommandResult
- PlansMixin
- .log
- set_keyboard_key
- server.py
- TargetSelection
- NetIPPacket
- PingTarget
- FFmpegRunner
- speed_providers.py
- network_diagnostics.py
- NetIPPacket
- test_speed_cleanup.py
- .configure_wsl_sparse
- test_port_catalog.py
- shutil
- PingProbeResult
- .compact_vhdx_files
- resolver_ip
- install.ps1
- install.sh
- UnifiedCameraSource
- test_android_adaptations.py
- termux_env.py
- camera_bridge.py
- regioes.py
- handle_key
- port_scanner.py
- t
- datetime
- mapa.py
- TermuxMixin
- LocationStore
- TargetPickerScreen
- test_auto_speed.py
- test_textual_cameras.py
- CameraFleetManager
- MLabNdt7Provider
- EventSeverity
- DailyLogWriter
- validar_stream
- SpeedtestNetProvider
- core.py
- TermuxKeysMixin
- Detection
- MotionHeatmap
- VareduraTextualApp
- quick_cleanup
- test_layout.py
- test_bridge_restart_terminates_only_matching_orphan_ffmpeg
- ._compose_dashboard
- _WebSocket
- log.py
- json
- CameraFleetManager
- test_i18n_parity.py
- InfoStream
- DataUsageTracker
- test_textual_termux.py
- SimetProvider
- shutil
- ._importar_credenciais
- steps
- xiongmai.py
- ._compose_cameras
- os
- varedura
- termux_install.sh
- test_ai_vision.py
- PingStats
- prompt_export_report
- _require_safe_child
- run_textual_app
- ._browse_arquivo
- ._get_all_vhdx_paths
- textual_app.py
- stop_continuous_testing
- time
- _ManualFuture
- textual_plans.py
- get_top_network_hogs
- _HangingPopen
- league_detector.py
- _CompletedPopen

## God Nodes (most connected - your core abstractions)
1. `t()` - 217 edges
2. `VareduraTextualApp` - 184 edges
3. `CamerasMixin` - 73 edges
4. `WSLDockerCleaner` - 71 edges
5. `CameraBridge` - 52 edges
6. `PingTarget` - 47 edges
7. `PlansMixin` - 40 edges
8. `_load_camera_backend()` - 38 edges
9. `PlanProfile` - 37 edges
10. `PingScheduler` - 37 edges

## Surprising Connections (you probably didn't know these)
- `_load_camera_backend()` --indirect_call--> `adicionar_par()`  [INFERRED]
  cli/textual_cameras.py → rtsp/credenciais.py
- `_load_camera_backend()` --indirect_call--> `carregar_conhecidos()`  [INFERRED]
  cli/textual_cameras.py → rtsp/credenciais.py
- `_load_camera_backend()` --indirect_call--> `carregar_lista()`  [INFERRED]
  cli/textual_cameras.py → rtsp/credenciais.py
- `_load_camera_backend()` --indirect_call--> `carregar_vault()`  [INFERRED]
  cli/textual_cameras.py → rtsp/credenciais.py
- `_load_camera_backend()` --indirect_call--> `combinar_credenciais()`  [INFERRED]
  cli/textual_cameras.py → rtsp/credenciais.py

## Import Cycles
- 2-file cycle: `cli/textual_app.py -> cli/textual_cameras.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_termux.py -> cli/textual_app.py`
- 2-file cycle: `cli/textual_app.py -> cli/textual_plans.py -> cli/textual_app.py`

## Communities (209 total, 122 thin omitted)

### Community 1 - "stalker.py"
Cohesion: 0.08
Nodes (11): check_keyboard(), ContractInfo, _draw_extra_pages(), _draw_text_page(), _flush_stdin(), get_last_export_path(), get_ping_command(), parse_ping() (+3 more)

### Community 2 - "data_usage.py"
Cohesion: 0.14
Nodes (10): _atomic_write(), get_usage_tracker(), load_speed_samples(), record_speed_sample(), samples_for_report(), SpeedSample, _quota_lines(), _pdf_text() (+2 more)

### Community 3 - "test_textual_app.py"
Cohesion: 0.06
Nodes (29): ShutdownScreen, PortScannerState, ProcessConnections, _patch_network(), test_capture_screenshot_saves_svg_and_txt(), test_diagnosis_renders_repair_actions_inside_responsive_grid(), test_first_run_requires_selection_before_external_monitoring(), test_hidden_tabs_are_composed_only_when_opened() (+21 more)

### Community 4 - "._accept_ping_result"
Cohesion: 0.10
Nodes (5): anatel_minimums(), format_duration(), test_speed_tab_shows_plan_history_including_background_runs(), test_additional_targets_do_not_update_primary_health_sparkline(), test_callback_from_previous_network_run_is_discarded()

### Community 5 - "CameraBridge"
Cohesion: 0.13
Nodes (6): _atomic_write_json(), CameraBridge, order(), _iso_now(), _parse_iso(), _read_json()

### Community 6 - "AIStreamProcessor"
Cohesion: 0.16
Nodes (4): test_stream_processor_pipeline(), SpatialEvent, AIStreamProcessor, VideoFrame

### Community 7 - "load_network_config"
Cohesion: 0.11
Nodes (18): load_network_config(), save_network_config(), _valid_legacy_host(), _verified_stored_app_ca(), prompt_change_external(), test_background_switch_in_settings_drives_the_scheduler(), test_settings_saves_auto_speed_interval(), _prefs() (+10 more)

### Community 8 - "PingScheduler"
Cohesion: 0.11
Nodes (23): PingScheduler, loop(), TargetRole, PingStatus, _Clock, _gateway(), _ManualExecutor, _result() (+15 more)

### Community 9 - "compute_health_score"
Cohesion: 0.24
Nodes (8): _clamp(), compute_health_score(), test_health_score_all_timeouts_is_critical(), test_health_score_falls_back_to_local_history_and_respects_window(), test_health_score_great_connection_is_top_tier(), test_health_score_laggy_is_lower_than_clean(), test_health_score_no_data_is_neutral(), test_health_score_speed_compliance_weights_10_percent()

### Community 11 - "ping_targets.py"
Cohesion: 0.08
Nodes (25): _Flight, build_ping_command(), create_custom_target(), _failure_status(), HostKind, _is_android_env(), parse_ping_latency(), probe_ping() (+17 more)

### Community 12 - "network_repairs.py"
Cohesion: 0.06
Nodes (32): DiagnosisReport, ProbeKind, _system_ssl_context(), _action_id(), _certificate_is_ca(), visit(), _der_tlvs(), _disruptive_block_reason() (+24 more)

### Community 13 - "test_rtsp_modules.py"
Cohesion: 0.13
Nodes (15): carregar_lista(), combinar_credenciais(), hosts_da_faixa(), normalizar_faixa(), test_carregar_lista_arquivo_ausente(), test_carregar_lista_ignora_branco_e_comentarios(), test_combinar_credenciais_apenas_uma_lista(), test_combinar_credenciais_produto() (+7 more)

### Community 14 - "re"
Cohesion: 0.09
Nodes (22): _clean_ssid(), detect_active_network(), detect_default_gateway(), _detect_unix(), _detect_windows(), _kind_from_interface(), parse_netsh_wlan(), parse_route_get() (+14 more)

### Community 15 - "main"
Cohesion: 0.09
Nodes (13): analyze_lag_source(), is_android(), main(), _initial_port_scan(), make_connections_panel(), make_header(), make_help_panel(), make_log_panel() (+5 more)

### Community 16 - "redact_sensitive"
Cohesion: 0.15
Nodes (8): configurar(), _redact_arg(), redact_sensitive(), RedactingFilter, RedactingFormatter, test_redacting_formatter_covers_exception_text(), test_redaction_removes_rtsp_userinfo_password_and_basic_auth(), configure_logging()

### Community 18 - "test_network_diagnostics.py"
Cohesion: 0.09
Nodes (31): DiagnosticOptions, NetworkDiagnosticEngine, ProxyConfiguration, run_network_diagnosis(), SnapshotCollector, _diagnose(), FakeBackend, FakeCommandRunner (+23 more)

### Community 19 - "Event"
Cohesion: 0.05
Nodes (39): _bounded_daemon_call(), _collect_linux_dhcp_configuration(), _collect_proxy_configuration(), CommandRunner, _default_route_command(), DiagnosticCancelled, HttpObservation, _interface_addresses() (+31 more)

### Community 20 - "ContinuousSpeedTester"
Cohesion: 0.06
Nodes (12): ContinuousSpeedTester, SpeedStats, SpeedTestConfig, SpeedTestResult, test_websocket_client_frame_header_and_worker_registry(), test_bandwidth_worker_cancellation_is_observed_promptly(), test_continuous_loop_uses_the_same_reservation_path(), test_continuous_stop_cleans_active_drivers() (+4 more)

### Community 21 - "test_camera_bridge.py"
Cohesion: 0.21
Nodes (30): command(), make_bridge(), new_id(), put_command(), shutdown_executor(), test_capture_logs_only_sanitized_state_transitions(), test_catalog_is_sanitized_and_atomic(), test_clear_location_is_idempotent_and_keeps_camera_in_catalog() (+22 more)

### Community 24 - "test_network_repairs.py"
Cohesion: 0.21
Nodes (31): NetworkInterface, NetworkState, RepairExecutor, RepairKind, RepairStatus, _action(), _fake_der_certificate(), FakeRunner (+23 more)

### Community 25 - "credenciais.py"
Cohesion: 0.16
Nodes (9): carregar_conhecidos(), carregar_vault(), CredencialIP, esquecer_ip(), lembrar_ip(), _registrar_diag(), _sucesso(), salvar_conhecidos() (+1 more)

### Community 29 - "CommandResult"
Cohesion: 0.11
Nodes (11): CommandResult, RepairAction, RepairRunner, SubprocessRepairRunner, run(), run(), run(), run() (+3 more)

### Community 30 - "PlansMixin"
Cohesion: 0.11
Nodes (4): _fmt_number(), _fmt_speed(), PlansMixin, find_profile()

### Community 31 - ".log"
Cohesion: 0.10
Nodes (3): main(), WSLDockerCleaner, test_parse_wsl_distros_drops_shell_metacharacters()

### Community 32 - "set_keyboard_key"
Cohesion: 0.18
Nodes (9): test_extra_keys_macros_and_temporary_keyboard_key(), test_publish_export_copies_to_shared_documents(), extra_key_macros(), visit(), publish_export(), _read_extra_keys(), set_keyboard_key(), shared_documents_dir() (+1 more)

### Community 33 - "server.py"
Cohesion: 0.09
Nodes (11): _confirmation_required(), docker_full_cleanup(), docker_quick_cleanup(), docker_status(), _dry_run_preview(), get_logs(), _is_docker_running(), port_scan() (+3 more)

### Community 34 - "TargetSelection"
Cohesion: 0.29
Nodes (3): TargetSelection, test_selection_enforces_five_persistent_and_primary(), test_selection_round_trip_and_legacy_migration()

### Community 35 - "NetIPPacket"
Cohesion: 0.17
Nodes (4): DiscoveredCamera, NetIPPacket, test_netip_packet_incomplete_buffer(), test_netip_packet_serialization()

### Community 36 - "PingTarget"
Cohesion: 0.12
Nodes (14): mask_ip(), NetworkHistoryRecord, NetworkSessionHistory, summarize_latencies(), PingTarget, TargetCategory, _result(), test_csv_rows_are_contiguous_by_target_generation() (+6 more)

### Community 37 - "FFmpegRunner"
Cohesion: 0.08
Nodes (8): FakeProcess, FakeRunner, test_hls_h264_uses_remux_without_audio(), test_snapshot_failure_is_reduced_to_safe_enum(), CaptureResult, FFmpegRunner, HlsProcess, _replace_with_retry()

### Community 41 - "network_diagnostics.py"
Cohesion: 0.13
Nodes (12): classify_diagnosis(), collect_network_snapshot(), Confidence, Evidence, _evidence_for_snapshot(), _failure_probe(), FailureCause, _http_failure_cause() (+4 more)

### Community 47 - "NetIPPacket"
Cohesion: 0.18
Nodes (3): XiongmaiNetIPClient, _delayed_stop(), test_netip_client_workflow()

### Community 48 - "test_speed_cleanup.py"
Cohesion: 0.12
Nodes (11): BrasilBandaLargaProvider, _chrome_service(), _safe_quit(), _sane_ping(), FakeDriver, test_chrome_service_suppresses_console_window(), test_provider_cleanup_quits_and_clears_driver(), test_safe_quit_calls_quit() (+3 more)

### Community 49 - ".configure_wsl_sparse"
Cohesion: 0.10
Nodes (15): CleanupStepResult, test_compact_vhdx_files_requests_elevation_and_falls_back(), test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(), test_configure_wsl_sparse_elevates_manage_commands(), test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(), test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(), test_container_step_only_prunes_stopped_containers(), test_docker_cleanup_preserves_running_containers() (+7 more)

### Community 50 - "test_port_catalog.py"
Cohesion: 0.14
Nodes (12): sort_key(), classify_exposure(), describe_port(), is_exposed(), _load(), test_catalog_keys_translated(), test_classify_exposure(), test_describe_port_ephemeral() (+4 more)

### Community 51 - "shutil"
Cohesion: 0.09
Nodes (18): _load_camera_backend(), escanear_portas_camera(), escanear_rede(), testar_porta(), abrir_stream(), _achar_exe(), capturar_e_abrir_snapshot(), comando_mpv_terminal() (+10 more)

### Community 52 - "PingProbeResult"
Cohesion: 0.18
Nodes (5): SchedulerTargetSnapshot, _TargetState, PingProbeResult, PingSample, fake_probe()

### Community 53 - ".compact_vhdx_files"
Cohesion: 0.09
Nodes (6): _ps_single_quoted(), _strip_powershell_clixml(), _temp_file_path(), _drain_and_wait(), stream_reader(), test_powershell_clixml_progress_is_removed_from_stderr()

### Community 54 - "resolver_ip"
Cohesion: 0.15
Nodes (6): monta(), monta(), Par, _promover_caminho(), resolver_ip(), _tratar_falha_step()

### Community 55 - "install.ps1"
Cohesion: 0.27
Nodes (18): Add-ToUserPath(), Get-CmdVersion(), Ask-Action(), Check-Dependencies(), Confirm-Yes(), Detect-OS(), Do-Check(), Do-Install() (+10 more)

### Community 56 - "install.sh"
Cohesion: 0.28
Nodes (20): cmd_exists(), get_version(), is_installed(), main(), refresh_path(), install.sh script, ask_action(), check_dependencies() (+12 more)

### Community 58 - "UnifiedCameraSource"
Cohesion: 0.10
Nodes (5): CameraMetadata, UnifiedCameraSource, SofiaP2PClient, test_unified_camera_source_netip(), MockNetIPServer

### Community 59 - "test_android_adaptations.py"
Cohesion: 0.13
Nodes (8): __getattr__(), StalkerConfig, _render(), test_dashboard_hides_docker_and_mcp_rows_without_docker_tab(), test_dashboard_traffic_uses_android_wifi_counters(), test_interfaces_fall_back_to_sysfs_when_stats_are_denied(), test_legacy_defaults_never_restore_speculative_external_target(), test_legacy_monitor_returns_without_ping_when_onboarding_is_incomplete()

### Community 60 - "termux_env.py"
Cohesion: 0.07
Nodes (30): test_collect_android_telemetry_battery_api_fallback_and_never_raises(), test_discover_termux_tools_builtins_claro_shortcuts_and_custom(), test_discover_termux_tools_ignores_invalid_custom_json(), test_env_detection_flags(), test_root_and_claro_suite_detection(), test_termux_services_list_and_toggle(), AndroidTelemetry, collect_android_telemetry() (+22 more)

### Community 61 - "camera_bridge.py"
Cohesion: 0.08
Nodes (17): test_inventory_id_survives_password_change_inside_vendor_path(), test_inventory_ids_are_stable_and_private_state_has_no_endpoint(), test_inventory_never_uses_ip_as_default_name(), ActiveSession, BridgeAlreadyRunning, build_parser(), _canonical_rtsp_identity(), _finite_real() (+9 more)

### Community 62 - "regioes.py"
Cohesion: 0.18
Nodes (6): adicionar_regiao(), carregar_regioes(), Regiao, remover_regiao(), _salvar_json(), salvar_regioes()

### Community 63 - "handle_key"
Cohesion: 0.14
Nodes (11): handle_key(), load_prefs(), prompt_change_contracted_speed(), prompt_change_gateway(), prompt_change_interval(), prompt_change_threshold(), save_prefs(), set_allow_full_history_export() (+3 more)

### Community 66 - "port_scanner.py"
Cohesion: 0.11
Nodes (19): get_listening_ports(), get_process_connections_count(), get_system_network_stats(), PortInfo, _read_proc_meminfo(), _read_proc_net_totals(), run_full_scan(), _safe_net_connections() (+11 more)

### Community 67 - "t"
Cohesion: 0.05
Nodes (27): _add_common_status_rows(), build_cleanup_status_panel(), build_cleanup_steps_table(), build_dashboard_status(), build_ports_summary(), build_scanner_tables(), build_settings_status_table(), build_tool_option() (+19 more)

### Community 68 - "datetime"
Cohesion: 0.18
Nodes (8): get_speed_tester(), start_continuous_testing(), export_combined_report(), _generate_combined_pdf_worker(), snapshot_ping_history(), cleanup_exports(), test_generate_small_pdf(), test_large_history_downsampling_and_full_flag()

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
Cohesion: 0.11
Nodes (6): RepairConfirmationScreen, TargetPickerScreen, on, pull_request, push, branches

### Community 75 - "test_auto_speed.py"
Cohesion: 0.16
Nodes (10): _FakeTester, _result(), test_concurrent_run_is_reported_busy(), test_failed_run_retries_in_fifteen_minutes(), test_measure_parallel_ignores_warmup_and_sums_streams(), test_never_runs_on_mobile_data_even_when_forced(), test_normalize_minutes_bounds(), test_runs_when_due_records_sample_and_respects_interval() (+2 more)

### Community 76 - "test_textual_cameras.py"
Cohesion: 0.16
Nodes (19): number(), text(), RedeLocal, isolated_state(), open_cameras(), test_cameras_401_limit_preserves_saved_url_and_opens_on_click(), test_cameras_action_cam_log_non_windows(), test_cameras_browse_fills_input() (+11 more)

### Community 77 - "CameraFleetManager"
Cohesion: 0.25
Nodes (3): CameraFleetManager, XiongmaiDiscovery, test_camera_fleet_manager()

### Community 78 - "MLabNdt7Provider"
Cohesion: 0.12
Nodes (5): CloudflareProvider, MLabNdt7Provider, SpeedTestResult, main(), run_provider()

### Community 79 - "EventSeverity"
Cohesion: 0.31
Nodes (3): test_zone_intrusion_rule(), EventSeverity, ZoneIntrusionRule

### Community 80 - "DailyLogWriter"
Cohesion: 0.12
Nodes (3): DailyLogWriter, cleanup_label(), run_cleanup_steps()

### Community 83 - "validar_stream"
Cohesion: 0.11
Nodes (20): classificar_erro_rtsp(), descobrir_stream(), _eh_erro_rede_fatal(), _resumir_erro_stderr(), validar_stream(), _validar_stream_ffmpeg(), _only_ffmpeg(), test_classificar_erro_rtsp_cobre_tipos_principais() (+12 more)

### Community 84 - "SpeedtestNetProvider"
Cohesion: 0.16
Nodes (5): SpeedtestNetProvider, test_every_bandwidth_provider_runs_in_an_isolated_worker(), fake_popen(), test_speedtest_provider_uses_isolated_json_subprocess(), fake_popen()

### Community 85 - "core.py"
Cohesion: 0.10
Nodes (8): main(), parse_args(), run_cmd(), _powershell_encoded_command(), buscar_prefixos_por_asn(), obter_amostra_aleatoria(), obter_blocos_rede(), obter_espaco_amostral_completo()

### Community 87 - "Detection"
Cohesion: 0.18
Nodes (5): test_line_crossing_rule(), Detection, GeometricRule, LineCrossingRule, LoiteringRule

### Community 89 - "VareduraTextualApp"
Cohesion: 0.05
Nodes (6): _cleanup_checkbox_id(), VareduraTextualApp, selected_cleanup_keys(), test_late_league_callback_cannot_reenable_disabled_detector(), test_shutdown_close_resources_terminates_players(), test_shutdown_stop_monitors_sets_events()

### Community 91 - "test_layout.py"
Cohesion: 0.14
Nodes (6): columns_for(), layout_tier(), load_dark_theme_pref(), test_compact_mode_only_on_narrow_screens(), test_layout_tiers_and_columns(), test_theme_toggle_persists_and_narrow_header_has_no_subtitle()

### Community 93 - "._compose_dashboard"
Cohesion: 0.11
Nodes (3): RichRenderable, TargetPingCard, get_language()

### Community 95 - "log.py"
Cohesion: 0.07
Nodes (13): Geo, geolocalizar(), obter_logger(), caminhos(), _dedup(), _base24(), detectar_redes(), _eh_privado_utilizavel() (+5 more)

### Community 96 - "json"
Cohesion: 0.10
Nodes (15): _probe_modules(), test_entrypoint_import_is_a_lightweight_dispatcher(), test_first_textual_frame_does_not_import_monitor_backends(), test_idle_speed_tester_does_not_materialize_providers(), test_textual_shell_defers_optional_backends_and_images(), test_collect_android_telemetry_parses_sysfs_proc_and_ip(), fake_run(), test_native_text_dialog_parses_ok_and_cancel() (+7 more)

### Community 97 - "CameraFleetManager"
Cohesion: 0.19
Nodes (4): CameraCapabilities, CameraProtocol, parse_camera_url(), test_parse_camera_url()

### Community 98 - "test_i18n_parity.py"
Cohesion: 0.21
Nodes (5): _field_names(), _load_locale(), test_i18n_all_values_non_empty_strings(), test_i18n_placeholder_parity(), test_i18n_pt_en_key_parity()

### Community 100 - "InfoStream"
Cohesion: 0.20
Nodes (16): InfoStream, _monta_url_teste(), _setup_resolver(), test_resolver_ip_401_com_cofre_grande_limita_tentativas_e_evita_bloqueio(), fake_validar(), test_resolver_ip_401_encontra_nova_credencial_no_caminho_lembrado(), fake_validar(), test_resolver_ip_faz_pausa_entre_falhas_de_auth() (+8 more)

### Community 103 - "test_textual_termux.py"
Cohesion: 0.24
Nodes (11): isolated_termux_env(), test_docker_tab_visibility_in_termux_mode(), test_narrow_mobile_dashboard_layout_and_quick_actions(), test_termux_hub_claro_and_services_subtabs(), test_termux_lol_disabled_and_outage_notifications(), test_termux_onboarding_non_blocking_f12_and_screenshot(), test_termux_tool_launcher_modes_and_arg_guard(), wait_until() (+3 more)

### Community 104 - "SimetProvider"
Cohesion: 0.16
Nodes (3): ProgressState, SimetProvider, test_provider_cleanup_without_driver_is_safe()

### Community 105 - "shutil"
Cohesion: 0.09
Nodes (19): _command(), describe_status(), is_background_enabled(), is_cron_enabled(), is_due(), last_run(), _load_state(), main() (+11 more)

### Community 107 - "._importar_credenciais"
Cohesion: 0.27
Nodes (3): adicionar_par(), remover_par(), salvar_vault()

### Community 108 - "steps"
Cohesion: 0.10
Nodes (23): concurrency, cancel-in-progress, group, jobs, lint, test, name, runs-on (+15 more)

### Community 109 - "xiongmai.py"
Cohesion: 0.18
Nodes (5): encrypt_xiongmai_digest(), encrypt_xiongmai_password(), NetIPMsgId, PTZCommand, test_xiongmai_password_encryption()

### Community 116 - "os"
Cohesion: 0.09
Nodes (23): test_graphify_artifact_excludes_private_runtime_sources(), test_cli_status_and_check_json(), test_cron_toggle_preserves_other_entries(), test_resolve_github_token_precedence_and_no_secret_in_label(), test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(), fake_run(), test_save_token_file_rejects_empty_or_multiline(), test_update_repository_states_and_cooldown() (+15 more)

### Community 121 - "test_ai_vision.py"
Cohesion: 0.17
Nodes (9): test_geometric_line_intersection(), test_iou_calculation(), test_nms_suppression(), test_point_in_polygon(), compute_iou(), nms(), ccw(), point_in_polygon() (+1 more)

### Community 146 - "PingStats"
Cohesion: 0.29
Nodes (3): make_ascii_graph(), make_graph_panel(), PingStats

### Community 147 - "prompt_export_report"
Cohesion: 0.60
Nodes (4): prompt_export_report(), cleanup_exports(), test_prompt_export_cancel(), test_prompt_export_confirm_triggers_export()

### Community 179 - "_require_safe_child"
Cohesion: 0.33
Nodes (3): test_runtime_subdirectory_link_is_rejected(), _is_link_like(), _require_safe_child()

### Community 185 - "textual_app.py"
Cohesion: 0.07
Nodes (11): merge_visible_selection(), theme_name(), _detect_system_language(), get_supported_languages(), init(), _load_preference(), _load_translations(), save_preference() (+3 more)

### Community 188 - "time"
Cohesion: 0.08
Nodes (9): FastComProvider, _ChunkStream, http_download_worker(), worker(), http_upload_worker(), worker(), measure_parallel(), add() (+1 more)

### Community 193 - "textual_plans.py"
Cohesion: 0.08
Nodes (28): ActiveNetwork, apply_profile(), bind_to_network(), current_cycle(), CycleWindow, describe_binding(), evaluate_speed(), _iso_date() (+20 more)

### Community 198 - "league_detector.py"
Cohesion: 0.07
Nodes (37): _default_process_iter(), fetch_live_client_data(), _is_game_port(), _is_game_process(), LeagueCandidate, LeagueDetectionResult, LeagueDetectorState, LeagueEndpoint (+29 more)

## Knowledge Gaps
- **1 isolated node(s):** `varedura`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1019 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **122 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `t` to `stalker.py`, `test_textual_app.py`, `._accept_ping_result`, `load_network_config`, `main`, `CamerasMixin`, `PingStats`, `prompt_export_report`, `credenciais.py`, `PlansMixin`, `.log`, `PingTarget`, `shutil`, `._browse_arquivo`, `resolver_ip`, `.compact_vhdx_files`, `textual_app.py`, `test_android_adaptations.py`, `regioes.py`, `handle_key`, `textual_plans.py`, `t`, `datetime`, `TermuxMixin`, `TargetPickerScreen`, `DailyLogWriter`, `core.py`, `TermuxKeysMixin`, `VareduraTextualApp`, `quick_cleanup`, `test_layout.py`, `._compose_dashboard`, `log.py`, `json`, `._render_ports_table`, `shutil`, `._importar_credenciais`, `._compose_cameras`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `VareduraTextualApp` (e.g. with `test_background_switch_in_settings_drives_the_scheduler()` and `test_settings_saves_auto_speed_interval()`) actually correct?**
  _`VareduraTextualApp` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `varedura` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `t` be split into smaller, more focused modules?**
  _Cohesion score 0.11576354679802955 - nodes in this community are weakly interconnected._
- **Why does `VareduraTextualApp` connect `VareduraTextualApp` to `t`, `test_textual_app.py`, `._accept_ping_result`, `load_network_config`, `re`, `CamerasMixin`, `ContinuousSpeedTester`, `PlansMixin`, `PingTarget`, `run_textual_app`, `textual_app.py`, `.on_main_tab_activated`, `stop_continuous_testing`, `termux_env.py`, `t`, `TermuxMixin`, `TargetPickerScreen`, `test_auto_speed.py`, `test_textual_cameras.py`, `DailyLogWriter`, `TermuxKeysMixin`, `test_layout.py`, `._compose_dashboard`, `json`, `._render_ports_table`, `test_textual_termux.py`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WSLDockerCleaner` (e.g. with `DailyLogWriter` and `docker_full_cleanup()`) actually correct?**
  _`WSLDockerCleaner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `stalker.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07635467980295567 - nodes in this community are weakly interconnected._