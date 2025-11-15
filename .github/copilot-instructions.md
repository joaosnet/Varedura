# Copilot instructions — Docker-Clennear

Purpose
- This repo contains two functional areas:
  - WSL Docker cleanup tools (`cli/main_cleaner.py`, `cli/quick_cleanup.py`, `docker_cleaner/core.py`) — Windows-only utilities to reclaim WSL/Docker space, prune Docker state and compact VHDX files.
  - LMArena model utilities (`lmarena/generator.py`, `lmarena_models*.{txt,py}`) — parser/transformer that extracts models from raw dumps and writes a Python file (.py) with a `models` list and helper dicts.

Big picture / architecture
- Minimal, script-based repo (small module layout under `cli/`, `docker_cleaner/`, `lmarena/`). Most functionality is in standalone Python modules and a Textual TUI.
- `docker_cleaner/core.py` is the main cleaner implementation (`WSLDockerCleaner` class). `cli/main_cleaner.py` is a small CLI wrapper and `cli/quick_cleanup.py` contains a simpler, quick-clean CLI function.
- `lmarena/generator.py` is a pure data-processing utility which identifies `initialModels` JSON payloads in raw LMArena dumps and produces a Python module containing `models`, `text_models` and helper structures.

Key files to inspect
- `docker_cleaner/core.py` — main cleaning logic and rich console UI (`WSLDockerCleaner` class). Key methods: `run_command`, `is_admin`, `run_as_admin`, `docker_cleanup`, `stop_docker_wsl`, `configure_wsl_sparse`, `compact_vhdx_files`, `cleanup_temp_files`, `run_full_cleanup_with_progress`.
- `cli/main_cleaner.py` — CLI wrapper entrypoint that calls `docker_cleaner.core.main()`.
- `cli/quick_cleanup.py` — quick cleaning CLI implementation (in-process quick prune & compact flow).
- `lmarena/generator.py` — parsing functions on `ModelsGenerator` class: `extract_initial_models`, `normalize_model`, `format_models_python`, `extract_text_models`, `extract_image_models`, `extract_vision_models`, `generate_full_code`.
- `lmarena_models.txt` — example raw input from which `lmarena/generator.py` (or `-m lmarena.generator`) extracts `initialModels`.
- `lmarena_models_models.py` — example output created by the generator (includes `models`, `text_models`, `image_models`, `vision_models`).
- `main.py` — Textual TUI that integrates quick & full cleanup operations and the LMArena generator into a unified UI.
- `README.md` — short project description; expand when making workflow changes.

Developer workflows
- Local dev environment:
  1. Use the included virtualenv in `.venv` or create one: `python -m venv .venv` then `& .\.venv\Scripts\Activate.ps1`.
  2. Install `rich`, `textual` and other deps if not installed: `python -m pip install rich textual` (no requirements.txt present — add one if updating dependencies).

-- How to run cleaners
- Full cleaner (requires Windows + admin + Docker Desktop):
  - `python -m cli.main_cleaner` (wraps `docker_cleaner.core.main`). The app attempts to elevate using UAC if required.
- Quick cleaner (faster but less aggressive):
  - `python -m cli.quick_cleanup` or `python -m cli.quick_cleanup` to run stand-alone.
-- Alternatively, start the UI with `python main.py` to use a TUI that can run granular cleanup steps.
  - Notes: these scripts call `taskkill` and `docker system prune -af --volumes`, and will stop Docker Desktop and call `wsl --shutdown`. These are destructive operations. Ask for confirm if you propose changes that automatically run these commands.

-- How to run model generator
- Basic: `python -m lmarena.generator lmarena_models.txt` — reads a raw payload and writes `lmarena_models_models.py` (or `<input>_models.py`) with `models` and derived dictionaries.
- Example: run `python -m lmarena.generator --examples` (or call the `ModelsGenerator` class from a small script) to use a built-in example.

Project-specific conventions / patterns
- Platform-specific: All cleaning scripts target Windows and call Windows shell commands (`taskkill`, `Optimize-VHD`, `wsl --shutdown`). `docker_cleaner/core.py` checks `sys.platform.startswith('win')`.
- Permission & admin flow: `docker_cleaner/core.py` and `WSLDockerCleaner` use `ctypes` and `ShellExecuteW` to re-run as admin (UAC) when required; do not bypass the UAC flow.
- Logging & UI: The repo uses `rich`/`Textual` for UI and `wsl_docker_cleanup.log` as the default log file; write logs via `WSLDockerCleaner.log()` so they are captured in `self.log_messages` and persisted to the log file.
- Shell commands and parsing: scripts use `subprocess.run(..., shell=True)` and parse `stdout` for `"Total reclaimed space"` in Docker CLI responses — if you alter this, update parsers and tests accordingly.

Integration points & external dependencies
- Docker CLI: `docker ps`, `docker system prune`, `docker container prune`, `docker image prune`, `docker volume prune`, `docker network prune`, `docker builder prune`.
- Windows components: `tasklist`/`taskkill`, `Optimize-VHD` (PowerShell), `wsl --shutdown`, and files under `%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx`.
- `rich`, `textual` packages are used for UX; consider adding a `requirements.txt` or `pyproject.toml` updates if adding/removing packages.

Important safety notes (must not change without prompt)
- `docker system prune -af --volumes` is destructive — avoid changes that reduce confirmation or make this command silent without user's awareness.
- Compacting VHDX and killing Docker/WSL are disruptive operations — persist in tests and require explicit user confirmation.
- `docker_cleaner.core.run_command` uses `shell=True` — if you change this to `shell=False` or alter quoting, adjust how arguments are passed and parsed.

Guidance for contributors / copilot suggestions
- When updating or adding features:
  - Keep all Windows-specific calls wrapped in platform checks.
  - Respect admin check and `run_as_admin` logic: do not bypass UAC.
  - If you need to add unit tests, focus them on `lmarena/generator.py` functions (pure/Python), and `docker_cleaner/core.py` via mocked `run_command` / subprocesses to avoid destructive system calls.
  - Add `requirements.txt` if you add packages (e.g., `textual`, `rich`).
  - When adding logging, extend `WSLDockerCleaner.log()` so messages are also appended to `self.log_messages` and persisted to `wsl_docker_cleanup.log`.

Notes for the AI agent (Copilot)
- Prefer READ-ONLY changes for new analysis or PRs: tests, static analysis, and unit tests for parsing logic in `lmarena/generator.py`.
- For changes that require manual testing — e.g., `Optimize-VHD` or `taskkill` — add mocks + a test harness and do not run destructive commands in CI.
- If you propose changing CLI behavior (adding flags, scheduling), update documentation in `README.md` and add example commands showing behavior.
- Always call out destructive commands in code review comments and ask maintainers whether they want safer behavior (e.g., `--dry-run`) or confirmations.

Examples (copy-paste):
- Run quick test of model generator (module):
  python -m lmarena.generator lmarena_models.txt

- Run the full cleanup (requires admin):
  # PowerShell (Admin):
  & .\.venv\Scripts\Activate.ps1
  python -m cli.main_cleaner

- Run only the docker prune steps (non-admin but destructive):
  docker system prune -af --volumes

UI / Textualize & UV workflow 🔧
- Textualize: We standardize on the Textual (Textualize) framework for any new terminal UI/TUI or interactive command-line screens. Textual provides a high-quality Compose/Widget/reactive API (see `compose()`, `reactive/var`, `watch_*`, and `mount()` patterns).
- Mandatory MCP usage: Before implementing any UI, CLI interaction, or new TUI screen, you must fetch and consult the official Textual docs using MCP. This ensures you use the proper API patterns and avoid duplicating outdated patterns.

  Minimum MCP lookup sequence (example):
  1. Resolve the library id: `mcp_mcp_docker_resolve-library-id('textualize/textual')`.
  2. Fetch docs and examples for topics you plan to implement: `mcp_mcp_docker_get-library-docs(contextID, tokens=2000, topic='getting_started')` and `topic='widgets'`, `topic='reactivity'`, `topic='compose'`.
  3. Inspect canonical examples (compose, widgets, input widgets, layout) and verify you use Textual's `compose()` & `reactive` idioms.

  Notes from the Textual docs (always consult via MCP each time):
  - Use `compose()` to create nested widgets and containers, not raw render functions.
  - Prefer `reactive` or `var` for state that triggers UI updates and `watch_*` callbacks to respond to state changes.
  - Use `mount()` for dynamic insertion and `set_interval()` for periodic updates.
  - Use CSS/TS files (Textual CSS) for styling and `styles.layout` to adjust layout at runtime.
  - Prefer built-in widgets (`Header`, `Footer`, `Input`, `Static`, `DataTable`, etc.) and compose compound widgets with containers.

Mandatory MCP usage for all external libraries & system components 🛡️
- The agent MUST consult authoritative documentation via MCP for any external library, runtime, or system feature it touches. This is mandatory when implementing, refactoring, or testing features that rely on external docs (Textual, Docker, WSL, Windows APIs, Optimize-VHD, Python libs, etc.).
- Minimal MCP workflow (required for every PR touching external components):
  1. Resolve the library id: `mcp_mcp_docker_resolve-library-id('<library-name>')`.
  2. Fetch docs & examples for relevant topics: `mcp_mcp_docker_get-library-docs(contextId, tokens=2000, topic='<topic>')`.
  3. For each topic, include in the PR description: the resolved library ID, topic names, and 1-2 example snippets you used as reference.
  4. If no authoritative docs appear in MCP search or results are ambiguous, ask the maintainers which docs or source to use.

  Example: When changing a Textual-based UI you must run:
    - `mcp_mcp_docker_resolve-library-id('textualize/textual')`
    - `mcp_mcp_docker_get-library-docs('/textualize/textual', topic='compose')`
    - `mcp_mcp_docker_get-library-docs('/textualize/textual', topic='reactivity')`

  Example: When modifying Docker/WSL logic you must run:
    - `mcp_mcp_docker_resolve-library-id('docker/cli')` (or the best match returned)
    - `mcp_mcp_docker_get-library-docs('<contextId>', topic='cli-reference')`

Enforcement & PR checklist ✅
- Every PR that adds/changes code interacting with external libraries must include a short block in the PR body with:
  - Libraries consulted (resolved MCP IDs)
  - Topics consulted (e.g., `compose`, `widgets`, `reactivity`, `docker prune`, `wsl`) and token-limited snippets used
  - A short summary of which API/behavior was implemented and why (1-2 lines)
  - Any version constraints or compatibility notes (e.g., Textual v4 API differences)

Note: This requirement is not optional — it ensures the agent is implementing against the current, authoritative docs and reduces regressions caused by deprecated APIs or mismatched patterns.

UV CLI policy for package management & runtime 🧭
- Use the `uv` helper for dependency management and to execute commands in the project environment: prefer `uv add`, `uv pip`, `uv run`, `uv sync` over raw pip or direct invocation.

  - Example UV workflow for UI work:
    1. Add the dependency manifest entry (if your repo tracks packages): `uv add textual`.
    2. Install with the extras you need: `uv pip install "textual[syntax]"` (for syntax highlighting in TextArea or `uv pip install textual-dev` for dev builds).
    3. Sync the environment: `uv sync`.
    4. Run the app or tests: `uv run python main.py` or `uv run python -m lmarena.generator`.
    5. If editing dependencies: `uv pip uninstall <old>` then `uv pip install <new>` and `uv sync`.

  Keep these in mind:
  - Always use `uv add`/`uv pip` to change dependencies; commit lockfile/manifests updated by `uv sync` if you use one.
  - Use `uv run` for reproducible command execution in the project's environment.
  - When opening a PR, include the initial MCP query results in your PR description: which `topic` docs you used (examples and links) and the minimal API patterns chosen.

Implementation details & examples 💡
-- Use `lmarena/generator.py` as the canonical example when adding Textual-based UIs to parsing tasks: keep UI code under `ui/` and keep business logic decoupled (no direct shell calls from UI).
- Example `compose()` pattern to follow (consult Textual docs via MCP and implement accordingly):
  - Provide `Header()` and `Footer()` for global controls.
  - Use `VerticalScroll`/`Container` for long content and `Input()` for interactive fields.
  - Use `reactive` state to update status (e.g., `status = var('ready')`) and `watch_status` to update UI.

Safety and code-review checklist ⚠️
- Must include MCP doc citations in PR (which pages/examples were used).
- Avoid embedding system-level destructive logic (e.g., `docker system prune`, `taskkill`, `wsl --shutdown`) directly in UI logic. UI should call into a safe facade (a function that is well-tested and mocks shell calls in tests).
-- For `docker_cleaner/core.py` and `cli/quick_cleanup.py`, only align UI with Textual when it replaces or adds interactive views; keep destructive operations explicit and request confirmation.

Testing and examples
- Add unit tests for UI logic that do not run shells: create fixtures that mock `subprocess.run`, `Optimize-VHD` and `ctypes` admin checks.
- For Textual components, add small programmatic tests that instantiate `App` objects and assert the presence of widgets and reactive updates.

-- End of Textualize & UV section --

-- End of file --
