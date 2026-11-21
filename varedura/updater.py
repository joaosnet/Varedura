"""Authenticated GitHub self-updater, cron scheduler and CLI for Varedura.

All top-level imports are 100% Python stdlib with zero I/O at import time.
Tokens are never written to git remotes, temp scripts or log/status outputs.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

DEFAULT_COOLDOWN_SECONDS = 6 * 3600
_INITIAL_HOME = Path.home()
TOKEN_FILE = _INITIAL_HOME / ".varedura_gh_token"
CRON_MARKER = "# VAREDURA-AUTO-UPDATE"

_URL_CREDENTIALS_RE = re.compile(r"(https?://)[^\s/@:]+:[^\s/@]+@")


@dataclass
class UpdateResult:
    """Outcome of a check or update run."""

    status: str  # "up_to_date" | "update_available" | "updated" | "dirty" | "cooldown" | "error"
    branch: str = ""
    current_commit: str = ""
    commits_behind: int = 0
    commits_pulled: int = 0
    summary: str = ""
    message: str = ""
    token_source: str = "none"
    reinstalled: bool = False


def _token_file_path() -> Path:
    if TOKEN_FILE != _INITIAL_HOME / ".varedura_gh_token":
        return TOKEN_FILE
    return Path.home() / ".varedura_gh_token"


def _alt_token_file_path() -> Path:
    return Path.home() / ".config" / "varedura" / "gh_token"


def _prefs_file_path() -> Path:
    return Path.home() / ".varedura_prefs.json"


def _default_repo_dir(repo_dir: Path | None = None) -> Path:
    if repo_dir is not None:
        return Path(repo_dir)
    return Path(__file__).resolve().parents[1]


def _redact_token(text: str, token: str | None = None) -> str:
    if not text:
        return ""
    cleaned = _URL_CREDENTIALS_RE.sub(r"\1***REDACTED***@", text)
    if token:
        cleaned = cleaned.replace(token, "***REDACTED***")
    return cleaned


def resolve_github_token() -> tuple[str | None, str]:
    """Resolve GitHub token from env vars or token files without exposing its value."""
    for env_name in ("GHG_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        val = os.environ.get(env_name, "").strip()
        if val:
            return val, f"env:{env_name}"

    candidates: list[tuple[Path, str]] = [
        (_token_file_path(), "file:~/.varedura_gh_token"),
        (_alt_token_file_path(), "file:~/.config/varedura/gh_token"),
    ]
    for path, label in candidates:
        try:
            if path.is_file():
                val = path.read_text(encoding="utf-8").strip()
                if val:
                    return val, label
        except OSError:
            continue

    return None, "none"


def save_token_file(token: str, path: Path | None = None) -> Path:
    """Persist a GitHub token securely (chmod 0o600 on POSIX)."""
    cleaned = (token or "").strip()
    if not cleaned or "\n" in cleaned or "\r" in cleaned:
        raise ValueError("Token must be a non-empty single-line string")
    target = Path(path) if path is not None else _token_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(cleaned + "\n", encoding="utf-8")
    if os.name != "nt":
        os.chmod(target, 0o600)
    return target


def _run_git_authenticated(
    args: list[str],
    repo_dir: Path,
    token: str | None,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    """Run git using an ephemeral env-backed GIT_ASKPASS script and redact output."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    script_path: Path | None = None
    try:
        if token:
            if os.name == "nt":
                suffix = ".bat"
                script_body = (
                    "@echo off\r\n"
                    'echo %~1 | findstr /B /I "Username" >nul\r\n'
                    "if %errorlevel%==0 (echo x-access-token) else (echo %_VAREDURA_ASKPASS_SECRET%)\r\n"
                )
            else:
                suffix = ".sh"
                script_body = (
                    "#!/bin/sh\n"
                    'case "$1" in\n'
                    '  Username*) printf "%s\\n" "x-access-token" ;;\n'
                    '  *) printf "%s\\n" "$_VAREDURA_ASKPASS_SECRET" ;;\n'
                    "esac\n"
                )
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=suffix,
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(script_body)
                script_path = Path(tmp.name)
            os.chmod(script_path, 0o700)
            env["GIT_ASKPASS"] = str(script_path)
            env["_VAREDURA_ASKPASS_SECRET"] = token

        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_dir),
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        return subprocess.CompletedProcess(
            args=proc.args,
            returncode=proc.returncode,
            stdout=_redact_token(proc.stdout or "", token),
            stderr=_redact_token(proc.stderr or "", token),
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return subprocess.CompletedProcess(
            args=["git", *args],
            returncode=124,
            stdout=_redact_token(out, token),
            stderr=_redact_token(err or f"git timed out after {timeout}s", token),
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            args=["git", *args],
            returncode=1,
            stdout="",
            stderr=_redact_token(str(exc), token),
        )
    finally:
        if script_path is not None:
            try:
                script_path.unlink(missing_ok=True)
            except OSError:
                pass


def _read_last_check() -> float | None:
    prefs_path = _prefs_file_path()
    try:
        if not prefs_path.is_file():
            return None
        data = json.loads(prefs_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("git_last_check") is not None:
            return float(data["git_last_check"])
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def _write_last_check(timestamp: float | None = None) -> None:
    prefs_path = _prefs_file_path()
    data: dict = {}
    try:
        if prefs_path.is_file():
            loaded = json.loads(prefs_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        data = {}

    data["git_last_check"] = time.time() if timestamp is None else float(timestamp)
    try:
        prefs_path.parent.mkdir(parents=True, exist_ok=True)
        prefs_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def get_repo_status(repo_dir: Path | None = None) -> dict:
    """Return local git branch, commit, dirty state, token source, cron and last check."""
    repo = _default_repo_dir(repo_dir)
    _, token_source = resolve_github_token()

    branch_res = _run_git_authenticated(
        ["rev-parse", "--abbrev-ref", "HEAD"], repo, None, timeout=5.0
    )
    commit_res = _run_git_authenticated(
        ["rev-parse", "--short", "HEAD"], repo, None, timeout=5.0
    )
    dirty_res = _run_git_authenticated(["status", "--porcelain"], repo, None, timeout=5.0)

    return {
        "branch": branch_res.stdout.strip() if branch_res.returncode == 0 else "",
        "commit": commit_res.stdout.strip() if commit_res.returncode == 0 else "",
        "dirty": bool(dirty_res.stdout.strip()) if dirty_res.returncode == 0 else False,
        "token_source": token_source,
        "cron_enabled": is_cron_update_enabled(),
        "last_check": _read_last_check(),
    }


def update_repository(
    repo_dir: Path | None = None,
    *,
    check_only: bool = False,
    force: bool = False,
    notify: bool = True,
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
) -> UpdateResult:
    """Check for or apply fast-forward updates from origin using authenticated git."""
    repo = _default_repo_dir(repo_dir)
    token, token_source = resolve_github_token()

    branch_res = _run_git_authenticated(
        ["rev-parse", "--abbrev-ref", "HEAD"], repo, None, timeout=5.0
    )
    if branch_res.returncode != 0:
        return UpdateResult(
            status="error",
            message=branch_res.stderr.strip() or "Not a git repository",
            token_source=token_source,
        )
    branch = branch_res.stdout.strip()

    short_res = _run_git_authenticated(
        ["rev-parse", "--short", "HEAD"], repo, None, timeout=5.0
    )
    current_commit = short_res.stdout.strip() if short_res.returncode == 0 else ""

    if not force and cooldown_seconds > 0:
        last_check = _read_last_check()
        if last_check is not None and (time.time() - last_check) < cooldown_seconds:
            return UpdateResult(
                status="cooldown",
                branch=branch,
                current_commit=current_commit,
                message="Cooldown active",
                token_source=token_source,
            )

    dirty_res = _run_git_authenticated(["status", "--porcelain"], repo, None, timeout=5.0)
    if dirty_res.returncode != 0:
        return UpdateResult(
            status="error",
            branch=branch,
            current_commit=current_commit,
            message=dirty_res.stderr.strip() or "git status failed",
            token_source=token_source,
        )
    if dirty_res.stdout.strip():
        return UpdateResult(
            status="dirty",
            branch=branch,
            current_commit=current_commit,
            message="Working tree has uncommitted changes",
            token_source=token_source,
        )

    if not branch or branch == "HEAD":
        return UpdateResult(
            status="error",
            branch=branch,
            current_commit=current_commit,
            message="Detached HEAD is not supported for auto-update",
            token_source=token_source,
        )

    fetch_res = _run_git_authenticated(
        ["fetch", "--quiet", "origin", branch], repo, token, timeout=30.0
    )
    if fetch_res.returncode != 0:
        return UpdateResult(
            status="error",
            branch=branch,
            current_commit=current_commit,
            message=fetch_res.stderr.strip() or "git fetch failed",
            token_source=token_source,
        )
    _write_last_check()

    count_res = _run_git_authenticated(
        ["rev-list", "--count", f"HEAD..origin/{branch}"], repo, None, timeout=10.0
    )
    if count_res.returncode != 0:
        return UpdateResult(
            status="error",
            branch=branch,
            current_commit=current_commit,
            message=count_res.stderr.strip() or "git rev-list failed",
            token_source=token_source,
        )
    try:
        behind = int(count_res.stdout.strip() or "0")
    except ValueError:
        behind = 0

    if behind == 0:
        return UpdateResult(
            status="up_to_date",
            branch=branch,
            current_commit=current_commit,
            commits_behind=0,
            message="Already up to date",
            token_source=token_source,
        )

    if check_only:
        log_res = _run_git_authenticated(
            ["log", "--oneline", f"HEAD..origin/{branch}"], repo, None, timeout=10.0
        )
        return UpdateResult(
            status="update_available",
            branch=branch,
            current_commit=current_commit,
            commits_behind=behind,
            summary=log_res.stdout.strip() if log_res.returncode == 0 else "",
            message=f"{behind} commit(s) available",
            token_source=token_source,
        )

    old_rev_res = _run_git_authenticated(["rev-parse", "HEAD"], repo, None, timeout=5.0)
    old_rev = old_rev_res.stdout.strip() if old_rev_res.returncode == 0 else "HEAD"

    pull_res = _run_git_authenticated(
        ["pull", "--ff-only", "origin", branch], repo, token, timeout=30.0
    )
    if pull_res.returncode != 0:
        return UpdateResult(
            status="error",
            branch=branch,
            current_commit=current_commit,
            commits_behind=behind,
            message=pull_res.stderr.strip() or "git pull failed",
            token_source=token_source,
        )

    new_rev_res = _run_git_authenticated(["rev-parse", "HEAD"], repo, None, timeout=5.0)
    new_rev = new_rev_res.stdout.strip() if new_rev_res.returncode == 0 else "HEAD"
    new_short_res = _run_git_authenticated(
        ["rev-parse", "--short", "HEAD"], repo, None, timeout=5.0
    )
    new_commit = new_short_res.stdout.strip() if new_short_res.returncode == 0 else current_commit

    summary_res = _run_git_authenticated(
        ["log", "--oneline", f"{old_rev}..{new_rev}"], repo, None, timeout=10.0
    )
    summary = summary_res.stdout.strip() if summary_res.returncode == 0 else ""

    diff_res = _run_git_authenticated(
        ["diff", "--name-only", f"{old_rev}..{new_rev}"], repo, None, timeout=10.0
    )
    changed_files = (
        {line.strip() for line in diff_res.stdout.splitlines() if line.strip()}
        if diff_res.returncode == 0
        else set()
    )

    from varedura.termux_env import is_termux, send_termux_notification

    reinstalled = False
    if "pyproject.toml" in changed_files and is_termux():
        try:
            pip_res = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-build-isolation",
                    "--no-deps",
                    "-e",
                    str(repo),
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=120,
            )
            reinstalled = pip_res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            reinstalled = False

    if notify and is_termux():
        send_termux_notification(
            "Varedura",
            f"Updated {behind} commit(s) on {branch} ({new_commit})",
            notif_id="varedura-update",
        )

    return UpdateResult(
        status="updated",
        branch=branch,
        current_commit=new_commit,
        commits_behind=behind,
        commits_pulled=behind,
        summary=summary,
        message=f"Updated {behind} commit(s)",
        token_source=token_source,
        reinstalled=reinstalled,
    )


def _read_crontab() -> tuple[bool, list[str], str]:
    exe = shutil.which("crontab")
    if not exe:
        return False, [], "crontab not found"
    try:
        proc = subprocess.run(
            [exe, "-l"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, [], str(exc)

    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        if "no crontab" in err.lower():
            return True, [], ""
        return False, [], err or "Failed to read crontab"

    return True, proc.stdout.splitlines(), ""


def is_cron_update_enabled() -> bool:
    """Return True if the Varedura auto-update cron entry is installed."""
    ok, lines, _ = _read_crontab()
    if not ok:
        return False
    return any(CRON_MARKER in line and not line.lstrip().startswith("#") for line in lines)


def set_cron_update_enabled(
    enabled: bool,
    schedule: str = "0 */6 * * *",
) -> tuple[bool, str]:
    """Install or remove the Varedura auto-update crontab entry safely."""
    if "\n" in schedule or "\r" in schedule:
        return False, "Invalid cron schedule"
    exe = shutil.which("crontab")
    if not exe:
        return False, "crontab not found"

    ok, lines, err = _read_crontab()
    if not ok:
        return False, err

    kept = [line for line in lines if CRON_MARKER not in line]
    if enabled:
        updater_bin = shutil.which("varedura-update") or f"{sys.executable} -m varedura.updater"
        kept.append(f"{schedule} {updater_bin} >/dev/null 2>&1 {CRON_MARKER}")

    payload = "\n".join(kept).rstrip("\n")
    if payload:
        payload += "\n"

    try:
        proc = subprocess.run(
            [exe, "-"],
            input=payload,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=5,
        )
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout or "Failed to update crontab").strip()
        return True, "Auto-update cron enabled" if enabled else "Auto-update cron disabled"
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for varedura-update."""
    parser = argparse.ArgumentParser(
        prog="varedura-update",
        description="Check and apply authenticated git updates for Varedura.",
    )
    parser.add_argument("--check", action="store_true", help="Check for updates only")
    parser.add_argument("--force", action="store_true", help="Ignore update cooldown")
    parser.add_argument(
        "--no-notify", action="store_true", help="Disable Termux notification"
    )
    parser.add_argument(
        "--set-token",
        action="store_true",
        help="Prompt for and store GitHub token securely",
    )
    parser.add_argument(
        "--cron-on", action="store_true", help="Enable 6h auto-update cron entry"
    )
    parser.add_argument(
        "--cron-off", action="store_true", help="Disable auto-update cron entry"
    )
    parser.add_argument("--status", action="store_true", help="Show repository status")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--repo-dir", type=Path, default=None, help="Repository path")
    args = parser.parse_args(argv)

    if args.set_token:
        try:
            raw = (
                getpass.getpass("GitHub token: ")
                if sys.stdin.isatty()
                else sys.stdin.readline()
            )
            saved_path = save_token_file(raw)
        except Exception as exc:
            if args.json:
                print(json.dumps({"ok": False, "error": str(exc)}))
            else:
                print(f"Error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"ok": True, "path": str(saved_path)}))
        else:
            print(f"Token saved to {saved_path}")
        return 0

    if args.cron_on or args.cron_off:
        ok, msg = set_cron_update_enabled(bool(args.cron_on))
        if args.json:
            print(json.dumps({"ok": ok, "message": msg}))
        else:
            print(msg)
        return 0 if ok else 1

    if args.status:
        status_info = get_repo_status(args.repo_dir)
        if args.json:
            print(json.dumps(status_info))
        else:
            print(
                f"branch={status_info['branch'] or '-'} "
                f"commit={status_info['commit'] or '-'} "
                f"dirty={status_info['dirty']} "
                f"token={status_info['token_source']} "
                f"cron={status_info['cron_enabled']}"
            )
        return 0

    result = update_repository(
        args.repo_dir,
        check_only=args.check,
        force=args.force,
        notify=not args.no_notify,
    )
    if args.json:
        print(json.dumps(asdict(result)))
    else:
        print(f"[{result.status}] {result.message}")
        if result.summary:
            print(result.summary)
    return 1 if result.status in {"error", "dirty"} else 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CRON_MARKER",
    "DEFAULT_COOLDOWN_SECONDS",
    "TOKEN_FILE",
    "UpdateResult",
    "get_repo_status",
    "is_cron_update_enabled",
    "main",
    "resolve_github_token",
    "save_token_file",
    "set_cron_update_enabled",
    "update_repository",
]
