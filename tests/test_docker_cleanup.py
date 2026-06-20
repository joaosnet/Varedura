import base64
import io
import json
import re
import subprocess
import sys

import pytest
from rich.console import Console

import cli.quick_cleanup as quick
import docker_cleaner.core as core
import mcp_server.server as mcp_server
from docker_cleaner.core import CleanupStepResult, WSLDockerCleaner


def test_docker_cleanup_preserves_running_containers(monkeypatch):
    cleaner = WSLDockerCleaner()
    commands = []

    monkeypatch.setattr(cleaner, "is_docker_running", lambda: True)
    monkeypatch.setattr(cleaner, "log", lambda *_args, **_kwargs: None)

    def fake_run_command(command: str, capture_output=True, shell=True):
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="Total reclaimed space: 0B", stderr="")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)

    assert cleaner.docker_cleanup() is True
    assert "docker ps -q" not in commands
    assert not any(command.startswith("docker stop ") for command in commands)
    assert commands == [
        "docker container prune -f",
        "docker image prune -af",
        "docker volume prune -f",
        "docker network prune -f",
        "docker system prune -af --volumes",
        "docker builder prune -af",
    ]


def test_container_step_only_prunes_stopped_containers(monkeypatch):
    cleaner = WSLDockerCleaner()
    commands = []

    monkeypatch.setattr(cleaner, "is_docker_running", lambda: True)
    monkeypatch.setattr(cleaner, "log", lambda *_args, **_kwargs: None)

    def fake_run_command(command: str, capture_output=True, shell=True):
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="Total reclaimed space: 0B", stderr="")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)

    assert cleaner.docker_cleanup(prune_only="containers") is True
    assert commands == ["docker container prune -f"]


def test_image_step_does_not_stop_containers_before_prune(monkeypatch):
    cleaner = WSLDockerCleaner()
    commands = []

    monkeypatch.setattr(cleaner, "is_docker_running", lambda: True)
    monkeypatch.setattr(cleaner, "log", lambda *_args, **_kwargs: None)

    def fake_run_command(command: str, capture_output=True, shell=True):
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="Total reclaimed space: 0B", stderr="")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)

    assert cleaner.docker_cleanup(prune_only="images") is True
    assert commands == ["docker image prune -af"]


def test_windows_elevated_command_uses_temp_files_not_start_process_redirects(monkeypatch):
    monkeypatch.setattr(core, "IS_WINDOWS", True)
    temp_paths = iter(["C:\\tmp\\out.txt", "C:\\tmp\\err.txt", "C:\\tmp\\code.txt"])
    monkeypatch.setattr(core, "_temp_file_path", lambda suffix: next(temp_paths))

    command = WSLDockerCleaner()._build_windows_elevated_command("diskpart.exe /s C:\\tmp\\compact.txt")
    encoded = command.rsplit(" ", 1)[1]
    parent_script = base64.b64decode(encoded).decode("utf-16le")

    assert "-Verb RunAs" in parent_script
    assert "RedirectStandardOutput" not in parent_script
    assert "RedirectStandardError" not in parent_script
    assert "C:\\tmp\\out.txt" in parent_script
    assert "C:\\tmp\\err.txt" in parent_script
    assert "C:\\tmp\\code.txt" in parent_script


def test_powershell_clixml_progress_is_removed_from_stderr():
    clixml = """#< CLIXML
<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><Obj S="progress"><MS><PR N="Record"><AV>Preparando módulos para primeiro uso.</AV></PR></MS></Obj></Objs>
"""

    assert core._strip_powershell_clixml(clixml) == ""


def test_stop_docker_wsl_uses_elevated_batch_without_process_errors(monkeypatch):
    monkeypatch.setattr(core, "IS_WINDOWS", True)

    cleaner = WSLDockerCleaner()
    captured_commands = []
    log_messages = []

    monkeypatch.setattr(cleaner, "is_admin", lambda: False)
    monkeypatch.setattr(
        cleaner,
        "log",
        lambda message, level="INFO": log_messages.append((level, message)),
    )
    monkeypatch.setattr(core.time, "sleep", lambda *_args, **_kwargs: None)

    def fake_run_elevated_command(command: str, stream_callback=None):
        captured_commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cleaner, "run_elevated_command", fake_run_elevated_command)

    assert cleaner.stop_docker_wsl() is True
    assert len(captured_commands) == 1

    command = captured_commands[0]
    assert 'taskkill /F /IM "Docker Desktop.exe" /T 2>$null' in command
    assert 'taskkill /F /IM "Docker.exe" /T 2>$null' in command
    assert command.endswith("wsl --shutdown")
    assert not any(level == "ERROR" for level, _message in log_messages)


def test_configure_wsl_sparse_elevates_manage_commands(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "IS_WINDOWS", True)

    cleaner = WSLDockerCleaner()
    captured_commands = []
    log_messages = []

    monkeypatch.setattr(cleaner, "is_admin", lambda: False)
    monkeypatch.setattr(
        cleaner,
        "log",
        lambda message, level="INFO": log_messages.append((level, message)),
    )

    monkeypatch.setattr(
        core.os.path,
        "expanduser",
        lambda path: str(tmp_path / ".wslconfig") if path == "~/.wslconfig" else path,
    )
    (tmp_path / ".wslconfig").write_text("[wsl2]\nmemory=8GB\nprocessors=6\n", encoding="utf-8")

    def fake_run_command(command: str, capture_output=True, shell=True):
        assert command == "wsl -l -v"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="docker-desktop\n docker-desktop-data\n", stderr="")

    def fake_run_elevated_command(command: str, stream_callback=None):
        captured_commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)
    monkeypatch.setattr(cleaner, "run_elevated_command", fake_run_elevated_command)

    assert cleaner.configure_wsl_sparse() is True
    assert len(captured_commands) == 1

    command = captured_commands[0]
    assert 'wsl --manage "docker-desktop" --set-sparse true' in command
    assert 'wsl --manage "docker-desktop-data" --set-sparse true' in command
    wslconfig = (tmp_path / ".wslconfig").read_text(encoding="utf-8")
    assert "memory=8GB" in wslconfig
    assert "processors=6" in wslconfig
    assert "sparseVhd=true" in wslconfig
    assert not any(level == "ERROR" for level, _message in log_messages)


def test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "IS_WINDOWS", True)

    cleaner = WSLDockerCleaner()
    captured_commands = []
    log_messages = []

    monkeypatch.setattr(
        cleaner,
        "log",
        lambda message, level="INFO": log_messages.append((level, message)),
    )
    monkeypatch.setattr(
        core.os.path,
        "expanduser",
        lambda path: str(tmp_path / ".wslconfig") if path == "~/.wslconfig" else path,
    )

    def fake_run_command(command: str, capture_output=True, shell=True):
        assert command == "wsl -l -v"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="Ubuntu\n", stderr="")

    def fake_run_elevated_command(command: str, stream_callback=None):
        captured_commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="should not run")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)
    monkeypatch.setattr(cleaner, "run_elevated_command", fake_run_elevated_command)

    assert cleaner.configure_wsl_sparse() is True
    assert captured_commands == []
    assert "sparseVhd=true" in (tmp_path / ".wslconfig").read_text(encoding="utf-8")
    assert not any(level == "ERROR" for level, _message in log_messages)


def test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "IS_WINDOWS", True)

    cleaner = WSLDockerCleaner()
    log_messages = []

    monkeypatch.setattr(cleaner, "is_admin", lambda: False)
    monkeypatch.setattr(
        cleaner,
        "log",
        lambda message, level="INFO": log_messages.append((level, message)),
    )
    monkeypatch.setattr(
        core.os.path,
        "expanduser",
        lambda path: str(tmp_path / ".wslconfig") if path == "~/.wslconfig" else path,
    )

    def fake_run_command(command: str, capture_output=True, shell=True):
        assert command == "wsl -l -v"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="docker-desktop\n", stderr="")

    def fake_run_elevated_command(command: str, stream_callback=None):
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="set-sparse unsupported")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)
    monkeypatch.setattr(cleaner, "run_elevated_command", fake_run_elevated_command)

    assert cleaner.configure_wsl_sparse() is True
    assert "sparseVhd=true" in (tmp_path / ".wslconfig").read_text(encoding="utf-8")
    assert any(level == "WARNING" and "set-sparse unsupported" in message for level, message in log_messages)


def test_compact_vhdx_files_requests_elevation_and_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "IS_WINDOWS", True)
    monkeypatch.setenv("TEMP", str(tmp_path))

    cleaner = WSLDockerCleaner()
    captured_commands = []
    diskpart_scripts = []
    log_messages = []
    vhdx_path = tmp_path / "ext4.vhdx"
    vhdx_path.write_bytes(b"placeholder")

    monkeypatch.setattr(cleaner, "is_admin", lambda: False)
    monkeypatch.setattr(
        cleaner,
        "log",
        lambda message, level="INFO": log_messages.append((level, message)),
    )
    monkeypatch.setattr(cleaner, "_get_all_vhdx_paths", lambda: [str(vhdx_path)])
    monkeypatch.setattr(cleaner, "_diskpart_exe", lambda: r"C:\Windows\System32\diskpart.exe")
    monkeypatch.setattr(core.time, "sleep", lambda *_args, **_kwargs: None)

    def fake_run_command(command: str, capture_output=True, shell=True):
        if command == "wsl -l -v":
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
        if command == "wsl --shutdown":
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
        if command.startswith("wsl -d ") and "-- echo ok" in command:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")
        if "Get-Command Optimize-VHD" in command:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="Optimize-VHD\n", stderr="")
        raise AssertionError(command)

    def fake_run_elevated_command(command: str, stream_callback=None):
        captured_commands.append(command)
        if len(captured_commands) == 1:
            script_path = re.search(r'/s "([^"]+)"', command).group(1)
            diskpart_scripts.append((tmp_path / script_path).read_text(encoding="utf-8") if not re.match(r"^[A-Za-z]:", script_path) else open(script_path, encoding="utf-8").read())
            return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="diskpart failed")
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)
    monkeypatch.setattr(cleaner, "run_elevated_command", fake_run_elevated_command)

    assert cleaner.compact_vhdx_files() is True
    assert len(captured_commands) == 2
    assert captured_commands[0].startswith('& "C:\\Windows\\System32\\diskpart.exe" /s ')
    assert f'select vdisk file="{vhdx_path}"' in diskpart_scripts[0]
    assert "attach vdisk readonly" in diskpart_scripts[0]
    assert "compact vdisk" in diskpart_scripts[0]
    assert "detach vdisk" in diskpart_scripts[0]
    assert "Optimize-VHD -Path" in captured_commands[1]
    assert not any(level == "ERROR" for level, _message in log_messages)


def test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "IS_WINDOWS", True)
    monkeypatch.setenv("TEMP", str(tmp_path))

    cleaner = WSLDockerCleaner()
    captured_commands = []
    log_messages = []
    vhdx_path = tmp_path / "ext4.vhdx"
    vhdx_path.write_bytes(b"placeholder")

    monkeypatch.setattr(cleaner, "is_admin", lambda: False)
    monkeypatch.setattr(
        cleaner,
        "log",
        lambda message, level="INFO": log_messages.append((level, message)),
    )
    monkeypatch.setattr(cleaner, "_get_all_vhdx_paths", lambda: [str(vhdx_path)])
    monkeypatch.setattr(cleaner, "_diskpart_exe", lambda: r"C:\Windows\System32\diskpart.exe")
    monkeypatch.setattr(core.time, "sleep", lambda *_args, **_kwargs: None)

    def fake_run_command(command: str, capture_output=True, shell=True):
        if command == "wsl -l -v":
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
        if command == "wsl --shutdown":
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
        if command.startswith("wsl -d ") and "-- echo ok" in command:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")
        if "Get-Command Optimize-VHD" in command:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
        raise AssertionError(command)

    def fake_run_elevated_command(command: str, stream_callback=None):
        captured_commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="diskpart failed")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)
    monkeypatch.setattr(cleaner, "run_elevated_command", fake_run_elevated_command)

    assert cleaner.compact_vhdx_files() is False
    assert len(captured_commands) == 1
    assert any(level == "ERROR" and "Optimize-VHD" in message for level, message in log_messages)


def test_quick_cleanup_reuses_central_cleaner(monkeypatch):
    calls = []

    class FakeCleaner:
        def __init__(self, console=None):
            self.console = console

        def docker_cleanup(self, steps=None):
            calls.append(("docker_cleanup", steps))
            return True

        def stop_docker_wsl(self):
            calls.append(("stop_docker_wsl", None))
            return True

        def compact_vhdx_files(self):
            calls.append(("compact_vhdx_files", None))
            return True

    monkeypatch.setattr(quick, "WSLDockerCleaner", FakeCleaner)

    assert quick.quick_cleanup(Console(file=io.StringIO())) is True
    assert calls == [
        ("docker_cleanup", ("containers", "images", "volumes", "networks", "system", "builder")),
        ("stop_docker_wsl", None),
        ("compact_vhdx_files", None),
    ]


def test_mcp_quick_cleanup_reuses_central_cleaner(monkeypatch):
    calls = []

    class FakeCleaner:
        def __init__(self):
            self.last_cleanup_results = [
                CleanupStepResult(
                    step="containers",
                    success=True,
                    command="docker container prune -f",
                    returncode=0,
                )
            ]

        def docker_cleanup(self, steps=None):
            calls.append(steps)
            self.steps = steps
            return True

    monkeypatch.setattr(mcp_server, "WSLDockerCleaner", FakeCleaner)
    monkeypatch.setattr(mcp_server, "_is_docker_running", lambda: True)

    payload = json.loads(mcp_server.docker_quick_cleanup(confirmed=True))

    assert payload["executed"] is True
    assert payload["success"] is True
    assert payload["running_containers_preserved"] is True
    assert payload["steps"][0]["command"] == "docker container prune -f"
    assert calls == [("containers", "images", "volumes", "networks", "system", "builder")]


def test_mcp_quick_cleanup_requires_confirmation(monkeypatch):
    """The destructive tool must not run without explicit confirmation."""
    calls = []

    class FakeCleaner:
        def __init__(self):
            self.last_cleanup_results = []

        def docker_cleanup(self, steps=None):
            calls.append(steps)
            return True

    monkeypatch.setattr(mcp_server, "WSLDockerCleaner", FakeCleaner)
    monkeypatch.setattr(mcp_server, "_is_docker_running", lambda: True)

    # Default call: no confirmation -> nothing executed.
    payload = json.loads(mcp_server.docker_quick_cleanup())
    assert payload["executed"] is False
    assert payload["requires_confirmation"] is True
    assert calls == []

    # Dry run: preview only -> still nothing executed.
    preview = json.loads(mcp_server.docker_quick_cleanup(dry_run=True))
    assert preview["executed"] is False
    assert preview["dry_run"] is True
    assert calls == []


def test_mcp_full_cleanup_requires_confirmation(monkeypatch):
    """Full cleanup is destructive + admin and must gate on confirmation."""
    monkeypatch.setattr(
        mcp_server, "WSLDockerCleaner", lambda: pytest.fail("must not instantiate cleaner")
    )

    payload = json.loads(mcp_server.docker_full_cleanup())
    assert payload["executed"] is False
    assert payload["requires_confirmation"] is True
    # VHDX compaction must appear in the disclosed action list.
    assert any("VHDX" in action or "Compact" in action for action in payload["actions"])


def test_parse_wsl_distros_drops_shell_metacharacters():
    """Distro names are interpolated into shell=True commands, so any name with
    shell metacharacters must be rejected (command-injection hardening)."""
    cleaner = WSLDockerCleaner()
    output = "\n".join(
        [
            "  NAME              STATE   VERSION",
            "* docker-desktop    Running 2",
            "  docker-desktop-data Running 2",
            "  evil`touch pwned`   Running 2",
            "  bad;rm -rf /        Running 2",
            "  $(whoami)           Running 2",
        ]
    )

    distros = cleaner._parse_wsl_distros(output)

    assert "docker-desktop" in distros
    assert "docker-desktop-data" in distros
    assert all(
        token not in distros
        for token in ("evil`touch", "bad;rm", "$(whoami)", "evil`touch pwned`")
    )
    assert all(re.match(r"^[A-Za-z0-9._-]+$", name) for name in distros)


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Exercises Windows %VAR% expansion and the WSL2 VHDX disk layout "
    "(os.path.expandvars only expands %VAR% on Windows)",
)
def test_get_docker_vhdx_paths_discovers_disk_layout(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "IS_WINDOWS", True)

    profile_root = tmp_path / "Users" / "joaod"
    localappdata_root = profile_root / "AppData" / "Local"
    docker_wsl_root = localappdata_root / "Docker" / "wsl"
    (docker_wsl_root / "data").mkdir(parents=True)
    (docker_wsl_root / "disk").mkdir(parents=True)

    docker_data_path = docker_wsl_root / "disk" / "docker_data.vhdx"
    ext4_path = docker_wsl_root / "data" / "ext4.vhdx"
    docker_data_path.write_bytes(b"docker-data")
    ext4_path.write_bytes(b"ext4-data")

    monkeypatch.setenv("LOCALAPPDATA", str(localappdata_root))
    monkeypatch.setenv("USERPROFILE", str(profile_root))

    paths = core.get_docker_vhdx_paths()

    assert paths == [str(docker_data_path), str(ext4_path)]
