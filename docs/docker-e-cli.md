# Docker Cleaner, TUI Textual e CLIs — Varedura

Cobre o motor de limpeza Docker/WSL2 (`docker_cleaner/`), a interface Textual única (`cli/textual_app.py`, `cli/textual_cameras.py`), CLIs headless, saúde de rede (`monitor/network_health.py`), captura de tela SVG nativa e internacionalização (`i18n/`). Para recursos específicos de Android/Termux e auto-atualização, veja também [docs/termux.md](termux.md).

---

## 1. Motor Docker / WSL2 (`docker_cleaner/core.py`)

A classe `WSLDockerCleaner` implementa um **modelo dual síncrono e assíncrono**:

- **Métodos síncronos** (`docker_cleanup`, `stop_docker_wsl`, `configure_wsl_sparse`, `compact_vhdx_files`, `cleanup_temp_files`, `cleanup_recycle_bin`): usados pelas CLIs headless e pelo servidor MCP.
- **Métodos assíncronos** (`*_async`): recebem `stream_callback: Callable[[str], None]` e leem stdout/stderr linha a linha via `asyncio.subprocess` para alimentar o log da TUI sem travar o loop de eventos.
- **Descoberta de VHDX (Windows)**: `get_docker_vhdx_paths()` procura `docker_data.vhdx` e `ext4.vhdx` em `%LOCALAPPDATA%\Docker\wsl` e `%USERPROFILE%\AppData\Local\Docker\wsl`.
- **Compactação e sparse mode**: encerram o WSL (`wsl --shutdown`), ativam alocação esparsa (`wsl --manage ... --set-sparse true`) e compactam com `Optimize-VHD` (PowerShell elevado via UAC) ou fallback `diskpart`.
- **Operações fora do Windows**: etapas exclusivas de Windows (VHDX/WSL/Lixeira PowerShell) são ignoradas com segurança via `IS_WINDOWS` (`sys.platform.startswith("win")`).

### CLIs headless e helpers de elevação

- `cli/quick_cleanup.py`: executa `docker_cleanup` (6 passos padrão: `containers`, `images`, `volumes`, `networks`, `system`, `builder`) → `stop_docker_wsl` → `compact_vhdx_files` com barra de progresso Rich.
- `cli/main_cleaner.py`: chama diretamente `docker_cleaner.core.main()`.
- `cli/admin_tasks.py`: helper elevado (`python -m cli.admin_tasks compact_vhdx|configure_sparse`), verifica `cleaner.is_admin()` antes de agir.

---

## 2. TUI Textual (`cli/textual_app.py` e `cli/textual_cameras.py`)

`VareduraTextualApp` (iniciado diretamente por `main.py` → `run_textual_app()`) organiza o app em abas principais (`#main-tabs`):

1. **`dashboard`**: resumo do sistema/rede em tempo real, atalhos rápidos às ferramentas e ações Termux quando ativo no Android.
2. **`docker`** *(condicional)*: exibida sempre no desktop; no Android/Termux só aparece quando `should_show_docker_tab()` é `True` (binário `docker` presente no `PATH` ou `VAREDURA_SHOW_DOCKER=1`). Traz presets (`QUICK_CLEANUP_KEYS` vs seleção granular de `CLEANUP_STEPS`), checkboxes persistidos em `~/.varedura_prefs.json`, execução em worker e barra de progresso.
3. **`network`**: 4 sub-abas (`#network-subtabs`: `net-speed-tab`, `net-ports-tab`, `net-procs-tab`, `net-log-tab`), card de saúde (`compute_health_score` em `monitor/network_health.py`), cards de latência por alvo (`TargetPingCard`), seleção de alvos (`TargetPickerScreen`), diagnóstico/reparos (`RepairConfirmationScreen`), exportação PDF/CSV e compartilhamento (`Termux:API` / sistema).
4. **`cameras`**: fornecida via mixin `CamerasMixin` (`cli/textual_cameras.py`), com 4 sub-abas (`tab-rede`, `tab-rtsp`, `tab-portas`, `tab-cred`), radar animado, descoberta LAN/externa, abertura de player (`vlc-android`/`termux-open`/`mpv --vo=tct` no Android ou `mpc-hc`/`ffplay`/`vlc`/`mpv` no desktop), snapshot JPEG e cópia de URL.
5. **`termux`** *(Termux/Android)*: Hub nativo via `varedura/termux_env.py` com telemetria do aparelho (bateria, Wi-Fi, dados móveis, memória, root), launcher de ferramentas/atalhos (`~/.claro_suite/`, `~/.shortcuts/`, `~/.varedura_termux_tools.json`), controles da Suite Claro e gestão de serviços/SSH (`sshd`, `crond`, `wakelock`, daemon Claro, cron do updater).
6. **`settings`**: idioma (`pt`/`en`), alvos/thresholds de rede, instalação do bloco `.vscode/mcp.json`, atualização Git via `varedura/updater.py` (status de branch/token, verificação/pull manual e toggle de cron 6h) e captura de tela nativa.

**Captura de tela nativa**: a TUI salva snapshots SVG diretamente via Textual (`save_screenshot()`) em `screenshots/`, sem depender de bibliotecas externas de imagem ou gravação.

---

## 3. Módulos auxiliares de UI

| Módulo | Responsabilidade |
|---|---|
| `cli/network_ui.py` | Modais Textual lazy: `TargetPickerScreen` (1–5 alvos + primário) e `RepairConfirmationScreen` |
| `cli/ui_shared.py` | `PREFS_FILE` (`~/.varedura_prefs.json`), `CLEANUP_STEPS`, `CLEANUP_GROUPS`, migração de config de rede v3, cards Rich compartilhados |
| `cli/richlog.py` | `DailyLogWriter`: grava com timestamp em `logs/YYYY-MM-DD.log` e encaminha para a UI |
| `monitor/network_health.py` | `compute_health_score`: cálculo puro (0–100, tiers `S`/`A`/`B`/`C`/`F`) a partir do histórico de latência, perda e conformidade ANATEL |
| `i18n/` | `init()`, `set_language()`, `t()` lendo `i18n/pt.json` e `i18n/en.json` (paridade verificada por `tests/test_i18n_parity.py`) e persistindo em `~/.varedura_lang.json` |

---

## 4. Índices de faixas de linha (arquivos > 1.300 linhas)

Para economizar tokens, use `read_file` apenas no trecho desejado:

### `docker_cleaner/core.py` (1.946 linhas)
- `L32-93`: constantes `IS_WINDOWS`, `DOCKER_CLEANUP_COMMANDS`, `CleanupStepResult`, `get_docker_vhdx_paths()`
- `L99-120`: helpers PowerShell (`_powershell_encoded_command`, `_strip_powershell_clixml`)
- `L122-444`: `WSLDockerCleaner.__init__`, `log`, `run_command*`, elevação UAC (`is_admin`, `run_as_admin`, `_build_windows_elevated_command`)
- `L446-689`: VHDX size/unlock, `_run_docker_cleanup_step`, `docker_cleanup()`, `stop_docker_wsl()`
- `L690-1199`: WSL `.wslconfig` sparse, `fstrim`, recriação/compactação VHDX (`configure_wsl_sparse`, `compact_vhdx_files`)
- `L1201-1408`: limpeza de temporários e lixeira (sync + async)
- `L1411-1743`: pipeline async completo (`docker_cleanup_async`, `stop_docker_wsl_async`, `configure_wsl_sparse_async`, `compact_vhdx_files_async`)
- `L1745-1942`: relatórios Rich, `run_full_cleanup_with_progress()` e `main()`

### `cli/textual_app.py` e `cli/textual_cameras.py`
- `cli/textual_app.py`: `TargetPingCard`, `ShutdownScreen`, `VareduraTextualApp` (abas `dashboard`, `docker` condicional, `network`, `cameras`, `termux`, `settings`, captura SVG nativa e integração `updater`) + `run_textual_app()`.
- `cli/textual_cameras.py`: `_load_camera_backend()` (import lazy de `rtsp/*`), `ClickOpenDataTable`, `CamerasMixin` (4 sub-abas, radar, workers de descoberta, snapshot, `mpv --vo=tct` e gestão de credenciais).
