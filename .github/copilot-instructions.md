# Copilot Instructions — Docker-Clennear

## Purpose & Architecture

This repo provides **Windows-only** WSL/Docker cleanup tools and LMArena model parsing utilities:

- **Docker Cleaner** (`docker_cleaner/core.py`, `cli/`, `main.py`) — Reclaims WSL/Docker space via pruning, VHDX compaction, and temp file cleanup
- **LMArena Generator** (`lmarena/generator.py`) — Extracts `initialModels` from raw LMArena dumps and generates Python code with model lists

**Key architectural pattern**: Dual execution model (sync + async) in `WSLDockerCleaner`:
- Sync methods (`docker_cleanup()`, `compact_vhdx_files()`) for CLI/Rich UI
- Async methods (`docker_cleanup_async()`, `compact_vhdx_files_async()`) for Textual TUI with real-time streaming via callbacks
- Both use `run_command()`/`run_command_async()` with `shell=True` for Windows commands

## Critical Files & Flows

**Docker Cleaner core** (`docker_cleaner/core.py`):
- `WSLDockerCleaner` class with methods: `docker_cleanup`, `stop_docker_wsl`, `configure_wsl_sparse`, `compact_vhdx_files`, `cleanup_temp_files`
- Admin elevation: `is_admin()` + `run_as_admin()` using `ctypes.windll.shell32.ShellExecuteW(None, "runas", ...)`
- Async variants (`*_async`) accept `stream_callback: Callable[[str], None]` for line-by-line output streaming

**Textual TUI** (`main.py`):
- `CommandRunnerApp`: Main app with sidebar buttons, `RichLog` output widget, and progress tracking
- `CleanupOptionsScreen`: Modal with checkboxes for granular cleanup steps (containers, images, volumes, etc.)
- Preferences saved to `~/.docker_clennear_prefs.json` (JSON dict mapping `opt_*` checkbox IDs to bool)
- `@work` decorated methods (`_run_prune_*`, `_run_compact_vhdx`) execute async operations as Textual workers
- **Auto-elevation**: `main.py` checks admin status on startup and re-launches with UAC if needed (Windows only)

**Logging system** (`cli/richlog.py`):
- `DailyLogWriter`: File-like object that writes to `logs/YYYY-MM-DD.log` (daily rotation) + optional UI callback
- All app logging routes through `write_ui_log()` → `DailyLogWriter` → both file and UI widget
- Exception hooks installed in `on_mount()` capture unhandled exceptions (Python `excepthook`, `asyncio`, `threading`)

**LMArena Generator** (`lmarena/generator.py`):
- `ModelsGenerator.extract_initial_models(raw_data)` — Regex-based extraction of `initialModels: [...]` JSON arrays
- Generates `models`, `text_models`, `image_models`, `vision_models` dicts based on capabilities
- Output: `<input>_models.py` (e.g., `lmarena_models_models.py`)

## Developer Workflows

**Setup**:
```powershell
& .\.venv\Scripts\Activate.ps1  # Use existing .venv or create new
# Dependencies tracked in pyproject.toml: rich, textual, pytest
```

**Running cleaners**:
```powershell
python main.py                          # TUI with auto-elevation (recommended)
python -m cli.main_cleaner              # Full cleanup CLI (elevates if needed)
python -m cli.quick_cleanup             # Quick prune-only CLI
python -m cli.admin_tasks compact_vhdx  # Admin helper for specific task
```

**Running model generator**:
```powershell
python -m lmarena.generator lmarena_models.txt  # Outputs lmarena_models_models.py
```

**Testing**:
```powershell
pytest tests/                           # Unit tests (mock subprocess/ctypes)
pytest tests/test_generator.py         # LMArena parser tests (pure Python)
```

## Project Conventions

**Windows-specific patterns**:
- All shell commands use `subprocess.run(..., shell=True)` for Windows compatibility
- Platform checks: `sys.platform.startswith('win')` guard destructive operations
- VHDX paths: `%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx` and `distro\ext4.vhdx`

**Admin & UAC flow**:
- `is_admin()` checks via `ctypes.windll.shell32.IsUserAnAdmin()`
- `run_as_admin()` uses `ShellExecuteW("runas")` to trigger UAC and relaunch
- **Never bypass UAC** — always preserve elevation flow for security

**Streaming output pattern** (Textual UI):
- Async methods accept `stream_callback: Callable[[str], None]`
- `run_command_async()` reads stdout/stderr line-by-line via `asyncio.subprocess.PIPE`
- UI calls `self.write_ui_log(text)` which uses `call_from_thread()` for thread-safe widget updates

**Logging conventions**:
- `WSLDockerCleaner.log(message, level)` writes to `self.log_messages` + Rich console + Python logging
- UI logging via `DailyLogWriter` persists to `logs/YYYY-MM-DD.log` with timestamps
- When adding features, use `self.write_ui_log()` in UI context or `self.log()` in cleaner logic

## Integration Points

**Docker CLI commands** (parsed for `"Total reclaimed space"`):
- `docker system prune -af --volumes` (⚠️ destructive)
- `docker container prune -f`, `docker image prune -af`, `docker volume prune -f`
- `docker network prune -f`, `docker builder prune -af`

**Windows system commands**:
- `taskkill /F /IM "Docker Desktop.exe"` (kills Docker processes)
- `wsl --shutdown` (stops all WSL distributions)
- `powershell -Command "Optimize-VHD -Path '...' -Mode Full"` (requires admin)

**Textual framework** (v6.6.0+):
- Use `compose()` for widget layouts (not raw render methods)
- Use `reactive`/`var` for state + `watch_*` callbacks for reactive updates
- `@work(exclusive=True)` decorator for async workers, `@work(thread=True)` for sync workers
- CSS styling via app-level `CSS` string or external files

## Safety Requirements

**Destructive operations** — Always require explicit user confirmation:
- `docker system prune -af --volumes` deletes all unused containers/images/volumes
- `taskkill /F` force-kills Docker Desktop processes
- `wsl --shutdown` stops all WSL distributions
- `Optimize-VHD` compacts VHDX files (requires admin, can take minutes)

**Testing destructive code**:
- Mock `subprocess.run` and `ctypes.windll.shell32` in tests (see `tests/test_admin_compact.py`)
- Never run actual `docker prune`, `taskkill`, or `Optimize-VHD` in CI
- Test admin logic by mocking `IsUserAnAdmin()` return value

**Shell command safety**:
- Commands use `shell=True` — be careful with user input to avoid injection
- Parse Docker output for `"Total reclaimed space:"` string (fragile to CLI changes)
- If changing to `shell=False`, update all command strings to list format

## Textual UI Guidelines

**Before implementing any UI feature, consult Textual docs via MCP**:
1. `mcp_mcp_docker_resolve-library-id('textualize/textual')`
2. `mcp_mcp_docker_get-library-docs('/textualize/textual', topic='<relevant-topic>')`
   - Topics: `compose`, `widgets`, `reactivity`, `workers`, `screens`

### Core Textual Patterns

**Composing widgets** — Use `compose()` method to build UI layout:
```python
def compose(self) -> ComposeResult:
    yield Header()
    with Container():
        yield Button("Click me", id="my-button")
        yield Static("Hello", id="greeting")
    yield Footer()
```

**Reactive attributes** — Auto-update UI when values change:
```python
from textual.reactive import reactive, var

class MyWidget(Widget):
    # reactive() triggers refresh/layout
    count = reactive(0)
    
    # var() doesn't trigger refresh (lightweight)
    color = var("blue")
    
    def watch_count(self, old_value: int, new_value: int) -> None:
        """Called automatically when count changes"""
        self.query_one("#counter").update(f"Count: {new_value}")
```

**Workers** — Background tasks without blocking UI:
```python
# Async worker (recommended for I/O-bound tasks)
@work(exclusive=True)
async def fetch_data(self) -> None:
    result = await self.run_command_async("docker ps", stream_callback=self.write_ui_log)
    self.query_one("#output").update(result.stdout)

# Thread worker (for blocking/CPU-bound tasks)
@work(thread=True)
def heavy_computation(self) -> None:
    # Use call_from_thread to update UI from worker
    self.call_from_thread(self.update_status, "Working...")
    result = expensive_operation()
    self.call_from_thread(self.update_status, f"Done: {result}")
```

**Screens** — Modal dialogs and navigation:
```python
# Define screen
class ConfirmDialog(Screen):
    def compose(self) -> ComposeResult:
        yield Static("Are you sure?")
        yield Button("Yes", id="yes")
        yield Button("No", id="no")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

# Show screen and wait for result
async def ask_user(self) -> None:
    result = await self.push_screen(ConfirmDialog(), wait_for_dismiss=True)
    if result:
        self.do_action()
```

**Event handling** — Two approaches:
```python
# Method 1: on_<widget>_<event> naming convention
def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "submit":
        self.submit_form()

# Method 2: @on decorator with CSS selectors (preferred for specific widgets)
from textual import on

@on(Button.Pressed, "#submit")
def handle_submit(self) -> None:
    self.submit_form()

@on(Input.Changed)
def handle_input_changed(self, event: Input.Changed) -> None:
    self.validate_input(event.value)
```

**Querying widgets** — Access widgets after composition:
```python
# Get single widget (raises NoMatches if not found)
button = self.query_one("#my-button", Button)

# Get all matching widgets
all_buttons = self.query(Button)
for button in all_buttons:
    button.disabled = True

# CSS-style selectors
self.query_one(".warning", Static).update("⚠️ Warning!")
```

**Context managers for containers**:
```python
def compose(self) -> ComposeResult:
    with Vertical():
        yield Label("Top")
        with Horizontal():
            yield Button("Left")
            yield Button("Right")
        yield Label("Bottom")
```

### Established patterns in this project (see `main.py`)

- Modal screens: `Screen` subclass with `push_screen(..., wait_for_dismiss=True)`
- Worker pattern: `@work` decorated methods + `write_ui_log()` via `call_from_thread()`
- Progress tracking: Custom `start_progress()`, `update_progress()`, `finish_progress()` using Rich `Progress` rendered in `Static` widget
- Checkbox persistence: Save to `~/.docker_clennear_prefs.json`, load defaults in `CleanupOptionsScreen.on_mount()`

### Testing Textual components

**Unit testing with `run_test()`** — Run apps in headless mode:
```python
import pytest
from textual.app import App
from textual.widgets import Button

# Basic test structure
async def test_button_click():
    """Test button interaction."""
    app = MyApp()
    async with app.run_test() as pilot:
        # Simulate button click
        await pilot.click("#my-button")
        # Assert state changes
        assert app.some_state == expected_value
```

**Pilot API** — Interact with the app during tests:
```python
async with app.run_test() as pilot:
    # Click widgets
    await pilot.click("#button-id")
    await pilot.click(Button)  # Click by type
    await pilot.click(offset=(10, 5))  # Click at coordinates
    
    # Press keys
    await pilot.press("enter")
    await pilot.press("h", "e", "l", "l", "o")
    await pilot.press("ctrl+s")
    
    # Hover over widgets
    await pilot.hover("#widget-id")
    
    # Wait for UI updates
    await pilot.pause()  # Wait for pending messages
    await pilot.pause(delay=0.1)  # Wait + delay
```

**Testing reactive attributes**:
```python
async def test_counter():
    """Test reactive counter updates UI."""
    app = CounterApp()
    async with app.run_test() as pilot:
        # Initial state
        assert app.count == 0
        
        # Trigger increment
        await pilot.click("#increment")
        await pilot.pause()
        
        # Verify reactive update
        assert app.count == 1
        assert app.query_one("#counter").renderable == "Count: 1"
```

**Testing workers**:
```python
async def test_background_task():
    """Test async worker completion."""
    app = WorkerApp()
    async with app.run_test() as pilot:
        # Start worker
        await pilot.click("#start-task")
        
        # Wait for worker to complete
        await pilot.pause(delay=1.0)
        
        # Verify result
        status = app.query_one("#status")
        assert "completed" in status.renderable.lower()
```

**Snapshot testing** — Visual regression tests:
```python
# Install: pip install pytest-textual-snapshot

def test_app_appearance(snap_compare):
    """Test visual appearance matches snapshot."""
    # First run generates snapshot (will fail)
    # Subsequent runs compare against saved snapshot
    assert snap_compare("path/to/app.py")

def test_with_interactions(snap_compare):
    """Test appearance after interactions."""
    assert snap_compare(
        "path/to/app.py",
        press=["tab", "enter"],  # Simulate key presses
        terminal_size=(100, 50),  # Custom terminal size
    )

# Update snapshots after verifying changes
# pytest --snapshot-update
```

**Testing screens and modals**:
```python
async def test_modal_dialog():
    """Test modal screen interaction."""
    app = MyApp()
    async with app.run_test() as pilot:
        # Push modal screen
        await pilot.click("#show-dialog")
        await pilot.pause()
        
        # Verify modal is shown
        assert isinstance(app.screen, DialogScreen)
        
        # Interact with modal
        await pilot.click("#confirm")
        await pilot.pause()
        
        # Verify modal dismissed
        assert not isinstance(app.screen, DialogScreen)
```

**Custom terminal size for tests**:
```python
async def test_responsive_layout():
    """Test layout at different screen sizes."""
    app = MyApp()
    # Set custom terminal size
    async with app.run_test(size=(120, 40)) as pilot:
        # Test layout behavior
        widget = app.query_one("#responsive-widget")
        assert widget.size.width == 120
```

**Testing project patterns** (see `tests/`):
- Mock `subprocess.run` for shell commands
- Mock `ctypes.windll.shell32` for admin checks
- Never run actual Docker/WSL commands in tests
- Use `@pytest.fixture` for app instances
- Test both sync and async variants of methods

## Common Tasks & Examples

**Adding a new cleanup operation**:
1. Add sync method to `WSLDockerCleaner` (e.g., `def new_cleanup(self): ...`)
2. Add async variant: `async def new_cleanup_async(self, stream_callback=None): ...`
3. Add `@work` decorated worker method to `CommandRunnerApp` (e.g., `_run_new_cleanup()`)
4. Add checkbox to `CleanupOptionsScreen.compose()` with ID `opt_new_cleanup`
5. Handle checkbox in `on_button_pressed(event)` for "opts_exec" button
6. Update `~/.docker_clennear_prefs.json` default in `docker_options` handler

**Adding new tests**:
```python
# Mock subprocess for Windows commands
from unittest.mock import patch, MagicMock

@patch('subprocess.run')
def test_docker_cleanup(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="Total reclaimed space: 1.5GB")
    cleaner = WSLDockerCleaner()
    result = cleaner.docker_cleanup()
    assert result is True
    assert mock_run.called
```

**Creating custom widgets**:
```python
# Simple widget with render method
class HelloWorld(Widget):
    def render(self) -> str:
        return "[b]Hello[/b] World"

# Widget with embedded CSS
class StyledWidget(Widget):
    DEFAULT_CSS = """
        StyledWidget {
            background: blue;
            color: white;
            padding: 1 2;
        }
    """
    
    def render(self) -> str:
        return "Styled Content"

# Widget with compose (compound widget)
class InputWithLabel(Container):
    def __init__(self, label: str, **kwargs):
        super().__init__(**kwargs)
        self.label_text = label
    
    def compose(self) -> ComposeResult:
        yield Label(self.label_text)
        yield Input(placeholder="Enter text...")

# Widget with reactive state
class Counter(Static):
    count = reactive(0)
    
    def watch_count(self, count: int) -> None:
        self.update(f"Count: {count}")
```

**Adding animations**:
```python
# Animate opacity (fade out)
widget.styles.animate("opacity", value=0.0, duration=2.0)

# Animate background color
widget.styles.animate("background", value="blue", duration=0.5)

# Animate offset (move widget)
widget.styles.animate("offset", value=(10, 5), duration=1.0)

# Animated gradient background
class AnimatedWidget(Widget):
    gradient_offset = var(0.0)
    
    def on_mount(self) -> None:
        self.set_interval(1/30, self.update_animation)
    
    def update_animation(self) -> None:
        self.gradient_offset += 0.01
        self.refresh()
    
    def render(self) -> LinearGradient:
        return LinearGradient(
            Color(0, 0, 255),
            Color(0, 255, 255),
            Color(255, 0, 255)
        ).shift(self.gradient_offset)
```

**Styling widgets**:
```python
# Programmatic styling
widget.styles.background = "blue"
widget.styles.border = ("heavy", "white")
widget.styles.padding = (1, 2)

# CSS styling (in app or widget)
CSS = """
#my-widget {
    background: $primary;
    border: solid green;
    text-align: center;
}

.warning {
    background: red;
    color: white;
}
"""

# Border titles and subtitles
widget.border_title = "Title"
widget.border_subtitle = "Subtitle"
widget.styles.border_title_align = "center"

# Component classes for sub-parts
class CustomWidget(Widget):
    COMPONENT_CLASSES = {
        "custom--header",
        "custom--body",
        "custom--footer"
    }
    
    DEFAULT_CSS = """
    CustomWidget .custom--header {
        background: blue;
    }
    CustomWidget .custom--body {
        background: white;
    }
    """
```

**Debugging streaming issues**:
- Check `stream_callback` is called with `\n`-terminated strings
- Verify `call_from_thread()` is used when writing from worker threads
- Ensure `PYTHONUNBUFFERED=1` env var is set for subprocesses (see `run_python_script()`)

## Dependencies & Package Management

**Current dependencies** (`pyproject.toml`):
- `rich>=14.2.0` (console UI, progress bars, tables)
- `textual>=6.6.0` (TUI framework)
- `pytest>=9.0.1` (testing)

**Package management**:
- Standard workflow: `pip install -e .` or `pip install rich textual pytest`
- If using `uv` (optional): `uv add <package>`, `uv sync`, `uv run python main.py`
- When adding packages, update `pyproject.toml` dependencies list

## Notes for AI Agents

- **Prefer read-only changes** for exploratory work: add tests, static analysis, or documentation
- **Always call out destructive operations** in code review comments (ask maintainers about `--dry-run` options)
- **Update README.md** when changing CLI behavior, adding flags, or modifying workflows
- **Include MCP doc references** in PRs touching Textual, Docker CLI, or Windows APIs (library ID + topic + code snippet)
- **Do not bypass UAC/admin checks** — respect security boundaries for elevation
- **Mock external calls in tests** — never run `docker prune`, `taskkill`, `wsl --shutdown`, or `Optimize-VHD` in CI
