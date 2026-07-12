import json
import subprocess
import sys


def _probe_modules(statement: str) -> dict[str, bool]:
    script = (
        "import json,sys; "
        + statement
        + "; names=['rich','textual','monitor.stalker','monitor.speed_providers',"
        "'requests','selenium','PIL','rtsp.scanner']; "
        "print(json.dumps({name:name in sys.modules for name in names}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return json.loads(result.stdout)


def test_entrypoint_import_is_a_lightweight_dispatcher():
    loaded = _probe_modules("import main")
    assert not any(loaded.values())


def test_textual_shell_defers_optional_backends_and_images():
    loaded = _probe_modules("import cli.textual_app")
    assert loaded["textual"]
    assert not loaded["monitor.speed_providers"]
    assert not loaded["requests"]
    assert not loaded["selenium"]
    assert not loaded["PIL"]
    assert not loaded["rtsp.scanner"]


def test_idle_speed_tester_does_not_materialize_providers():
    loaded = _probe_modules(
        "from monitor.speed_tester import get_speed_tester; get_speed_tester()"
    )
    assert not loaded["monitor.speed_providers"]
    assert not loaded["requests"]
    assert not loaded["selenium"]


def test_first_textual_frame_does_not_import_monitor_backends():
    script = r"""
import asyncio, json, socket, subprocess, sys, urllib.request
from cli.textual_app import VareduraTextualApp
def forbidden(*args, **kwargs):
    raise AssertionError("external I/O entered the first-frame path")
async def check():
    socket.getaddrinfo = forbidden
    socket.create_connection = forbidden
    subprocess.Popen = forbidden
    subprocess.run = forbidden
    urllib.request.urlopen = forbidden
    app = VareduraTextualApp()
    app._after_first_refresh = lambda: None
    app._animate_mascot = lambda: None
    async with app.run_test(size=(100, 36)):
        names = [
            "monitor.stalker", "monitor.speed_tester", "monitor.port_scanner",
            "monitor.speed_providers", "requests", "selenium", "PIL", "rtsp.scanner",
        ]
        print(json.dumps({name: name in sys.modules for name in names}))
asyncio.run(check())
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    loaded = json.loads(result.stdout.strip().splitlines()[-1])
    assert not any(loaded.values())
