import asyncio
import os
import sys
import tempfile
import io
import time
import subprocess
from unittest.mock import MagicMock

import pytest

from docker_cleaner.core import WSLDockerCleaner


def test_log_and_run_command_errors(monkeypatch):
    cleaner = WSLDockerCleaner()
    # Simulate subprocess.run returning error
    cp = subprocess.CompletedProcess(args="cmd", returncode=1, stdout="", stderr="fail")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: cp)
    res = cleaner.run_command("some-cmd")
    assert res is cp
    assert any("Erro:" in m for m in cleaner.log_messages)

    # Simulate timeout
    def raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd="cmd", timeout=1)
    monkeypatch.setattr(subprocess, "run", raise_timeout)
    res2 = cleaner.run_command("whatever")
    assert res2 is None
    assert any("Timeout" in m for m in cleaner.log_messages)


@pytest.mark.asyncio
async def test_run_command_async_stream(monkeypatch):
    cleaner = WSLDockerCleaner()
    outputs = []
    def cb(line):
        outputs.append(line)

    # Use Python to print - should work cross-platform
    cmd = f'{sys.executable} -c "print(\'hello async\')"'
    res = await cleaner.run_command_async(cmd, stream_callback=cb)
    assert res.returncode == 0
    assert any("hello async" in s for s in outputs)


def test_run_command_handles_generic_exception(monkeypatch):
    cleaner = WSLDockerCleaner()
    def raiser(*a, **k):
        raise ValueError("boom")
    monkeypatch.setattr(subprocess, "run", raiser)
    res = cleaner.run_command("cmd")
    assert res is None
    assert any("Erro ao executar comando" in m or "Erro" in m for m in cleaner.log_messages)


@pytest.mark.asyncio
async def test_run_command_async_handles_create_process_error(monkeypatch):
    cleaner = WSLDockerCleaner()
    async def fake_create_shell(*a, **k):
        raise ValueError("boom")
    monkeypatch.setattr(asyncio, "create_subprocess_shell", fake_create_shell)
    res = await cleaner.run_command_async("echo hi")
    assert res.returncode == -1
    assert "Erro ao executar comando" in res.stderr or "boom" in res.stderr


def test_run_elevated_command_invokes_run_command(monkeypatch):
    cleaner = WSLDockerCleaner()
    captured = {}
    def fake_run_command(cmd, **kwargs):
        # capture command and return ok
        captured['cmd'] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr(cleaner, "run_command", fake_run_command)
    cp = cleaner.run_elevated_command("Optimize-VHD -Path C:\\file.vhdx -Mode Full")
    assert cp.returncode == 0
    assert "Optimize-VHD" in captured['cmd']


def test_run_elevated_command_handles_error(monkeypatch):
    cleaner = WSLDockerCleaner()
    def fake(cmd, **k):
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout='', stderr='ps-error')
    monkeypatch.setattr(cleaner, "run_command", fake)
    res = cleaner.run_elevated_command("some cmd")
    assert res.returncode == 1
    assert any("Executando elevated" in m or "ps-error" in m for m in cleaner.log_messages)


def test_stop_docker_wsl_handles_error(monkeypatch):
    cleaner = WSLDockerCleaner()
    def fake_run(cmd, **k):
        if cmd.startswith('taskkill'):
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout='', stderr='')
        if 'wsl --shutdown' in cmd:
            return None
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_command', fake_run)
    res = cleaner.stop_docker_wsl()
    assert res is True
    assert any('Erro ao desligar WSL' in m or 'WSL desligado' in m for m in cleaner.log_messages)


def test_is_docker_running_and_admin(monkeypatch):
    cleaner = WSLDockerCleaner()
    # tasklist returns success and docker ps returns success
    def fake_run(cmd, **k):
        if "tasklist" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="found", stderr="")
        if cmd.strip().startswith("docker ps"):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="err")
    monkeypatch.setattr(cleaner, "run_command", fake_run)
    assert cleaner.is_docker_running() is True

    # test admin check using ctypes.patch
    class FakeWindll:
        class shell32:
            @staticmethod
            def IsUserAnAdmin():
                return True
    monkeypatch.setattr("ctypes.windll", FakeWindll())
    assert cleaner.is_admin() is True


def test_run_as_admin_calls_shellexecute_and_exits(monkeypatch):
    cleaner = WSLDockerCleaner()
    class Shell32:
        def ShellExecuteW(self, *a, **k):
            return 1
    class FakeShell:
        def __init__(self):
            self.shell32 = Shell32()
    monkeypatch.setattr("ctypes.windll", FakeShell())
    # Ensure sys.exit doesn't kill the test by catching SystemExit
    with pytest.raises(SystemExit):
        cleaner.run_as_admin()


def test_get_docker_vhdx_size(tmp_path, monkeypatch):
    cleaner = WSLDockerCleaner()
    # Set env LOCALAPPDATA and USERPROFILE to tmp_path
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    vhdx = tmp_path / "Docker" / "wsl" / "data"
    vhdx.mkdir(parents=True)
    p = vhdx / "ext4.vhdx"
    p.write_bytes(b"0" * 1024)
    total, files = cleaner.get_docker_vhdx_size()
    assert total > 0
    assert any(str(p) in f[0] for f in files)


def test_docker_cleanup_sync(monkeypatch):
    cleaner = WSLDockerCleaner()
    # Prepare a sequence of responses for various docker commands
    def fake_run(cmd, capture_output=True, text=True, shell=True, timeout=300):
        if 'docker ps -q' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='abc\n')
        if cmd.startswith('docker stop'):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='stopped')
        if 'docker container prune' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='Total reclaimed space: 1GB')
        if 'docker image prune' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='Total reclaimed space: 2GB')
        if 'docker volume prune' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='Total reclaimed space: 3GB')
        if 'docker system prune' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='Total reclaimed space: 6GB')
        if 'docker builder prune' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_command', fake_run)
    # Simulate docker running
    monkeypatch.setattr(cleaner, 'is_docker_running', lambda: True)
    # Now call docker_cleanup
    res = cleaner.docker_cleanup()
    assert res is True
    assert any('Espaço recuperado' in m for m in cleaner.log_messages)


def test_docker_cleanup_no_containers(monkeypatch):
    cleaner = WSLDockerCleaner()
    def fake_run(cmd, **k):
        if 'docker ps -q' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_command', fake_run)
    monkeypatch.setattr(cleaner, 'is_docker_running', lambda: True)
    res = cleaner.docker_cleanup()
    assert res is True
    assert any('Nenhum container em execução' in m for m in cleaner.log_messages)


def test_configure_wsl_sparse_sync(tmp_path, monkeypatch):
    cleaner = WSLDockerCleaner()
    # ensure expands to temp home
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    # Fake wsl -l -v to succeed
    def fake_run(cmd, **k):
        if 'wsl -l -v' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_command', fake_run)
    res = cleaner.configure_wsl_sparse()
    assert res is True
    assert os.path.exists(os.path.expanduser('~/.wslconfig'))


def test_configure_wsl_sparse_sync_error(monkeypatch):
    cleaner = WSLDockerCleaner()
    def fake_run(cmd, **k):
        if 'wsl -l -v' in cmd:
            return None
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_command', fake_run)
    res = cleaner.configure_wsl_sparse()
    assert res is False


def test_compact_vhdx_files(monkeypatch, tmp_path):
    cleaner = WSLDockerCleaner()
    # admin allowed
    monkeypatch.setattr(cleaner, "is_admin", lambda: True)
    # create two vhdx files
    base = tmp_path / "Docker" / "wsl" / "data"
    base.mkdir(parents=True)
    p = base / "ext4.vhdx"
    p.write_bytes(b"a" * 2048)

    # run_elevated_command should shrink the file (simulate compact)
    def fake_elev(cmd):
        # shrink file
        p.write_bytes(b"a")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(cleaner, "run_elevated_command", fake_elev)
    # Adjust expandvars to map to tmp_path
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    res = cleaner.compact_vhdx_files()
    assert res is True
    assert cleaner.total_space_saved > 0


def test_compact_vhdx_files_error(monkeypatch, tmp_path):
    cleaner = WSLDockerCleaner()
    monkeypatch.setattr(cleaner, "is_admin", lambda: True)
    # create path
    vdir = tmp_path / "Docker" / "wsl" / "data"
    vdir.mkdir(parents=True)
    p = vdir / "ext4.vhdx"
    p.write_bytes(b"x" * 1024)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    def fake_elev(cmd):
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout='', stderr='error')
    monkeypatch.setattr(cleaner, "run_elevated_command", fake_elev)
    res = cleaner.compact_vhdx_files()
    assert res is False
    assert any("Erro na compactação" in m or "error" in m for m in cleaner.log_messages)


def test_cleanup_temp_files_and_async(monkeypatch, tmp_path):
    cleaner = WSLDockerCleaner()
    # create temp directories and files
    t1 = tmp_path / "Temp"
    t1.mkdir()
    f1 = t1 / "foo.log"
    f1.write_text("log")
    monkeypatch.setenv("TEMP", str(t1))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    ldir = tmp_path / "Temp"
    ldir.mkdir(parents=True, exist_ok=True)
    f2 = ldir / "bar.tmp"
    f2.write_text("tmp")
    # call sync
    res = cleaner.cleanup_temp_files()
    assert res is True
    # call async
    outputs = []
    async def run_async():
        rv = await cleaner.cleanup_temp_files_async(stream_callback=lambda s: outputs.append(s))
        return rv
    rv = asyncio.run(run_async())
    assert isinstance(rv, bool)


@pytest.mark.asyncio
async def test_docker_cleanup_async_and_stop(monkeypatch):
    cleaner = WSLDockerCleaner()
    # monkeypatch run_command_async to provide fake CompletedProcess outputs
    async def fake_run(cmd, shell=True, stream_callback=None):
        # simulate outputs and return success
        if stream_callback:
            stream_callback(f"Ran: {cmd}\n")
        if 'docker ps -q' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='Total reclaimed space: 1GB', stderr='')
    monkeypatch.setattr(cleaner, "run_command_async", fake_run)
    outputs = []
    res = await cleaner.docker_cleanup_async(stream_callback=lambda s: outputs.append(s))
    assert res is True
    assert any("INICIANDO LIMPEZA" in o or "Ran:" in o for o in outputs)


@pytest.mark.asyncio
async def test_run_elevated_command_async_handles_error(monkeypatch):
    cleaner = WSLDockerCleaner()
    async def fake_run(cmd, shell=True, stream_callback=None):
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout='', stderr='err')
    monkeypatch.setattr(cleaner, 'run_command_async', fake_run)
    res = await cleaner.run_elevated_command_async('do-something', stream_callback=lambda s: None)
    assert res.returncode == 1
    assert 'err' in res.stderr


@pytest.mark.asyncio
async def test_stop_and_sparse_async(monkeypatch, tmp_path):
    cleaner = WSLDockerCleaner()
    # run_elevated_command_async returns success
    async def fake_elev(cmd, shell=True, stream_callback=None):
        if stream_callback:
            stream_callback("elevated\n")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(cleaner, "run_elevated_command_async", fake_elev)
    res = await cleaner.stop_docker_wsl_async(stream_callback=lambda s: None)
    assert res is True
    # configure sparse should write .wslconfig
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    res2 = await cleaner.configure_wsl_sparse_async(stream_callback=lambda s: None)
    assert res2 is True


def test_generate_report_and_run_full(monkeypatch, tmp_path):
    cleaner = WSLDockerCleaner()
    # create small vhdx file to allow get size
    d = tmp_path / "Docker" / "wsl" / "data"
    d.mkdir(parents=True)
    p = d / "ext4.vhdx"
    p.write_bytes(b"hello")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    # generate report should create log file
    cleaner.log_messages.append("dummy log")
    cleaner.generate_report()
    assert os.path.exists("wsl_docker_cleanup.log")
    # Now run full cleanup with monkeypatched sub-steps
    monkeypatch.setattr(cleaner, "is_admin", lambda: False)
    monkeypatch.setattr(cleaner, "get_docker_vhdx_size", lambda: (0, []))
    monkeypatch.setattr(cleaner, "docker_cleanup", lambda: True)
    monkeypatch.setattr(cleaner, "stop_docker_wsl", lambda: True)
    monkeypatch.setattr(cleaner, "configure_wsl_sparse", lambda: True)
    monkeypatch.setattr(cleaner, "compact_vhdx_files", lambda: True)
    monkeypatch.setattr(cleaner, "cleanup_temp_files", lambda: True)
    res = cleaner.run_full_cleanup_with_progress()
    assert res is True


def test_run_full_cleanup_with_progress_error(monkeypatch):
    cleaner = WSLDockerCleaner()
    monkeypatch.setattr(cleaner, 'is_admin', lambda: False)
    monkeypatch.setattr(cleaner, 'get_docker_vhdx_size', lambda: (0, []))
    def raise_error():
        raise RuntimeError('boom')
    monkeypatch.setattr(cleaner, 'docker_cleanup', raise_error)
    monkeypatch.setattr(cleaner, 'stop_docker_wsl', lambda: True)
    monkeypatch.setattr(cleaner, 'configure_wsl_sparse', lambda: True)
    monkeypatch.setattr(cleaner, 'compact_vhdx_files', lambda: True)
    monkeypatch.setattr(cleaner, 'cleanup_temp_files', lambda: True)
    res = cleaner.run_full_cleanup_with_progress()
    assert res is False


def test_display_info_and_final_report():
    cleaner = WSLDockerCleaner()
    cleaner.display_initial_info()
    cleaner.display_final_report(1.0, 0.5)


def test_main_behaviour(monkeypatch):
    # Test non-Windows exit
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(SystemExit):
        from docker_cleaner import core
        core.main()

    # Test Windows flow where we are not admin: should call run_as_admin and exit
    monkeypatch.setattr(sys, "platform", "win32")
    class C:
        def is_admin(self):
            return False
        def run_as_admin(self):
            raise SystemExit(0)
        def display_initial_info(self):
            pass
        def run_full_cleanup_with_progress(self):
            return True
    monkeypatch.setattr('docker_cleaner.core.WSLDockerCleaner', C)
    with pytest.raises(SystemExit):
        from docker_cleaner import core
        core.main()

    # Test Windows flow as admin: monkeypatch is_admin True and run functions
    class C2:
        def is_admin(self):
            return True
        def display_initial_info(self):
            pass
        def run_full_cleanup_with_progress(self):
            return True
    monkeypatch.setattr('docker_cleaner.core.WSLDockerCleaner', C2)
    # Monkeypatch input to avoid blocking
    monkeypatch.setattr('builtins.input', lambda *a, **k: '')
    # Running main should not raise
    from docker_cleaner import core
    core.main()


def test_exercise_all_methods(monkeypatch, tmp_path):
    """Call many WSLDockerCleaner methods with patched environment to exercise branches."""
    cleaner = WSLDockerCleaner()
    # Patch time.sleep to no-op so loops are fast
    monkeypatch.setattr(time, 'sleep', lambda *a, **k: None)

    # General run_command behavior: success for docker commands
    def run_cmd_sim(cmd, **k):
        if 'docker ps -q' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        if 'docker ps' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        if 'Find' in cmd or 'tasklist' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        # Return a sample Total reclaimed space line when prune is called
        if 'prune' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='Total reclaimed space: 1GB')
        if 'wsl -l -v' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='ok')
    monkeypatch.setattr(cleaner, 'run_command', run_cmd_sim)

    # run_command success path
    assert cleaner.run_command('echo 1')
    # run_command timeout simulated by raising (use a fresh cleaner to avoid previous monkeypatch)
    cleaner2 = WSLDockerCleaner()
    def raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd='x', timeout=1)
    monkeypatch.setattr(subprocess, 'run', raise_timeout)
    # Timeout path returns None
    assert cleaner2.run_command('true') is None
    # restore run to default simple result
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(args=a, returncode=0, stdout=''))
    

    # run_command_async: run a real python to test streaming quickly
    outputs = []
    async def cb(s):
        outputs.append(s)
    res = asyncio.run(cleaner.run_command_async(f'{sys.executable} -c "print(1)"', stream_callback=lambda s: outputs.append(s)))
    assert isinstance(res, subprocess.CompletedProcess)

    # run_elevated_command uses run_command - monkeypatch run_command
    monkeypatch.setattr(cleaner, 'run_command', lambda *a, **k: subprocess.CompletedProcess(args=a, returncode=0, stdout=''))
    ecp = cleaner.run_elevated_command('cmd')
    assert isinstance(ecp, subprocess.CompletedProcess)

    # is_docker_running false case
    monkeypatch.setattr(cleaner, 'run_command', lambda *a, **k: subprocess.CompletedProcess(args=a, returncode=1, stdout=''))
    assert cleaner.is_docker_running() is False
    # admin checks: simulate both
    class FakeWind:
        class shell32:
            @staticmethod
            def IsUserAnAdmin():
                return True
    monkeypatch.setattr('ctypes.windll', FakeWind())
    assert cleaner.is_admin() is True

    # run_as_admin raise due to ShellExecuteW raising -> exit
    class Shell32Ban:
        def ShellExecuteW(self, *a, **k):
            raise Exception('boom')
    class FakeShellBan:
        def __init__(self):
            self.shell32 = Shell32Ban()
    monkeypatch.setattr('ctypes.windll', FakeShellBan())
    with pytest.raises(SystemExit):
        cleaner.run_as_admin()

    # get_docker_vhdx_size: create files under LOCALAPPDATA and USERPROFILE
    vdir = tmp_path / "Docker" / "wsl" / "data"
    vdir.mkdir(parents=True)
    f = vdir / 'ext4.vhdx'
    f.write_bytes(b'x' * 1024)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    total, files = cleaner.get_docker_vhdx_size()
    assert total > 0

    # docker_cleanup path where docker is running: set run_command properly
    def rc_ok(cmd, **k):
        if 'docker ps -q' in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='Total reclaimed space: 1GB')
    monkeypatch.setattr(cleaner, 'run_command', rc_ok)
    monkeypatch.setattr(cleaner, 'is_docker_running', lambda: True)
    assert cleaner.docker_cleanup() is True

    # stop_docker_wsl: error path
    def rc_err(cmd, **k):
        if 'wsl --shutdown' in cmd:
            return None
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout='')
    monkeypatch.setattr(cleaner, 'run_command', rc_err)
    res = cleaner.stop_docker_wsl()
    assert res is True

    # cleanup_temp_files: create files under TEMP and LOCALAPPDATA temp
    t1 = tmp_path / 'Temp'
    t1.mkdir(exist_ok=True)
    (t1 / 'a.log').write_text('x')
    monkeypatch.setenv('TEMP', str(t1))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert cleaner.cleanup_temp_files() is True

    # async cleanup tempfile
    rv = asyncio.run(cleaner.cleanup_temp_files_async(stream_callback=lambda s: None))
    assert isinstance(rv, bool)

    # stop_docker_wsl_async: simulate elevated command returning nonzero
    async def fake_elev(cmd, shell=True, stream_callback=None):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_elevated_command_async', fake_elev)
    res = asyncio.run(cleaner.stop_docker_wsl_async(stream_callback=lambda s: None))
    assert res is True

    # configure_wsl_sparse_async error flow
    async def rc_none(cmd, shell=True, stream_callback=None):
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout='')
    monkeypatch.setattr(cleaner, 'run_command_async', rc_none)
    res = asyncio.run(cleaner.configure_wsl_sparse_async(stream_callback=lambda s: None))
    assert res is False

    # compact_vhdx_files_async success
    vfile = tmp_path / 'Docker' / 'wsl' / 'distro'
    vfile.mkdir(parents=True, exist_ok=True)
    p2 = vfile / 'ext4.vhdx'
    p2.write_bytes(b'hello')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    async def shrink(cmd, stream_callback=None):
        p2.write_bytes(b'a')
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_elevated_command_async', shrink)
    res = asyncio.run(cleaner.compact_vhdx_files_async(stream_callback=lambda s: None))
    assert isinstance(res, bool)


def test_log_swallow_logger_exceptions():
    cleaner = WSLDockerCleaner()
    class BrokenLogger:
        def error(self, _):
            raise RuntimeError('boom')
        def warning(self, _):
            raise RuntimeError('boom')
        def info(self, _):
            raise RuntimeError('boom')
    cleaner.logger = BrokenLogger()
    # This should not raise despite logger throwing
    cleaner.log('test')


def test_run_command_async_shell_false_and_stderr(monkeypatch):
    cleaner = WSLDockerCleaner()
    outputs = []
    def cb(line):
        outputs.append(line)
    # Run a shell-free command as a list
    res = asyncio.run(cleaner.run_command_async(f'{sys.executable} -c "import sys; print(\"out\"); sys.stderr.write(\"err\")"', shell=True, stream_callback=cb))
    assert isinstance(res, subprocess.CompletedProcess)
    # Call with shell=False and as list
    res2 = asyncio.run(cleaner.run_command_async([sys.executable, '-c', 'print("ok")'], shell=False, stream_callback=cb))
    assert isinstance(res2, subprocess.CompletedProcess)
    assert any('err' in s for s in outputs)


def test_run_elevated_command_async_stream_callback(monkeypatch):
    cleaner = WSLDockerCleaner()
    outputs = []
    async def fake_elev(cmd, shell=True, stream_callback=None):
        if stream_callback:
            stream_callback('Solicitando privilégios admin (UAC)...\n')
            stream_callback('done\n')
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_command_async', fake_elev)
    res = asyncio.run(cleaner.run_elevated_command_async('cmd', stream_callback=lambda s: outputs.append(s)))
    assert res.returncode == 0
    assert any('Solicitando privilégios admin' in o or 'done' in o for o in outputs)


def test_compact_vhdx_files_async_error(monkeypatch, tmp_path):
    cleaner = WSLDockerCleaner()
    # create vhdx
    vdir = tmp_path / 'Docker' / 'wsl' / 'data'
    vdir.mkdir(parents=True)
    p = vdir / 'ext4.vhdx'
    p.write_bytes(b'x' * 1024)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    async def fake_elev(cmd, shell=True, stream_callback=None):
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout='', stderr='err')
    monkeypatch.setattr(cleaner, 'run_elevated_command_async', fake_elev)
    res = asyncio.run(cleaner.compact_vhdx_files_async(stream_callback=lambda s: None))
    assert res is False


def test_run_elevated_async_no_stream(monkeypatch):
    cleaner = WSLDockerCleaner()
    async def fake(cmd, shell=True, stream_callback=None):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
    monkeypatch.setattr(cleaner, 'run_command_async', fake)
    res = asyncio.run(cleaner.run_elevated_command_async('cmd'))
    assert isinstance(res, subprocess.CompletedProcess)


def test_docker_cleanup_start_error(monkeypatch):
    cleaner = WSLDockerCleaner()
    # Simulate docker not running and path exists
    monkeypatch.setattr(cleaner, 'is_docker_running', lambda: False)
    # Force docker path to exist
    monkeypatch.setattr(os.path, 'exists', lambda p: True)
    # Simulate subprocess.Popen raising
    class FakePopen:
        def __init__(self, *a, **k):
            raise Exception('fail to spawn')
    monkeypatch.setattr(subprocess, 'Popen', FakePopen)
    res = cleaner.docker_cleanup()
    assert res is False
    assert any('Erro ao iniciar Docker' in m for m in cleaner.log_messages)


