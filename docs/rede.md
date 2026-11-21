# Rede: Monitoramento, Diagnóstico, Reparos e Speedtest — Varedura

O pacote `monitor/` concentra todo o núcleo de observabilidade e correção de rede local e internet. Nenhum módulo de `monitor/` deve disparar I/O no `import` (contrato verificado em [tests/test_startup_lazy.py](../tests/test_startup_lazy.py)).

---

## 1. Arquitetura do subsistema `monitor/`

| Módulo | Papel | Símbolos-chave |
|---|---|---|
| `monitor/ping_targets.py` | Catálogo oficial, validação de IP/hostname e primitivas de probe ICMP | `NETWORK_SCHEMA_VERSION = 3`, `MAX_PERSISTENT_TARGETS = 5`, `TargetSelection`, `validate_host`, `target_catalog`, `probe_ping` |
| `monitor/ping_scheduler.py` | Escalonador justo com backoff (`_FAST_BACKOFF`, `_SECONDARY_BACKOFF`) e limite de 3 probes simultâneos | `PingScheduler`, `TargetRole`, `SchedulerTargetSnapshot`, `MAX_CONCURRENT_PROBES = 3` |
| `monitor/netinfo.py` | Detecção multiplataforma do gateway padrão (sem I/O ao importar) | `detect_default_gateway` |
| `monitor/network_history.py` | Histórico thread-safe por alvo (`max_records=50_000`), exportação CSV/PDF e mascaramento IPv4 `/24` / IPv6 `/64` | `NetworkSessionHistory`, `NetworkHistoryRecord`, `mask_ip`, `summarize_latencies` |
| `monitor/stalker.py` *(3.029L)* | Runner contínuo ICMP (`StalkerConfig`), análise de causa de lag, dashboard Rich standalone e gerador de PDF formal estilo ANATEL | `StalkerConfig`, `PingStats`, `ContractInfo`, `run_ping`, `analyze_lag_source`, `export_combined_report` |
| `monitor/network_diagnostics.py` *(2.226L)* | Coleta snapshot de interfaces/rotas/DNS/DHCP/proxy, executa probes (Link, Route, DNS, TCP, Captive Portal, HTTPS, ICMP) e classifica causa raiz | `NetworkDiagnosticEngine`, `SnapshotCollector`, `SystemProbeBackend`, `classify_diagnosis`, `NetworkState`, `FailureCause` |
| `monitor/network_repairs.py` *(1.737L)* | Lista e executa reparos conservadores/confirmados (DNS flush, DHCP renew, reconexão, Wi-Fi, CA do app) + guias não-executáveis para resets arriscados | `RepairKind`, `RepairAction`, `RepairGuidance`, `RepairExecutor`, `list_repair_actions`, `list_repair_guidance` |
| `monitor/port_scanner.py` + `monitor/port_catalog.py` | Enumeração TCP/UDP listening, top processos por conexões e mapeamento para chaves i18n amigáveis | `run_full_scan`, `get_listening_ports`, `get_process_connections_count`, `describe_port`, `classify_exposure` |
| `monitor/speed_tester.py` + `speed_providers.py` + `speed_worker.py` | Teste contínuo/único de velocidade + conformidade ANATEL (≥ 80% contratado) + fallback multi-provedor (Speedtest.net, Fast.com, Brasil Banda Larga, SIMET) | `ContinuousSpeedTester`, `MultiProviderSpeedTester`, `SpeedtestNetProvider`, `FastComProvider`, `BrasilBandaLargaProvider`, `SimetProvider`, `run_provider` |
| `monitor/league_detector.py` | Detecção passiva de partida ativa de League of Legends via Live Client API (`127.0.0.1:2999`) + leitura de sockets UDP existentes (sem enviar pacotes ao jogo) | `LeagueMatchDetector`, `LeagueDetectorState`, `LeagueEndpoint`, `mask_endpoint_ip` |

---

## 2. Fluxo Diagnóstico → Reparo

1. `SnapshotCollector.collect()` reúne interfaces ativas, rota padrão, servidores DNS/DHCP, proxy explícito/PAC e flags de ambiente sem expor credenciais (`_redact_text`).
2. `NetworkDiagnosticEngine.diagnose()` roda probes ordenados e chama `classify_diagnosis()` para produzir um `DiagnosisReport` com `NetworkState` (`ONLINE`, `LIMITED`, `LOCAL_ONLY`, `CAPTIVE_PORTAL`, `PROXY_AUTH_REQUIRED`, `POLICY_BLOCKED`, `TLS_POLICY_BLOCKED`, `OFFLINE`, etc.) e `FailureCause`.
3. `list_repair_actions(report)` gera apenas ações seguras/reversíveis (`RepairKind`: `REFRESH_STATUS`, `OPEN_CAPTIVE_PORTAL`, `FLUSH_DNS`, `RENEW_DHCP`, `RECONNECT_INTERFACE`, `ENABLE_WIFI`, `CONFIGURE_APP_CA`).
4. Antes de executar via `RepairExecutor`, a TUI exibe `RepairConfirmationScreen` (`cli/network_ui.py`) e o executor reconstrói os comandos a partir do diagnóstico recente para impedir injeção de comandos arbitrários.

---

## 3. Índices de faixas de linha (arquivos > 1.300 linhas)

### `monitor/stalker.py` (3.029 linhas)
- `L52-133`: `StalkerConfig`, `PingStats`, `ContractInfo`
- `L151-253`: histórico de amostras (`record_ping_sample`), preferências (`save_prefs`/`load_prefs` em `exports/stalker_prefs.json`), `get_ping_command`, `parse_ping`, `run_ping`
- `L256-411`: consumo por processo (`get_top_network_hogs`) e diagnóstico de lag (`analyze_lag_source`)
- `L420-683`: teclado standalone e prompts interativos (gateway, alvo externo, threshold, exportação)
- `L691-2314`: **gerador de PDF formal ANATEL** (`_generate_combined_pdf_worker` L691-2270, `export_combined_report` L2273-2301, `get_export_status` L2304-2314)
- `L2318-3022`: painéis Rich standalone (`make_ascii_graph`, `make_*_panel`) e `main()`

### `monitor/network_diagnostics.py` (2.226 linhas)
- `L41-257`: enums (`NetworkState`, `Confidence`, `ProbeKind`, `ProbeStatus`, `FailureCause`) e modelos (`NetworkSnapshot`, `ProbeResult`, `DiagnosisReport`, `DiagnosticOptions`, `CommandResult`)
- `L260-374`: `CommandRunner`, `_terminate_process`, `SubprocessCommandRunner`
- `L388-995`: redação/sanitização, parsers de rotas/DNS/DHCP/proxy para Windows, Linux e macOS
- `L998-1250`: `SnapshotCollector.collect()`
- `L1254-1456`: `ProbeBackend`, `SystemProbeBackend` (DNS/TCP/HTTPS/Captive Portal/ICMP) e `DiagnosticCancelled`
- `L1474-1797`: `_local_probes`, `_evidence_for_snapshot` e `classify_diagnosis()`
- `L1800-2196`: `NetworkDiagnosticEngine.diagnose()`, `collect_network_snapshot()`, `run_network_diagnosis()`

### `monitor/network_repairs.py` (1.737 linhas)
- `L43-121`: enums (`RepairKind`, `RepairImpact`, `RepairStatus`) e modelos (`RepairAction`, `RepairGuidance`, `RepairResult`, `RepairRunner`)
- `L164-645`: utilitários Windows/UAC (`_windows_elevated_script`), `_kill_process`, `SubprocessRepairRunner`
- `L648-1022`: pré-visualizações seguras, `list_repair_actions()` e `list_repair_guidance()`
- `L1025-1173`: validação DER/PEM e armazenamento de CA em `~/.varedura/certs/` (`_validate_app_ca`, `_store_app_ca`)
- `L1176-1723`: `RepairExecutor` (`_execute_flush`, `_execute_renew`, `_execute_reconnect`, `_execute_wifi`, `execute()`)
