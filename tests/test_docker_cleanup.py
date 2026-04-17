import subprocess

import docker_cleaner.core as core
from docker_cleaner.core import WSLDockerCleaner


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
    assert 'taskkill /F /IM "Docker Desktop.exe" /T 2>nul' in command
    assert 'taskkill /F /IM "Docker.exe" /T 2>nul' in command
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

    def fake_run_command(command: str, capture_output=True, shell=True):
        assert command == "wsl -l -v"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="docker-desktop\n", stderr="")

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
    assert (tmp_path / ".wslconfig").exists()
    assert not any(level == "ERROR" for level, _message in log_messages)


def test_compact_vhdx_files_requests_elevation_and_falls_back(monkeypatch, tmp_path):
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
    monkeypatch.setattr(core.time, "sleep", lambda *_args, **_kwargs: None)

    def fake_run_command(command: str, capture_output=True, shell=True):
        assert command == "wsl --shutdown"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    def fake_run_elevated_command(command: str, stream_callback=None):
        captured_commands.append(command)
        if len(captured_commands) == 1:
            return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="diskpart failed")
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cleaner, "run_command", fake_run_command)
    monkeypatch.setattr(cleaner, "run_elevated_command", fake_run_elevated_command)

    assert cleaner.compact_vhdx_files() is True
    assert len(captured_commands) == 2
    assert captured_commands[0].startswith("diskpart /s ")
    assert 'Optimize-VHD -Path' in captured_commands[1]
    assert not any(level == "ERROR" for level, _message in log_messages)