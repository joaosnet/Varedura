"""Tests for varedura.updater (authenticated git self-updater & cron)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from varedura import updater


def test_updater_import_is_100pct_stdlib_and_zero_io():
    script = (
        "import json, socket, subprocess, sys; "
        "bad = lambda *a, **k: (_ for _ in ()).throw(AssertionError('IO on import')); "
        "socket.getaddrinfo = bad; subprocess.run = bad; subprocess.Popen = bad; "
        "import varedura.updater; "
        "heavy = ['psutil', 'requests', 'textual', 'rich', 'PIL', 'selenium']; "
        "print(json.dumps({m: m in sys.modules for m in heavy}))"
    )
    res = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    loaded = json.loads(res.stdout.strip())
    assert not any(loaded.values())


def test_resolve_github_token_precedence_and_no_secret_in_label(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(updater, "TOKEN_FILE", tmp_path / ".varedura_gh_token")
    for env in ("GHG_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(env, raising=False)

    assert updater.resolve_github_token() == (None, "none")

    alt = tmp_path / ".config" / "varedura" / "gh_token"
    alt.parent.mkdir(parents=True)
    alt.write_text("secret_alt_123\n", encoding="utf-8")
    tok, src = updater.resolve_github_token()
    assert tok == "secret_alt_123"
    assert "secret_alt_123" not in src

    updater.save_token_file("  secret_primary_456  ")
    tok, src = updater.resolve_github_token()
    assert tok == "secret_primary_456"
    assert src == "file:~/.varedura_gh_token"
    assert "secret_primary_456" not in src

    monkeypatch.setenv("GITHUB_TOKEN", "env_github_1")
    assert updater.resolve_github_token() == ("env_github_1", "env:GITHUB_TOKEN")

    monkeypatch.setenv("GH_TOKEN", "env_gh_2")
    assert updater.resolve_github_token() == ("env_gh_2", "env:GH_TOKEN")

    monkeypatch.setenv("GHG_TOKEN", "env_ghg_3")
    assert updater.resolve_github_token() == ("env_ghg_3", "env:GHG_TOKEN")


def test_save_token_file_rejects_empty_or_multiline(tmp_path):
    with pytest.raises(ValueError):
        updater.save_token_file("   ", tmp_path / "tok")
    with pytest.raises(ValueError):
        updater.save_token_file("abc\ndef", tmp_path / "tok")

    saved = updater.save_token_file("ghp_valid_token", tmp_path / "tok")
    assert saved.read_text(encoding="utf-8").strip() == "ghp_valid_token"


def test_run_git_authenticated_uses_ephemeral_askpass_and_redacts(monkeypatch, tmp_path):
    captured = {}

    def fake_run(cmd, **kwargs):
        env = kwargs["env"]
        askpass = Path(env["GIT_ASKPASS"])
        captured["exists_during_call"] = askpass.is_file()
        captured["askpass_path"] = askpass
        captured["script_body"] = askpass.read_text(encoding="utf-8")
        captured["secret_env"] = env.get("_VAREDURA_ASKPASS_SECRET")
        captured["terminal_prompt"] = env.get("GIT_TERMINAL_PROMPT")
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="using super_secret_tok_999",
            stderr="fatal: https://user:super_secret_tok_999@github.com/repo.git",
        )

    monkeypatch.setattr(updater.subprocess, "run", fake_run)
    res = updater._run_git_authenticated(
        ["fetch", "origin", "main"], tmp_path, "super_secret_tok_999"
    )

    assert captured["exists_during_call"] is True
    assert not captured["askpass_path"].exists()
    assert "super_secret_tok_999" not in captured["script_body"]
    assert "_VAREDURA_ASKPASS_SECRET" in captured["script_body"]
    assert captured["secret_env"] == "super_secret_tok_999"
    assert captured["terminal_prompt"] == "0"
    assert "super_secret_tok_999" not in res.stdout
    assert "super_secret_tok_999" not in res.stderr
    assert "***REDACTED***" in res.stderr


def test_update_repository_states_and_cooldown(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(updater, "TOKEN_FILE", tmp_path / ".varedura_gh_token")
    monkeypatch.setenv("GHG_TOKEN", "tok_test_123")
    monkeypatch.setenv("VAREDURA_TERMUX_MODE", "1")

    # 1. Dirty repo
    def dirty_git(args, repo_dir, token, timeout=30.0):
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(args, 0, "main\n", "")
        if args[:2] == ["rev-parse", "--short"]:
            return subprocess.CompletedProcess(args, 0, "abc1234\n", "")
        if args[:2] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(args, 0, " M main.py\n", "")
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(updater, "_run_git_authenticated", dirty_git)
    res_dirty = updater.update_repository(tmp_path)
    assert res_dirty.status == "dirty"
    assert res_dirty.branch == "main"

    # 2. Up to date -> writes cooldown
    def clean_uptodate_git(args, repo_dir, token, timeout=30.0):
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(args, 0, "main\n", "")
        if args[:2] == ["rev-parse", "--short"]:
            return subprocess.CompletedProcess(args, 0, "abc1234\n", "")
        if args[:2] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "fetch":
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "rev-list":
            return subprocess.CompletedProcess(args, 0, "0\n", "")
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(updater, "_run_git_authenticated", clean_uptodate_git)
    res_ok = updater.update_repository(tmp_path)
    assert res_ok.status == "up_to_date"
    assert res_ok.token_source == "env:GHG_TOKEN"

    # 3. Subsequent call hits 6h cooldown
    res_cd = updater.update_repository(tmp_path)
    assert res_cd.status == "cooldown"

    # 4. check_only with force=True sees available updates
    def update_avail_git(args, repo_dir, token, timeout=30.0):
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(args, 0, "main\n", "")
        if args[:2] == ["rev-parse", "--short"]:
            return subprocess.CompletedProcess(args, 0, "abc1234\n", "")
        if args[:2] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "fetch":
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "rev-list":
            return subprocess.CompletedProcess(args, 0, "2\n", "")
        if args[0] == "log":
            return subprocess.CompletedProcess(args, 0, "def5678 feat: x\n", "")
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(updater, "_run_git_authenticated", update_avail_git)
    res_avail = updater.update_repository(tmp_path, check_only=True, force=True)
    assert res_avail.status == "update_available"
    assert res_avail.commits_behind == 2
    assert "feat: x" in res_avail.summary

    # 5. Full pull with pyproject.toml change triggers Termux reinstall & notification
    pip_calls = []
    notifs = []

    def full_pull_git(args, repo_dir, token, timeout=30.0):
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(args, 0, "main\n", "")
        if args[:2] == ["rev-parse", "--short"]:
            return subprocess.CompletedProcess(args, 0, "def5678\n", "")
        if args == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, "1111111\n", "")
        if args[:2] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "fetch":
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "rev-list":
            return subprocess.CompletedProcess(args, 0, "2\n", "")
        if args[0] == "pull":
            return subprocess.CompletedProcess(args, 0, "Updating", "")
        if args[0] == "log":
            return subprocess.CompletedProcess(args, 0, "def5678 feat: y\n", "")
        if args[0] == "diff":
            return subprocess.CompletedProcess(args, 0, "pyproject.toml\nmain.py\n", "")
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(updater, "_run_git_authenticated", full_pull_git)
    monkeypatch.setattr(
        updater.subprocess,
        "run",
        lambda cmd, **kw: (pip_calls.append(cmd), subprocess.CompletedProcess(cmd, 0, "", ""))[1],
    )
    from varedura import termux_env

    monkeypatch.setattr(
        termux_env,
        "send_termux_notification",
        lambda title, body, **kw: (notifs.append((title, body)), True)[1],
    )

    res_upd = updater.update_repository(tmp_path, force=True, notify=True)
    assert res_upd.status == "updated"
    assert res_upd.commits_pulled == 2
    assert res_upd.reinstalled is True
    assert pip_calls and "--no-build-isolation" in pip_calls[0]
    assert len(notifs) == 1


def test_cron_toggle_preserves_other_entries(monkeypatch):
    stored = {"text": "0 3 * * * /usr/bin/backup\n"}
    monkeypatch.setattr(updater.shutil, "which", lambda name: f"/bin/{name}")

    def fake_run(cmd, **kwargs):
        if cmd[-1] == "-l":
            return subprocess.CompletedProcess(cmd, 0, stored["text"], "")
        if cmd[-1] == "-":
            stored["text"] = kwargs["input"]
            return subprocess.CompletedProcess(cmd, 0, "", "")
        raise AssertionError(cmd)

    monkeypatch.setattr(updater.subprocess, "run", fake_run)

    assert updater.is_cron_update_enabled() is False
    ok, _ = updater.set_cron_update_enabled(True)
    assert ok is True
    assert updater.CRON_MARKER in stored["text"]
    assert "/usr/bin/backup" in stored["text"]
    assert updater.is_cron_update_enabled() is True

    ok, _ = updater.set_cron_update_enabled(False)
    assert ok is True
    assert updater.CRON_MARKER not in stored["text"]
    assert "/usr/bin/backup" in stored["text"]
    assert updater.is_cron_update_enabled() is False


def test_cli_status_and_check_json(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        updater,
        "get_repo_status",
        lambda repo_dir=None: {
            "branch": "main",
            "commit": "abc1234",
            "dirty": False,
            "token_source": "env:GHG_TOKEN",
            "cron_enabled": True,
            "last_check": time.time(),
        },
    )
    assert updater.main(["--status", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["branch"] == "main"
    assert out["cron_enabled"] is True

    monkeypatch.setattr(
        updater,
        "update_repository",
        lambda *a, **k: updater.UpdateResult(status="up_to_date", branch="main"),
    )
    assert updater.main(["--check", "--json", "--repo-dir", str(tmp_path)]) == 0
    out2 = json.loads(capsys.readouterr().out)
    assert out2["status"] == "up_to_date"
