# AGENTS.md — Varedura (mapa para agentes)

Toolkit multiplataforma (Python ≥ 3.14.2, desktop + Android/Termux) para manutenção Docker/WSL2, monitoramento/diagnóstico/reparo de rede, descoberta e ponte sanitizada de câmeras IP (`rtsp/`, `varedura-camera-bridge`) com visão AI (`varedura/ai_vision/`), auto-atualização Git (`varedura-update`) e servidor MCP (`mcp_server/`).

## 0. Como analisar barato (leia primeiro)

1. Pergunta sobre código → `graphify query "<pergunta>" --budget 800` (ou MCP `query_graph`). Relações: `graphify path "A" "B"`; conceito: `graphify explain "X"`; impacto reverso: `graphify affected "X"`.
2. Navegação ampla → `graphify-out/wiki/index.md`. Evite ler `graphify-out/GRAPH_REPORT.md` inteiro ou `graphify-out/graph.json` bruto.
3. Consulte §2 e §3 abaixo antes de abrir código. Nos arquivos grandes (`monitor/stalker.py`, `cli/textual_app.py`, `monitor/network_diagnostics.py`, `docker_cleaner/core.py`, `varedura/camera_bridge.py`, `monitor/network_repairs.py`, `cli/textual_cameras.py`), use os índices de faixas de linhas em `docs/` e leia apenas com `StartLine`/`EndLine`.
4. Guias detalhados por área (leia só o relevante): [docs/arquitetura.md](docs/arquitetura.md) · [docs/manutencao.md](docs/manutencao.md) · [docs/como-adicionar-recursos.md](docs/como-adicionar-recursos.md) · [docs/docker-e-cli.md](docs/docker-e-cli.md) · [docs/rede.md](docs/rede.md) · [docs/cameras-e-ia.md](docs/cameras-e-ia.md) · [docs/termux.md](docs/termux.md) · [docs/mcp.md](docs/mcp.md).
5. **Não leia** (ruído, binário, gerado ou privado): `todos_ips_belem.txt` (602 KB), `runtime/`, `screenshots/`, `exports/`, `logs/`, `lmarena/`, `docs/arquivo/`, `graphify-out/graph.json`, `uv.lock`, e arquivos privados (`credenciais.json`, `ips_conhecidos.json`, `regioes.json`, `camera_bridge_state.json`, `.camera-locations.private.json`, `roteador_creds.txt`, `router_template.html`, `tests/arp.py`, `tests/router_phishing.py`).
6. Sempre pesquise a documentação via MCP (e internet se necessário) antes de usar qualquer biblioteca externa nova.
7. Após alterar código, execute `graphify update .` (AST-only, sem custo de API) — e `graphify export wiki` se a estrutura mudar bastante.

## 1. Arquitetura em uma tela

```
                    ┌──► TUI Textual (cli/textual_app.py + CamerasMixin)
                    │      ├── dashboard, docker (condicional via should_show_docker_tab()),
main.py (lazy) ─────┤      │   network, cameras, termux, settings + captura SVG nativa
                    └──► CLIs headless (cli/quick_cleanup.py, cli/main_cleaner.py,
                           cli/admin_tasks.py, varedura-update)

docker_cleaner/core.py (WSLDockerCleaner sync/async) ◄──────┐
monitor/* (stalker, diagnostics, repairs, ports, speed,     ├──► mcp_server/server.py (FastMCP stdio)
           network_health, lol)                             │
rtsp/* (camera_engine, scanner, xiongmai NetIP/P2P, video) ─┼──► varedura/camera_bridge.py (Mural sanitizado)
                                                            ├──► varedura/ai_vision/ (YOLONanoDetector + regras)
varedura/termux_env.py (telemetria, hub, Termux:API) ───────┼──► aba Termux & notificações/share na TUI
varedura/updater.py (git auth + cooldown 6h + cron) ────────┘
```

## 2. Mapa de módulos

| Arquivo | Papel | Símbolos-chave |
|---|---|---|
| `main.py` | Despachante leve sem imports pesados que inicia `run_textual_app()` | `main` |
| `docker_cleaner/core.py` *(1.946L — índice em `docs/docker-e-cli.md`)* | Motor Docker/WSL2 sync + async, UAC/elevação, VHDX sparse/`Optimize-VHD` | `WSLDockerCleaner`, `CleanupStepResult`, `DOCKER_CLEANUP_COMMANDS`, `get_docker_vhdx_paths` |
| `cli/textual_app.py` *(índice em `docs/docker-e-cli.md`)* | App Textual principal (abas: `dashboard`, `docker` condicional, `network`, `cameras`, `termux`, `settings` + captura SVG nativa) | `VareduraTextualApp`, `TargetPingCard`, `ShutdownScreen`, `run_textual_app` |
| `cli/textual_cameras.py` *(índice em `docs/docker-e-cli.md`)* | Aba Câmeras (4 sub-abas), workers, radar, snapshot JPEG e `mpv --vo=tct` | `CamerasMixin`, `ClickOpenDataTable` |
| `cli/layout.py` | Régua única de breakpoints da TUI (estreito < 76, médio, largo ≥ 112 colunas) e colunas de cada grade; a faixa estreita liga o modo compacto (`Screen.mobile-narrow`: botões de 1 linha, cards de ping em 2 linhas) | `layout_tier`, `columns_for`, `GRID_COLUMNS` |
| `cli/theme.py` | Tema próprio (`varedura-dark`/`varedura-light`); a tecla `d` alterna e a escolha fica em `dark_theme` nas prefs. Não use cores fixas (`white`, hex) em renderables: herde do tema | `THEMES`, `theme_name` |
| `cli/textual_termux_keys.py` | Termux: macros das teclas extras viram ações, tecla ⌨ temporária na barra `extra-keys` e digitação por `termux-dialog` (detalhes em `docs/termux.md` §7) | `TermuxKeysMixin` |
| `cli/network_ui.py` | Modais lazy de seleção de alvos e confirmação de reparos | `TargetPickerScreen`, `RepairConfirmationScreen`, `merge_visible_selection` |
| `cli/ui_shared.py` / `cli/richlog.py` | Prefs (`~/.varedura_prefs.json`), presets de limpeza, logs diários e painéis Rich | `CLEANUP_STEPS`, `load_network_config`, `DailyLogWriter`, `format_duration` |
| `cli/quick_cleanup.py` / `cli/main_cleaner.py` / `cli/admin_tasks.py` | CLIs headless e executor elevado (`compact_vhdx`, `configure_sparse`) | `quick_cleanup`, `parse_args`, `main` |
| `monitor/stalker.py` *(índice em `docs/rede.md`)* | Monitor ICMP contínuo, análise de lag, exportador PDF formal estilo ANATEL | `StalkerConfig`, `PingStats`, `run_ping`, `analyze_lag_source`, `export_combined_report` |
| `monitor/network_diagnostics.py` *(índice em `docs/rede.md`)* | Coleta de snapshot, probes HTTP/DNS/rota/proxy e classificação de causas | `NetworkDiagnosticEngine`, `SnapshotCollector`, `SystemProbeBackend`, `classify_diagnosis` |
| `monitor/network_repairs.py` *(índice em `docs/rede.md`)* | Ações conservadoras e confirmadas (DNS, DHCP, reconexão, Wi-Fi, CA) | `RepairKind`, `RepairAction`, `RepairExecutor`, `list_repair_actions` |
| `monitor/network_health.py` | Cálculo puro do score de saúde (0–100, tiers `S`–`F`) | `compute_health_score` |
| `monitor/ping_targets.py` / `monitor/ping_scheduler.py` / `monitor/netinfo.py` | Catálogo/validação de alvos, escalonador com backoff (máx. 3 probes), gateway padrão (desktop + Android/Termux) | `TargetSelection`, `validate_host`, `PingScheduler`, `detect_default_gateway` |
| `monitor/network_history.py` / `monitor/league_detector.py` | Histórico thread-safe por alvo (CSV/PDF, mascaramento `/24`/`/64`) e detecção LoL | `NetworkSessionHistory`, `mask_ip`, `LeagueMatchDetector`, `LeagueEndpoint` |
| `monitor/port_scanner.py` / `monitor/port_catalog.py` | Portas TCP/UDP em listening, conexões por processo, rótulos i18n amigáveis | `run_full_scan`, `get_listening_ports`, `describe_port`, `classify_exposure` |
| `monitor/plan_profiles.py` / `monitor/data_usage.py` / `cli/textual_plans.py` | Perfis de plano (fixo/móvel) escolhidos pela rede ativa, franquia por ciclo, histórico de velocidade persistente e formulário de planos na TUI (detalhes em `docs/rede.md` §4) | `PlanProfile`, `select_profile`, `apply_profile`, `DataUsageTracker`, `samples_for_report`, `PlansMixin` |
| `monitor/speed_tester.py` / `monitor/speed_providers.py` / `monitor/speed_providers_http.py` / `monitor/speed_worker.py` / `monitor/auto_speed.py` | Speedtest contínuo + multi-provedor (Speedtest.net, Fast.com, Cloudflare, M-Lab NDT7, BBL, SIMET) e teste automático agendado (`varedura-speedtest`, detalhes em `docs/rede.md` §5) | `ContinuousSpeedTester`, `MultiProviderSpeedTester`, `SpeedTestProvider`, `run_provider` |
| `varedura/termux_env.py` | Ambiente Termux/Android, visibilidade condicional da aba Docker, descoberta de ferramentas/Claro, telemetria, serviços e Termux:API | `is_termux`, `is_android`, `should_show_docker_tab`, `discover_termux_tools`, `collect_android_telemetry`, `list_termux_services`, `toggle_termux_service`, `send_termux_notification`, `share_file` |
| `varedura/updater.py` | Auto-atualização GitHub autenticada (`GHG_TOKEN`/`~/.varedura_gh_token`), cooldown 6h, cron e CLI `varedura-update` | `UpdateResult`, `resolve_github_token`, `save_token_file`, `get_repo_status`, `update_repository`, `is_cron_update_enabled`, `set_cron_update_enabled`, `main` |
| `varedura/camera_bridge.py` *(1.862L — índice em `docs/cameras-e-ia.md`)* | Ponte local sanitizada de câmeras para o Mural (snapshots, HLS, inbox atômico, leases) | `CameraBridge`, `FFmpegRunner`, `LocationStore`, `IdentityStore`, `build_parser` |
| `varedura/ai_vision/{detector,rules,stream_processor}.py` | YOLO ONNX + fallback, NMS/IoU tracker, tripwire/zona/loitering, heatmap 32×32 | `YOLONanoDetector`, `LineCrossingRule`, `ZoneIntrusionRule`, `LoiteringRule`, `AIStreamProcessor` |
| `rtsp/{camera_engine,scanner,xiongmai,video}.py` | Motor unificado (RTSP/iCSee/P2P/ONVIF), scanner stdlib, NetIP :34567/Sofia P2P, FFmpeg + players Android (`vlc-android`, `termux-open`, `mpv-tct`) | `CameraFleetManager`, `UnifiedCameraSource`, `escanear_rede`, `XiongmaiNetIPClient`, `validar_stream`, `capturar_e_abrir_snapshot` |
| `rtsp/{credenciais,regioes,rede,paths,geo,mapa,log,amostra_ips_belem}.py` | Vault/IPs conhecidos, regiões, detecção LAN, paths por fabricante, geo/mapa ASCII, log redator | `carregar_vault`, `carregar_regioes`, `detectar_redes`, `CAMINHOS_RTSP`, `redact_sensitive` |
| `mcp_server/server.py` | Servidor FastMCP (stdio) com 5 ferramentas e confirmação obrigatória em limpeza | `docker_status`, `docker_quick_cleanup`, `docker_full_cleanup`, `port_scan`, `get_logs` |
| `i18n/` | Traduções sincronizadas `pt`/`en` (verificadas por `tests/test_i18n_parity.py`) | `t`, `init`, `set_language`, `get_language` |
| `scripts/termux_install.sh` / `scripts/sync_termux_adb.ps1` | Instalador ARM64 idempotente no Termux (`--replace-menu`) e sync PC → Termux via ADB+SSH | — |

## 3. Onde mudar X

| Quero… | Arquivos |
|---|---|
| Nova etapa de limpeza Docker/WSL | `docker_cleaner/core.py` (sync + async + `DOCKER_CLEANUP_COMMANDS`), `cli/ui_shared.py`, `cli/textual_app.py`, `i18n/{pt,en}.json`, `tests/test_docker_cleanup.py` |
| Nova aba, modal ou atalho na TUI | `cli/textual_app.py` (`compose`, `BINDINGS`, `@work`), `cli/layout.py` (nunca crie limites de largura avulsos; use `columns_for`/`layout_tier`), `cli/network_ui.py`, `i18n/{pt,en}.json`, `tests/test_textual_app.py` |
| Novo alvo de ping, diagnóstico ou reparo | `monitor/ping_targets.py`, `monitor/network_diagnostics.py`, `monitor/network_repairs.py` (`RepairAction` + `RepairExecutor`), `tests/` |
| Plano contratado, franquia ou laudo PDF | `monitor/plan_profiles.py`, `monitor/data_usage.py`, `cli/textual_plans.py`, `monitor/stalker.py` (`set_contract`, `_generate_combined_pdf_worker`), `i18n/{pt,en}.json`, `tests/test_plan_profiles.py`, `tests/test_data_usage.py` |
| Novo provedor de speedtest | `monitor/speed_providers.py` ou `monitor/speed_providers_http.py` (`SpeedTestProvider`), `monitor/speed_worker.py` (`PROVIDER_IDS`), `monitor/speed_tester.py` (`_available_provider_ids`), `tests/test_speed_cleanup.py` |
| Integração Termux / auto-updater | `varedura/termux_env.py`, `varedura/updater.py`, `scripts/termux_install.sh`, `scripts/sync_termux_adb.ps1`, `docs/termux.md`, `tests/test_termux_env.py`, `tests/test_updater.py` |
| Nova ferramenta MCP | `mcp_server/server.py` (`@mcp.tool()`, exigir `confirmed`/`dry_run` se destrutiva), `docs/mcp.md` |
| Protocolo/descoberta de câmera ou ponte do Mural | `rtsp/camera_engine.py`, `rtsp/xiongmai.py`, `rtsp/scanner.py`, `varedura/camera_bridge.py`, `tests/` |
| Nova regra de visão AI | `varedura/ai_vision/rules.py` (`GeometricRule`), `varedura/ai_vision/stream_processor.py`, `tests/test_ai_vision.py` |

## 4. Invariantes (não quebrar)

- **Ferramenta global editable (`uv tool`)**: instalado via `uv tool install --editable ".[browser-speedtest]"`. Sempre que `pyproject.toml` mudar dependências, extras ou scripts, execute `uv tool upgrade varedura`. Nunca use `python`/`pip` nus no desktop; use `uv run ...` e mantenha o extra `browser-speedtest` (`selenium`).
- **Startup lazy (`tests/test_startup_lazy.py`)**: `import main` não pode importar `rich`, `textual`, `monitor.*`, `requests`, `selenium`, `PIL` ou `rtsp.scanner`; `import cli.textual_app` e o 1º frame do `VareduraTextualApp` não fazem I/O externo nem carregam backends pesados; `varedura/termux_env.py` e `varedura/updater.py` mantêm apenas imports stdlib sem I/O no import; `get_speed_tester()` ocioso não instancia provedores.
- **Segurança & elevação**: nunca contorne UAC (`is_admin()`/`run_as_admin()`) nem execute operações destrutivas (`docker system prune`, `taskkill /F`, `wsl --shutdown`, `Optimize-VHD`) sem confirmação explícita; em testes, sempre mocke `subprocess` e `ctypes`.
- **Segurança do updater (`varedura/updater.py`)**: nunca grave tokens GitHub (`GHG_TOKEN`/`GH_TOKEN`/`GITHUB_TOKEN` ou `~/.varedura_gh_token`) em `.git/config`, scripts temporários persistentes ou logs; use `GIT_ASKPASS` efêmero via env e redija segredos na saída.
- **Guardrails do MCP (`mcp_server/server.py`)**: `docker_quick_cleanup` e `docker_full_cleanup` não executam sem `confirmed=True` e devem preservar `dry_run=True`.
- **Sanitização da Camera Bridge (`varedura/camera_bridge.py`)**: único processo que conhece URLs RTSP e credenciais; a pasta de saída só recebe IDs opacos, estados enumerados e mídia derivada (`LocationStore` grava `.camera-locations.private.json` dentro de `--output-dir`); comandos via inbox nunca aceitam URLs ou caminhos arbitrários.
- **Privacidade do grafo (`tests/test_graphify_privacy.py`)**: arquivos privados (`credenciais.json`, `ips_conhecidos.json`, `regioes.json`, `camera_bridge_state.json`, `.camera-locations.private.json`, `roteador_creds.txt`) nunca podem entrar em `graphify-out/graph.json`.
- **Verificação visual autêntica**: proibido usar `dummyimage.com` ou placeholders sintéticos; use feeds reais em `runtime/cctv_samples/` e capturas SVG nativas da TUI Textual em `screenshots/`.
- **i18n (`tests/test_i18n_parity.py`)**: mantenha chaves e placeholders 100% sincronizados entre `i18n/pt.json` e `i18n/en.json` (preferência persistida em `~/.varedura_lang.json`).

## 5. Comandos canônicos

```powershell
uv run main.py                                    # TUI Textual (padrão)
varedura                                          # Binário global (editable)
varedura-update --status                          # Status do repositório e auto-updater
varedura-speedtest --status                       # Teste de velocidade automático (--once, --cron-on, --windows-task)
uv run python -m mcp_server                       # Servidor MCP stdio
varedura-camera-bridge --output-dir <dir>         # Ponte sanitizada para o Mural
.\scripts\sync_termux_adb.ps1 -Install            # Sincroniza e instala no Termux via ADB+SSH
uv run pytest -q                                  # Suíte Python
uv run ruff check .                               # Lint obrigatório no CI
graphify update .                                 # Atualiza grafo AST após editar código
```

## 6. Armadilhas conhecidas

- `pyproject.toml` declara `[build-system]` (`setuptools>=68.0`), portanto `uv sync` gera os scripts `[project.scripts]` (`varedura`, `varedura-camera-bridge`, `varedura-update`, `varedura-speedtest`) dentro do `.venv`; após mudar `pyproject.toml`, execute `uv tool upgrade varedura` para atualizar os binários globais.
- No CI, `ruff check .` é bloqueante e `ruff format --check .` é informativo (`continue-on-error: true`).
- `selenium` (`browser-speedtest`) é opcional: sem ele, `BrasilBandaLargaProvider` e `SimetProvider` retornam `is_available() == False` e fazem fallback HTTP; no Termux ARM64 o Selenium não é instalado.
- `should_show_docker_tab()` oculta a aba `docker` no Android/Termux quando o binário `docker` não está disponível (salvo se `VAREDURA_SHOW_DOCKER=1`).
- `[tool.uv]` contém override de `pywin32>=999` no Windows por compatibilidade com Python 3.14 free-threaded (`cp314t`).

## graphify

This project has a knowledge graph at `graphify-out/` with community wiki articles at `graphify-out/wiki/index.md`.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` (or `query_graph` via MCP). Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- Dirty `graphify-out/` files are expected after hooks or incremental updates; only skip graphify if the task is specifically about stale/broken graph output or the user asks not to use it.
- Prefer `graphify-out/wiki/index.md` for broad navigation instead of reading `GRAPH_REPORT.md` or raw source files upfront.
- After modifying code files, run `graphify update .` (AST-only, no API cost).
