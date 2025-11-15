# Copilot instructions — Docker-Clennear

Purpose
- This repo contains two functional areas:
  - WSL Docker cleanup tools (`wsl_docker_cleaner.py`, `quick_wsl_cleanup.py`) — Windows-only scripts to reclaim WSL/Docker space and compact VHDX files.
  - LMArena model utilities (`models_generator.py`, `lmarena_models*.{txt,py}`) — parser/transformer that extracts models from raw dumps and writes a Python file (.py) with a `models` list and helper dicts.

Big picture / architecture
- Minimal, script-based repo (no package import structure). Most work is in standalone Python scripts.
- `wsl_docker_cleaner.py` is the main, full-featured cleaner (rich UI, progress, admin-elevation flow). `quick_wsl_cleanup.py` offers a lighter, faster path.
- `models_generator.py` is a pure data-processing utility which identifies `initialModels` JSON payloads in raw `LMArena` dumps and produces `*_models.py`.

Key files to inspect
- `wsl_docker_cleaner.py` — main cleaning logic and rich console UI. Key methods: `run_command`, `is_admin`, `run_as_admin`, `docker_cleanup`, `stop_docker_wsl`, `configure_wsl_sparse`, `compact_vhdx_files`, `cleanup_temp_files`, `run_full_cleanup_with_progress`.
- `quick_wsl_cleanup.py` — quick cleaning steps, mirrors core commands used by the full cleaner.
- `models_generator.py` — parsing functions on static `ModelsGenerator` class: `extract_initial_models`, `normalize_model`, `format_models_python`, `extract_text_models`, `extract_image_models`, `extract_vision_models`.
- `lmarena_models.txt` — example raw input from which `models_generator.py` extracts initialModels.
- `lmarena_models_models.py` — example output created by the generator (includes `models`, `text_models`, `image_models`, `vision_models`).
- `README.md` — extremely short project description; expand when making workflow changes.

Developer workflows
- Local dev environment:
  1. Use the included virtualenv in `.venv` or create one: `python -m venv .venv` then `& .\.venv\Scripts\Activate.ps1`.
  2. Install `rich` if not installed: `python -m pip install rich` (no requirements.txt present — add one if updating dependencies).

- How to run cleaners
  - Full cleaner (requires Windows + admin + Docker Desktop):
      - `python wsl_docker_cleaner.py` (the script will attempt to re-run itself as admin if not elevated)
  - Quick cleaner (faster but less aggressive):
      - `python quick_wsl_cleanup.py`
  - Notes: these scripts call `taskkill` and `docker system prune -af --volumes`, and will stop Docker Desktop and call `wsl --shutdown`. These are destructive operations. Ask for confirm if you propose changes that automatically run these commands.

- How to run model generator
  - Basic: `python models_generator.py lmarena_models.txt` — reads raw payload and writes `lmarena_models_models.py` (or `<input>_models.py`) with `models` and derived dictionaries.
  - Example: `python models_generator.py --examples` prints a built-in practical example.

Project-specific conventions / patterns
- Platform-specific: All cleaning scripts assume Windows (shell commands like `taskkill`, `Optimize-VHD`, `wsl --shutdown`). `wsl_docker_cleaner.py` is explicit in the `if not sys.platform.startswith('win')` check.
- Permission & admin flow: `wsl_docker_cleaner.py` uses `ctypes` and `ShellExecuteW` to re-run with elevated privileges when necessary rather than failing silently. Keep this flow unchanged unless you know Windows UAC patterns intimately.
- Logging & UI: The repo uses `rich` for console UI and table/panel layouts and maintains `wsl_docker_cleanup.log`. For new behavior add `self.log(...)` to centralize messages.
- Shell commands and parsing: scripts use `subprocess.run(..., shell=True)` and parse `stdout` for `"Total reclaimed space"` text returned by Docker CLI. When modifying logic, update both run_command behavior and message parsing.

Integration points & external dependencies
- Docker CLI: `docker ps`, `docker system prune`, `docker container prune`, `docker image prune`, `docker volume prune`, `docker network prune`, `docker builder prune`.
- Windows system: `tasklist`/`taskkill`, `Optimize-VHD` (PowerShell), `wsl --shutdown`, and files under `%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx`.
- `rich` package is used for UX. There is no `requirements.txt` — add one if you introduce new dependencies.

Important safety notes (must not change without prompt)
- `docker system prune -af --volumes` is destructive — avoid changes that reduce confirmation or make this command silent without user's awareness.
- Compacting VHDX and killing Docker/WSL are disruptive operations. Tests should simulate flow or run on non-critical/home machine before committing changes.
- `run_command` currently uses `shell=True`: if you alter this, adjust command string handling accordingly.

Guidance for contributors / copilot suggestions
- When updating or adding features:
  - Keep all Windows-specific calls wrapped in platform checks.
  - Respect admin check and `run_as_admin` logic: do not bypass UAC.
  - If you need to add unit tests, focus them on `models_generator.py` functions: they’re pure/Python and safe to test. For `wsl_docker_cleaner.py`, unit tests should mock `run_command` to avoid destructive system calls.
  - Add `requirements.txt` if you add packages (e.g. additional 3rd-party libs).
  - When adding logging, extend `log()` so messages are also appended to `self.log_messages` and the `wsl_docker_cleanup.log` for future debugging.

Notes for the AI agent (Copilot)
- Prefer READ-ONLY changes for new analysis or PRs: tests, static analysis, and unit tests for parsing logic in `models_generator.py`.
- For code changes that require manual testing — e.g., `Optimize-VHD` or `taskkill` — suggest adding mocks + a corresponding test harness as part of the PR.
- If you propose changing CLI behavior (adding flags, scheduling), update documentation in `README.md` and add example commands.
- Always call out destructive commands in code review comments and ask maintainers whether they want safer behavior (e.g., `--dry-run`) or confirmations.

Examples (copy-paste):
- Run quick test of model generator:
    python models_generator.py lmarena_models.txt

- Run the full cleanup (requires admin):
    # PowerShell (Admin):
    & .\.venv\Scripts\Activate.ps1
    python wsl_docker_cleaner.py

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

  Example UV workflow for UI work:
  1. Add the dependency manifest entry (if your repo tracks packages): `uv add textual`.
  2. Install with the extras you need: `uv pip install "textual[syntax]"` (for syntax highlighting in TextArea or `uv pip install textual-dev` for dev builds).
  3. Sync the environment: `uv sync`.
  4. Run the app or tests: `uv run python -m textual` or `uv run python your_ui_module.py`.
  5. If editing dependencies: `uv pip uninstall <old>` then `uv pip install <new>` and `uv sync`.

  Keep these in mind:
  - Always use `uv add`/`uv pip` to change dependencies; commit lockfile/manifests updated by `uv sync` if you use one.
  - Use `uv run` for reproducible command execution in the project's environment.
  - When opening a PR, include the initial MCP query results in your PR description: which `topic` docs you used (examples and links) and the minimal API patterns chosen.

Implementation details & examples 💡
- Use `models_generator.py` as the canonical example when adding Textual-based UIs to parsing tasks: keep UI code under a module (e.g., `ui/`) and keep business logic decoupled (no direct shell calls from UI).
- Example `compose()` pattern to follow (consult Textual docs via MCP and implement accordingly):
  - Provide `Header()` and `Footer()` for global controls.
  - Use `VerticalScroll`/`Container` for long content and `Input()` for interactive fields.
  - Use `reactive` state to update status (e.g., `status = var('ready')`) and `watch_status` to update UI.

Safety and code-review checklist ⚠️
- Must include MCP doc citations in PR (which pages/examples were used).
- Avoid embedding system-level destructive logic (e.g., `docker system prune`, `taskkill`, `wsl --shutdown`) directly in UI logic. UI should call into a safe facade (a function that is well-tested and mocks shell calls in tests).
- For `wsl_docker_cleaner.py` and `quick_wsl_cleanup.py`, only align UI with Textual when it replaces or adds interactive views; always keep the destructive operations explicit and request confirmation from the user with a clear warning prompt.

Testing and examples
- Add unit tests for UI logic that do not run shells: create fixtures that mock `subprocess.run`, `Optimize-VHD` and `ctypes` admin checks.
- For Textual components, add small programmatic tests that instantiate `App` objects and assert the presence of widgets and reactive updates.

-- End of Textualize & UV section --

-- End of file --
