# Arquitetura — Varedura

O Varedura evoluiu de uma ferramenta de limpeza Docker/WSL2 para um workspace multiplataforma em Python (≥ 3.14.2, desktop Windows/Linux/macOS + Android/Termux) composto por subsistemas desacoplados que compartilham os mesmos núcleos de execução.

---

## 1. Visão geral dos subsistemas

```
                       ┌──► TUI Textual (cli/textual_app.py + cli/textual_cameras.py)
                       │      └── abas: dashboard, docker (condicional), network, cameras, termux, settings
main.py (lazy) ────────┤      └── captura de tela SVG nativa em screenshots/
                       └──► CLIs headless (cli.quick_cleanup, cli.main_cleaner, cli.admin_tasks, varedura-update)

Núcleos compartilhados:
  ├── docker_cleaner/core.py   ──► Limpeza Docker, WSL sparse, compactação VHDX (Windows UAC / sudo)
  ├── monitor/*                ──► Ping multi-alvo, diagnóstico, reparos, portas, speedtest, network_health, LoL, PDF ANATEL
  ├── rtsp/*                   ──► Descoberta RTSP/ONVIF/Xiongmai NetIP (:34567) / Sofia P2P + FFmpeg / Android players
  ├── varedura/ai_vision/*     ──► YOLONanoDetector (ONNX) + tracker IoU + regras espaciais + heatmap
  ├── varedura/termux_env.py   ──► Detecção Android/Termux, visibilidade Docker condicional, telemetria, hub & Termux:API
  ├── varedura/updater.py      ──► Self-updater Git autenticado (GIT_ASKPASS efêmero), cooldown 6h e cron
  │
  ├──► mcp_server/server.py    ──► Servidor FastMCP (stdio) com trava confirmed/dry_run para agentes IA
  └──► varedura/camera_bridge.py ──► Ponte sanitizada (snapshots + HLS + inbox) -> Mural dos Sonhos
```

---

## 2. Startup lazy (`main.py` → `cli/`)

O ponto de entrada `main.py` é mantido intencionalmente livre de imports pesados (`rich`, `textual`, `monitor.*`, `requests`, `selenium`, `PIL`, `rtsp.scanner`). Esse contrato é validado automaticamente por [tests/test_startup_lazy.py](../tests/test_startup_lazy.py):

1. `import main` não carrega `rich`, `textual`, `monitor.*`, `requests`, `selenium`, `PIL` ou `rtsp.scanner`.
2. `import cli.textual_app` carrega o shell Textual, mas adia `monitor.speed_providers`, `requests`, `selenium`, `PIL` e `rtsp.scanner`.
3. `varedura/termux_env.py` e `varedura/updater.py` utilizam apenas biblioteca padrão no `import` e não executam subprocessos nem I/O de rede ao serem importados.
4. `VareduraTextualApp.compose()` renderiza o `dashboard` de imediato; abas secundárias usam hidratação sob demanda (`_hydrate_tab`), e a aba `docker` é omitida no Android/Termux quando `should_show_docker_tab()` retorna `False` (sem binário `docker` nem `VAREDURA_SHOW_DOCKER=1`).
5. O primeiro frame do `VareduraTextualApp` não abre sockets, DNS, `subprocess` nem HTTP.
6. Os submódulos de câmera em `rtsp/` só são importados na aba `cameras` via `_load_camera_backend()` em [cli/textual_cameras.py](../cli/textual_cameras.py).

---

## 3. Pontos de entrada

| Comando / Módulo | Uso | Guia |
|---|---|---|
| `varedura` ou `uv run main.py` | TUI Textual única (desktop + Termux nativo) | [docs/docker-e-cli.md](docker-e-cli.md) |
| `varedura-update` ou `uv run python -m varedura.updater` | Auto-atualização Git (`--check`, `--force`, `--set-token`, `--cron-on/off`, `--status`) | [docs/termux.md](termux.md) |
| `uv run python -m cli.quick_cleanup` | Limpeza rápida Docker + shutdown WSL + VHDX sem TUI | [docs/docker-e-cli.md](docker-e-cli.md) |
| `uv run python -m cli.main_cleaner` | Executor CLI do `WSLDockerCleaner` (`docker_cleaner/core.py`) | [docs/docker-e-cli.md](docker-e-cli.md) |
| `uv run python -m cli.admin_tasks <compact_vhdx\|configure_sparse>` | Helper elevado via UAC (`runas`) no Windows | [docs/docker-e-cli.md](docker-e-cli.md) |
| `varedura-camera-bridge --output-dir <dir>` | Ponte local sanitizada de câmeras para o Mural dos Sonhos | [docs/cameras-e-ia.md](cameras-e-ia.md) |
| `uv run python -m mcp_server` | Servidor FastMCP em transporte `stdio` | [docs/mcp.md](mcp.md) |
| `uv run python -m monitor.speed_worker` | Worker isolado de provedor de speedtest | [docs/rede.md](rede.md) |

> **Nota sobre `pyproject.toml`**: `[build-system]` (`setuptools>=68.0`) está declarado no projeto, portanto `uv sync` no `.venv` e `uv tool install --editable ".[browser-speedtest]"` geram todos os entry points em `[project.scripts]` (`varedura`, `varedura-camera-bridge`, `varedura-update`). No Termux ARM64, use `scripts/termux_install.sh` (`pip install --no-build-isolation --no-deps -e .`).

---

## 4. Fronteiras de segurança e privacidade

- **Elevação UAC / `sudo`**: operações destrutivas do sistema (`Optimize-VHD`, `configure_wsl_sparse`, reparos de interface/DNS/DHCP) usam `is_admin()` / `run_as_admin()` (`ShellExecuteW(..., "runas", ...)` no Windows) ou guias sem execução automática quando há risco.
- **Autenticação do `varedura-update` (`varedura/updater.py`)**: tokens (`GHG_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`, `~/.varedura_gh_token` com `chmod 0600`) nunca são gravados em `.git/config`, em scripts temporários persistentes nem em logs; o Git é invocado via `GIT_ASKPASS` efêmero lendo variável de ambiente e toda saída passa por `_redact_token()`.
- **Ponte sanitizada (`varedura/camera_bridge.py`)**: único processo que lê credenciais e URLs RTSP brutas. O diretório `--output-dir` expõe somente IDs opacos, snapshots JPEG, segmentos HLS e `catalog.json` sanitizado; o canal `commands/inbox/` rejeita URLs e caminhos arbitrários.
- **Guardrails do MCP (`mcp_server/server.py`)**: `docker_quick_cleanup` e `docker_full_cleanup` recusam executar sem `confirmed=True` e oferecem `dry_run=True`.
- **Redação em logs e privacidade no histórico/grafo**: `rtsp/log.py` (`redact_sensitive`) remove senhas/URLs RTSP dos logs; `monitor/network_history.py` (`mask_ip`) mascara IPs como `/24` ou `/64` nas exportações; arquivos privados locais ficam fora do Git e do `graphify-out/graph.json`.

---

## 5. Mapa de arquivos persistidos e variáveis de ambiente

| Caminho / Variável | Escopo / Conteúdo | Controlado por |
|---|---|---|
| `~/.varedura_prefs.json` | Preferências de limpeza (`opt_*`), alvos de rede (`v3`) e `git_last_check` do updater | `cli/ui_shared.py`, `varedura/updater.py` |
| `~/.varedura_lang.json` | Idioma ativo (`"pt"` ou `"en"`) | `i18n/__init__.py` |
| `~/.varedura_gh_token` (ou `~/.config/varedura/gh_token`) | Token pessoal GitHub para `varedura-update` (`chmod 0600` no POSIX) | `varedura/updater.py` |
| `~/.varedura_termux_tools.json` | Lista customizada opcional de ferramentas lançadas pela aba Termux | `varedura/termux_env.py` |
| `~/.varedura/certs/` | CA de aplicativo validado pelo reparo `CONFIGURE_APP_CA` | `cli/ui_shared.py`, `monitor/network_repairs.py` |
| `exports/stalker_prefs.json` | Preferências do relatório PDF/exportação do Stalker | `monitor/stalker.py` |
| `screenshots/*.svg` | Capturas de tela SVG nativas da TUI Textual | `cli/textual_app.py` |
| `logs/YYYY-MM-DD.log` | Logs diários rotacionados da TUI (`DailyLogWriter`) | `cli/richlog.py` |
| `logs/rtsp.log*` | Log rotacionado com redação de credenciais (`RedactingFilter`) | `rtsp/log.py` |
| `logs/camera_bridge.log*` | Log rotacionado padrão do `varedura-camera-bridge` | `varedura/camera_bridge.py` |
| `credenciais.json`, `ips_conhecidos.json`, `regioes.json` | Vault de credenciais, cache de IPs RTSP e regiões salvas (gitignored) | `rtsp/credenciais.py`, `rtsp/regioes.py` |
| `camera_bridge_state.json`, `<output-dir>/.camera-locations.private.json` | Inventário privado e localização manual das câmeras gravada pelo `LocationStore` dentro do `--output-dir` (gitignored) | `varedura/camera_bridge.py` |
| `VAREDURA_TERMUX_MODE=1` / `VAREDURA_SHOW_DOCKER=1` | Forçam modo Termux ou exibição da aba `docker` no Android | `varedura/termux_env.py` |
| `GHG_TOKEN` / `GH_TOKEN` / `GITHUB_TOKEN` | Token GitHub em memória para `varedura-update` | `varedura/updater.py` |
