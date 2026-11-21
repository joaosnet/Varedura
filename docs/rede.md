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

### `monitor/stalker.py` (3344 linhas)
- `L52-190`: `StalkerConfig`, `PingStats`, `ContractInfo` (preenchido por `set_contract()` a partir do perfil ativo), `set_report_context()`
- `L151-253`: histórico de amostras (`record_ping_sample`), preferências (`save_prefs`/`load_prefs` em `exports/stalker_prefs.json`), `get_ping_command`, `parse_ping`, `run_ping`
- `L256-411`: consumo por processo (`get_top_network_hogs`) e diagnóstico de lag (`analyze_lag_source`)
- `L420-683`: teclado standalone e prompts interativos (gateway, alvo externo, threshold, exportação)
- `L744-2639`: **gerador do laudo PDF do consumidor** (páginas extras `_draw_text_page`/`_quota_lines` a partir de L744, `_generate_combined_pdf_worker` L844, `export_combined_report` L2577, `get_last_export_path`, `get_export_status`)
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

---

## 4. Planos de internet, franquia e laudo PDF

O que foi contratado deixa de ser fixo no código: vem de **perfis de plano** em `~/.varedura_prefs.json` (`network.plan_profiles`, schema v4), editados em **Configurações → Planos de internet**.

| Módulo | Papel |
|---|---|
| `monitor/plan_profiles.py` | Dados puros: `PlanProfile` (fixo/móvel, velocidade de referência, franquia, ciclo, rede associada), `select_profile()`, `evaluate_speed()`, `quota_status()`, `apply_profile()` (único ponto que escreve em `speed_config` e `stalker.contract_info`) |
| `monitor/netinfo.py::detect_active_network()` | Tipo de rede (Wi-Fi, dados móveis, cabo), SSID e gateway. Android: `ip route get` + `termux-wifi-connectioninfo`; Windows: `netsh wlan show interfaces` |
| `monitor/data_usage.py` | `DataUsageTracker` (consumo por ciclo em `~/.varedura_usage.json`) e histórico de velocidade em `~/.varedura_speed_history.jsonl` |
| `cli/textual_plans.py` | `PlansMixin`: formulário, plano ativo, linha de status na aba Rede e no Painel |

**Escolha do plano**: manual (Configurações → "Plano em uso") > SSID > gateway > tipo de rede > único plano fixo. Dados móveis nunca são conferidos contra um plano fixo, e um plano móvel nunca é aplicado em Wi-Fi. Sem permissão de localização o Android devolve `<unknown ssid>`; nesse caso a associação cai para o gateway.

**Franquia**: o Android só expõe contadores desde o boot (`rmnet*`/`ccmni*` em `/proc/net/dev`). O rastreador soma deltas e reinicia a base quando o contador regride. O tráfego entre a última leitura e um reboot não é contado — o campo "Já consumido (GB)" serve para acertar com o extrato da operadora. Fora do Android não há medição de franquia.

**Laudo PDF** (botão "Exportar PDF" da aba Rede → `export_combined_report()`): documento **do consumidor**, não da ANATEL. Usa as medições de velocidade do plano ativo no ciclo vigente (ou últimos 30 dias). Os limiares de 80 % (média) e 40 % (instantânea) vêm dos antigos indicadores SCM4/SCM5 da Res. 574/2011, **revogados pelo RQUAL (Res. 717/2019)**: aparecem como "referência", e os vereditos são "dentro/abaixo da referência". Plano sem velocidade informada sai como "velocidade medida (sem referência)". Plano móvel com franquia ganha a seção "Franquia de dados".

---

## 5. Provedores de velocidade e teste automático

| Provedor | Id do worker | Como mede | Onde roda |
|---|---|---|---|
| Speedtest.net | `speedtest` | `speedtest-cli` | Todas as plataformas |
| Fast.com | `fast` | HTTP; download e **upload reais** (o upload já foi estimado em 40 % do download — removido) | Todas |
| Cloudflare | `cloudflare` | HTTP em `speed.cloudflare.com`, 4 fluxos de download e 3 de upload | Todas |
| M-Lab NDT7 | `mlab` | WebSocket (cliente mínimo em stdlib), 1 fluxo TCP por sentido, servidores da RNP | Todas |
| Brasil Banda Larga / SIMET | `brasil_banda_larga` / `simet` | Selenium | Só desktop com o extra `browser-speedtest` |

Cloudflare e M-Lab ficam em `monitor/speed_providers_http.py`. O LibreSpeed foi avaliado e descartado: a lista pública não tem servidor no Brasil, então mediria a rota internacional. Upload `0` significa "não medido" e fica fora de médias e vereditos.

**Teste automático** (`monitor/auto_speed.py`, comando `varedura-speedtest`): com `auto_speed_minutes > 0` (Configurações → "Teste de velocidade automático", mínimo 15 min), um teste roda a cada intervalo, em rodízio de provedores, e a medição entra no histórico do plano ativo — a fonte do laudo PDF.

- **App aberto**: `PlansMixin._auto_speed_tick` confere a cada minuto.
- **Segundo plano**: o interruptor "Também com o app fechado" (mesma seção de Configurações) chama `set_background_enabled()`. No Windows ele cria/remove a tarefa "Varedura Speedtest" do usuário atual no Agendador (`schtasks`, sem elevação, via `pythonw` para não abrir janela); no Termux/Linux instala `*/15 * * * * varedura-speedtest --scheduled` no cron (requer o serviço `crond` ligado). Em ambos o comando só mede se o intervalo venceu. A linha de situação logo abaixo mostra intervalo, segundo plano e último teste — não é preciso usar o CLI.
- O estado em `~/.varedura_auto_speed.json` é compartilhado, então app e cron não rodam em dobro. Falha tenta de novo em 15 min.
- **Nunca** roda em dados móveis nem sem rede identificada, mesmo com `--once`.

