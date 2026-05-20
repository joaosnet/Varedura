# 🧹 Varedura

<p align="center">
  <img src="screenshots/demo.gif" alt="Varedura demo" width="720" />
</p>

<p align="center">
  <strong>Cross-platform Docker cleanup toolkit, network monitor & MCP server — built entirely with GitHub Copilot CLI</strong>
</p>

<p align="center">
  <em>"Varedura" — Portuguese for "sweeping clean"</em>
</p>

<p align="center">
  <a href="https://github.com/joaosnet/Varedura/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License" /></a>
  <a href="https://github.com/joaosnet/Varedura"><img src="https://img.shields.io/badge/python-≥3.14-3776AB.svg?logo=python&logoColor=white" alt="Python 3.14+" /></a>
  <a href="https://github.com/joaosnet/Varedura"><img src="https://img.shields.io/badge/platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg" alt="Platform" /></a>
  <a href="https://dev.to/challenges/github-2026-01-21"><img src="https://img.shields.io/badge/DEV-GitHub%20Copilot%20CLI%20Challenge-black?logo=dev.to" alt="DEV Challenge" /></a>
</p>

<p align="center">
  <sub>Available in: <a href="README.md">English</a> · <a href="README.pt-BR.md">Português (pt-BR)</a></sub>
</p>

<p align="center">
  <a href="#-quick-install">Install</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-mcp-server--copilot-cli-integration">MCP + Copilot</a> ·
  <a href="#%EF%B8%8F-cross-platform">Cross-Platform</a> ·
  <a href="#-built-with-github-copilot-cli">Built with Copilot CLI</a>
</p>

---

## 📦 Quick Install

### One-liner (recommended)

**Windows** (PowerShell):
```powershell
irm https://raw.githubusercontent.com/joaosnet/Varedura/main/install.ps1 | iex
```

**Linux / macOS**:
```bash
curl -fsSL https://raw.githubusercontent.com/joaosnet/Varedura/main/install.sh | bash
```

After installing, just type **`varedura`** in any terminal to launch.

> The installer automatically detects your OS, checks for required tools (`uv`, `Docker`, `Git`), installs only what's missing, and supports both **Portuguese** and **English**. If Varedura is already installed, it offers to **reinstall** or **uninstall**.

### Other installation methods

<details>
<summary><strong>Install with uv (manual)</strong></summary>

```bash
uv tool install git+https://github.com/joaosnet/Varedura.git --python ">=3.14"
```

Then run: `varedura`

</details>

<details>
<summary><strong>Clone & run from source</strong></summary>

```bash
git clone https://github.com/joaosnet/Varedura.git
cd Varedura
uv run main.py           # TUI (recommended)
```

</details>

<details>
<summary><strong>CLI modules (without TUI)</strong></summary>

```bash
uv run python -m cli.quick_cleanup             # Quick Docker prune
uv run python -m cli.main_cleaner              # Full cleanup with progress bar
uv run python -m cli.admin_tasks compact_vhdx  # Admin-only tasks (Windows)
```

</details>

<details>
<summary><strong>Uninstall</strong></summary>

**Via installer:**
```powershell
# Windows
.\install.ps1 -Uninstall
```
```bash
# Linux / macOS
./install.sh --uninstall
```

**Or via uv:**
```bash
uv tool uninstall varedura
```

</details>

### Requirements

| Requirement | Notes |
|---|---|
| **Python ≥ 3.14.2** | Managed automatically by `uv` during install |
| **uv** | Installed automatically by the installer if missing |
| **Docker** | Optional — needed for Docker cleanup features |
| **Admin / root** | Optional — needed for VHDX compaction & WSL config (Windows) |

---

## 📌 Current Project Status

Varedura is currently a **Textual + Rich terminal app** with modular tooling for Docker cleanup, network diagnostics, MCP integration, and session recording.

- Main interface: Textual TUI in `cli/textual_app.py` with Rich renderables
- Legacy Rich interface: `varedura --legacy-rich` or `VAREDURA_UI=rich varedura`
- Docker engine cleanup: sync + async logic in `docker_cleaner/core.py`
- Network tooling: `monitor/stalker.py`, `monitor/port_scanner.py`, `monitor/speed_tester.py`
- MCP server: `mcp_server/server.py` (5 tools exposed to AI agents)
- Session recorder: SVG capture + GIF generation in `recorder/`
- i18n: bilingual `i18n/en.json` and `i18n/pt.json`
- Model utilities: LM Arena parser/generator in `lmarena/`

---

## ✨ Features

### 🐳 Docker Cleanup
- **Full system prune** — containers, images, volumes, networks, build cache
- **Granular options** — pick exactly what to clean via interactive menu
- **VHDX compaction** — reclaim disk space from WSL2 virtual disks (Windows)
- **WSL sparse config** — optimize WSL2 memory and disk usage (Windows)
- **Temp file cleanup** — clear system temp directories
- **Real-time streaming** — watch every command execute line-by-line

### 🔍 Network Stalker
- Real-time network monitoring with latency graphs
- Port scanning with process identification
- Internet speed testing (multi-provider: Speedtest.net, Fast.com)
- ANATEL compliance checking (Brazil broadband regulation)
- PDF report export with history charts
- Persistent preferences for export settings

### 🤖 MCP Server (AI Integration)
- Exposes Varedura tools to **GitHub Copilot CLI** and other AI agents via [Model Context Protocol](https://modelcontextprotocol.io/)
- 5 tools available: `docker_status`, `docker_quick_cleanup`, `docker_full_cleanup`, `port_scan`, `get_logs`
- Automatic `.vscode/mcp.json` configuration from Settings menu
- Works seamlessly with GitHub Copilot CLI agent mode

### 🎬 Session Recorder
- Automatic GIF recording of terminal sessions
- SVG snapshot capture → animated GIF generation
- Auto-updates `screenshots/demo.gif` for README
- Toggle on/off from Settings menu

### 🤖 Animated Mascot
- Pixel-art robot companion with state-based animations
- States: Idle, Working, Success, Error, Scanning, Wave
- Speech bubbles with contextual messages

### 📊 Logging & Reports
- Daily rotating logs in `logs/YYYY-MM-DD.log`
- PDF export for network monitoring reports
- CSV export for ping and speed history
- Automatic exception capture (Python, asyncio, threading)

### 🌍 Internationalization
- **Auto-detects** your system locale on first run (Portuguese / English)
- **Switch anytime** from the Settings menu
- **350+ translation keys** covering every UI element
- **Persists** your choice to `~/.varedura_lang.json`

### 🧠 LM Arena Models
- Parses and normalizes model lists for LM Arena workflows
- Generates structured outputs from `lmarena/lmarena_models.txt`

---

## 🤖 MCP Server & Copilot CLI Integration

Varedura includes a built-in **MCP (Model Context Protocol) server** that exposes its tools to AI agents like **GitHub Copilot CLI**.

### Setup

From the Varedura menu, go to **Settings → MCP Server** to auto-configure, or manually add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "varedura": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server"]
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `docker_status` | Get Docker disk usage, running containers, image/volume counts |
| `docker_quick_cleanup` | Prune containers, images, volumes, networks, build cache |
| `docker_full_cleanup` | Full cleanup + WSL shutdown + VHDX compaction (Windows) |
| `port_scan` | Scan listening TCP/UDP ports, top processes by connection count |
| `get_logs` | Retrieve recent Varedura log entries (up to 500 lines) |

### Usage with Copilot CLI

Once configured, GitHub Copilot CLI can use Varedura tools directly:

```
> How much Docker disk space am I using?        → calls docker_status
> Clean up all unused Docker resources           → calls docker_quick_cleanup
> What ports are listening on my system?         → calls port_scan
> Show me the last 50 log entries                → calls get_logs
```

---

## 🖥️ Cross-Platform

Varedura runs on **Windows**, **Linux**, and **macOS**:

| Feature | Windows | Linux | macOS |
|---------|---------|-------|-------|
| Docker prune/cleanup | ✅ | ✅ | ✅ |
| Stop Docker processes | ✅ `taskkill` | ✅ `systemctl`/`killall` | ✅ `killall`/`open` |
| VHDX compaction | ✅ `Optimize-VHD` | ⬜ N/A | ⬜ N/A |
| WSL sparse config | ✅ | ⬜ N/A | ⬜ N/A |
| Temp file cleanup | ✅ `%TEMP%` | ✅ `/tmp` | ✅ `/tmp` |
| Recycle bin cleanup | ✅ PowerShell | ⬜ Skipped | ⬜ Skipped |
| Admin elevation | ✅ UAC | ✅ `sudo` | ✅ `sudo` |
| Network Stalker | ✅ | ✅ | ✅ |
| MCP Server | ✅ | ✅ | ✅ |
| One-liner install | ✅ `irm \| iex` | ✅ `curl \| bash` | ✅ `curl \| bash` |

> Windows-only features (VHDX, WSL sparse) are gracefully skipped on other platforms with an informational message.

---

## 🏗️ Current File Tree (Mar 2026)

```
Varedura/
├── .github/
├── .vscode/
├── build/
│   └── lib/
│       ├── cli/
│       ├── docker_cleaner/
│       ├── i18n/
│       ├── mascot/
│       ├── mcp_server/
│       ├── monitor/
│       └── recorder/
├── cli/
│   ├── admin_tasks.py
│   ├── main_cleaner.py
│   ├── quick_cleanup.py
│   └── richlog.py
├── docker_cleaner/
│   └── core.py
├── exports/
├── i18n/
│   ├── en.json
│   └── pt.json
├── lmarena/
│   ├── generator.py
│   ├── lmarena_models.txt
│   └── models.py
├── mascot/
│   ├── frames.py
│   ├── generate_sprites.py
│   ├── images/
│   └── renderer.py
├── mcp_server/
│   ├── __main__.py
│   └── server.py
├── monitor/
│   ├── port_scanner.py
│   ├── speed_providers.py
│   ├── speed_tester.py
│   └── stalker.py
├── recorder/
│   ├── gif_generator.py
│   └── session_recorder.py
├── recordings/
├── screenshots/
├── tests/
│   ├── images/
│   ├── static/
│   ├── test_export_pdf.py
│   ├── test_export_prefs.py
│   └── test_export_prompt.py
├── install.ps1
├── install.sh
├── LICENSE
├── main.py
├── POST-SUBMISSION.md
├── pyproject.toml
├── README.md
├── README.pt-BR.md
├── router_template.html
└── uv.lock
```

---

## ⚠️ Safety

**Destructive operations** always require explicit user confirmation:

| Command | Effect |
|---------|--------|
| `docker system prune -af --volumes` | Removes ALL unused containers, images, volumes, networks |
| `taskkill /F` / `killall` | Force-kills Docker processes |
| `wsl --shutdown` | Stops all WSL distributions (Windows) |
| `Optimize-VHD` | Compacts VHDX files (Windows, requires admin) |

**Recommendations:**
1. ✅ Back up important data before running cleanup
2. ✅ Review selected options before confirming
3. ✅ Run as admin/root for full functionality
4. ✅ Monitor real-time logs during execution

---

## 🧪 Testing

```bash
uv run python -m pytest tests/ -v
```

All destructive operations are mocked in tests — no Docker commands are actually executed.

---

## 🤖 Built with GitHub Copilot CLI

> *This project was built for the [GitHub Copilot CLI Challenge](https://dev.to/challenges/github-2026-01-21).*

**Every feature** of Varedura was developed using [GitHub Copilot CLI](https://github.com/features/copilot/cli) as the primary development tool — from architecture decisions to implementation, debugging, and testing.

How Copilot CLI was used throughout the project:

- **🏗️ Architecture** — Designed the dual sync/async execution model, MCP server integration, and cross-platform abstraction
- **🐳 Docker Cleaner** — Implemented WSLDockerCleaner with streaming output, admin elevation, and VHDX compaction
- **🔍 Network Monitor** — Built the stalker, port scanner, speed tester with multi-provider support
- **🤖 MCP Server** — Created the Model Context Protocol server exposing all tools to AI agents
- **🎨 TUI & Mascot** — Designed the Rich-based menu system and pixel-art animated robot companion
- **🌍 i18n System** — Implemented 350+ bilingual translation keys with auto-detection
- **📦 Installer** — Created the standalone installer scripts (install.sh + install.ps1) following UV/OpenClaw patterns
- **🎬 Session Recorder** — Built the SVG→GIF recording pipeline for automatic demo generation
- **🧪 Testing** — Wrote unit tests with proper mocking for all destructive operations

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ using <a href="https://github.com/features/copilot/cli">GitHub Copilot CLI</a>
</p>

