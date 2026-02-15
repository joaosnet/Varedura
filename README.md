# 🧹 Varedura

<p align="center">
  <img src="screenshots/Captura de tela 2026-01-14 125838.png" alt="Varedura screenshot" />
</p>

<p align="center">
  <strong>Cross-platform Docker cleanup toolkit, network monitor & AI model generator</strong>
</p>

<p align="center">
  <em>"Varedura" — Portuguese for "sweeping clean"</em>
</p>

<p align="center">
  <small>Available in: <a href="README.md">English</a> • <a href="README.pt-BR.md">Português (pt-BR)</a></small>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#%EF%B8%8F-cross-platform">Cross-Platform</a> •
  <a href="#-internationalization">i18n</a> •
  <a href="#-project-structure">Structure</a> •
  <a href="#%EF%B8%8F-safety">Safety</a>
</p>

---

## 🚀 Quick Start

### TUI (Recommended)

```bash
# using uv (recommended)
uv run main.py

# or without uv
python main.py
```

The app auto-detects your system language (English/Portuguese) and requests admin/root privileges when needed.

### CLI

```bash
# using uv (recommended)
uv run python -m cli.quick_cleanup             # Quick Docker prune
uv run python -m cli.main_cleaner              # Full cleanup with progress bar
uv run python -m cli.admin_tasks compact_vhdx  # Admin-only tasks (Windows)
uv run python -m lmarena.generator input.txt   # LMArena model generator

# or run directly with python
python -m cli.quick_cleanup             # Quick Docker prune
python -m cli.main_cleaner              # Full cleanup with progress bar
python -m cli.admin_tasks compact_vhdx  # Admin-only tasks (Windows)
python -m lmarena.generator input.txt   # LMArena model generator
```

## ✨ Features

### 🐳 Docker Cleanup
- **Full system prune** — containers, images, volumes, networks, build cache
- **Granular options** — pick exactly what to clean via interactive modal
- **VHDX compaction** — reclaim disk space from WSL2 virtual disks (Windows)
- **WSL sparse config** — optimize WSL2 memory and disk usage (Windows)
- **Temp file cleanup** — clear system temp directories
- **Real-time streaming** — watch every command execute line-by-line

### 🔍 Network Stalker
- Real-time network monitoring with latency graphs
- Port scanning and lag source analysis
- PDF report export with history charts
- Persistent preferences for export settings

### 🤖 LMArena Generator
- Extracts `initialModels` from LMArena data dumps
- Generates typed Python dicts: `models`, `text_models`, `image_models`, `vision_models`
- Outputs ready-to-use `.py` module files

### 📊 Logging & Reports
- Daily rotating logs in `logs/YYYY-MM-DD.log`
- PDF export for network monitoring reports
- Automatic exception capture (Python, asyncio, threading)

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
| LMArena Generator | ✅ | ✅ | ✅ |

> Windows-only features (VHDX, WSL sparse) are gracefully skipped on other platforms with an informational message.

## 🌍 Internationalization

Varedura supports **Portuguese** and **English** with automatic language detection:

1. **Auto-detects** your system locale on first run
2. **Switch anytime** by pressing `L` in the main menu
3. **Persists** your choice to `~/.varedura_lang.json`

The i18n system uses flat JSON files (`i18n/pt.json`, `i18n/en.json`) with `t("key")` lookups and `.format()` interpolation.

## 🏗️ Project Structure

```
Varedura/
├── docker_cleaner/        # Core cleanup logic (sync + async)
│   ├── core.py           # WSLDockerCleaner class
│   └── __init__.py
├── cli/                   # CLI entry points
│   ├── main_cleaner.py   # Full cleanup CLI
│   ├── quick_cleanup.py  # Quick prune CLI
│   ├── admin_tasks.py    # Admin helper
│   └── richlog.py        # Daily log writer
├── monitor/               # Network monitoring
│   ├── stalker.py        # Network Stalker
│   └── port_scanner.py   # Port scanner
├── lmarena/               # LMArena utilities
│   ├── generator.py      # Model list generator
│   └── __init__.py
├── i18n/                  # Translations
│   ├── __init__.py       # t() function, auto-detection
│   ├── pt.json           # Portuguese (170+ keys)
│   └── en.json           # English (170+ keys)
├── tests/                 # Unit tests (pytest)
├── exports/               # Generated PDFs
├── logs/                  # Daily rotating logs
├── main.py                # TUI entry point (Textual)
└── pyproject.toml         # Dependencies & config
```

## ⚙️ Installation

```bash
# Clone
git clone https://github.com/joaosnet/Varedura.git
cd Varedura

# Create venv & install
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e .
```

Using `uv` (optional, recommended for running tasks):

```bash
# add dependencies (example):
uv add <package>
uv sync

# run app / tests via uv
uv run main.py
uv run pytest tests/ -v
```

### Requirements

- **Python** 3.10+
- **Docker** installed and in PATH
- **Admin/root** for VHDX compaction and WSL configuration (Windows)
- **Dependencies:** `rich`, `textual`, `psutil`, `matplotlib`, `reportlab`

## ⚠️ Safety

**Destructive operations** — always require explicit user confirmation:

| Command | Effect |
|---------|--------|
| `docker system prune -af --volumes` | Removes ALL unused containers, images, volumes, networks |
| `taskkill /F` / `killall` | Force-kills Docker processes |
| `wsl --shutdown` | Stops all WSL distributions (Windows) |
| `Optimize-VHD` | Compacts VHDX files (Windows, requires admin) |

**Recommendations:**
1. ✅ Back up important data before running cleanup
2. ✅ Review selected options in the modal before confirming
3. ✅ Run as admin/root for full functionality
4. ✅ Monitor real-time logs during execution

## 🧪 Testing

```bash
pytest tests/ -v
```

All destructive operations are mocked in tests — no Docker commands are actually executed.

## 📄 License

See [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ using <a href="https://github.com/features/copilot/cli">GitHub Copilot CLI</a>
</p>

