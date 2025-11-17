import io
import os
import tempfile
import subprocess
from rich.console import Console
import pytest

import cli.quick_cleanup as qc
import runpy


def test_run_cmd_success(monkeypatch):
    buf = io.StringIO()
    console = Console(file=buf)
    cp = subprocess.CompletedProcess(args="cmd", returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: cp)
    ok = qc.run_cmd(console, "echo hi", "Desc")
    assert ok is True
    out = buf.getvalue()
    assert "Executando:" in out
    assert "Saída:" in out


def test_run_cmd_timeout(monkeypatch):
    buf = io.StringIO()
    console = Console(file=buf)
    def raiser(*a, **k):
        raise subprocess.TimeoutExpired(cmd="cmd", timeout=1)
    monkeypatch.setattr(subprocess, "run", raiser)
    ok = qc.run_cmd(console, "sleep 10", "Desc")
    assert ok is False
    assert "TIMEOUT" in buf.getvalue()


def test_run_cmd_error(monkeypatch):
    buf = io.StringIO()
    console = Console(file=buf)
    cp = subprocess.CompletedProcess(args="cmd", returncode=1, stdout="", stderr="oops")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: cp)
    ok = qc.run_cmd(console, "bad command", "Desc")
    assert ok is False
    assert "Erro:" in buf.getvalue()


def test_quick_cleanup_no_vhdx(monkeypatch):
    buf = io.StringIO()
    console = Console(file=buf)
    # Make run_cmd always succeed
    monkeypatch.setattr(qc, "run_cmd", lambda c, cmd, desc="": True)
    # Ensure vhdx non existent
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    ok = qc.quick_cleanup(console)
    assert ok is True
    assert "== LIMPEZA CONCLUÍDA ==" in buf.getvalue()


def test_quick_cleanup_with_vhdx(monkeypatch, tmp_path):
    buf = io.StringIO()
    console = Console(file=buf)
    # Create fake vhdx
    vhdx_dir = tmp_path / "Docker" / "wsl" / "data"
    vhdx_dir.mkdir(parents=True)
    test_vhdx = vhdx_dir / "ext4.vhdx"
    test_vhdx.write_bytes(b"x" * 2048)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    # Replace run_cmd to simulate compaction and shrink file
    def fake_run_cmd(c, cmd, desc=""):
        # shrink file (simulate Optimize-VHD)
        test_vhdx.write_bytes(b"x")
        return True
    monkeypatch.setattr(qc, "run_cmd", fake_run_cmd)
    ok = qc.quick_cleanup(console)
    assert ok is True
    out = buf.getvalue()
    assert "Arquivo VHDX não encontrado" not in out
    assert "Espaço economizado" in out or "Tamanho após" in out


def test_quick_cleanup_main_exec(monkeypatch, tmp_path, capsys):
    # Ensure runpy runs main without hanging (input patched)
    vhdx_dir = tmp_path / "Docker" / "wsl" / "data"
    vhdx_dir.mkdir(parents=True)
    vhdx_file = vhdx_dir / "ext4.vhdx"
    vhdx_file.write_bytes(b"x" * 1024)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    # Monkeypatch subprocess.run globally so run_cmd returns success
    cp = subprocess.CompletedProcess(args="cmd", returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: cp)
    # Avoid waiting input
    monkeypatch.setattr('builtins.input', lambda *a, **k: '')
    # Run module as __main__ - should not raise
    runpy.run_module('cli.quick_cleanup', run_name='__main__')
