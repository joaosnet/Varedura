"""
Varedura MCP Server

Exposes Varedura tools via the Model Context Protocol so that AI agents
(e.g. GitHub Copilot CLI) can interact with Docker cleanup, port scanning,
and system monitoring using the same underlying logic as the TUI.

Usage:
    uv run python -m mcp_server          # stdio transport (default)
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from docker_cleaner.core import WSLDockerCleaner

mcp = FastMCP(
    "Varedura",
    version="1.0.0",
    description="Docker cleanup, port scanning and system monitoring tools",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cmd(command: str, timeout: int = 120) -> dict[str, Any]:
    """Run a shell command and return structured result."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


def _is_docker_running() -> bool:
    """Check whether Docker daemon is reachable."""
    r = _run_cmd("docker ps", timeout=15)
    return r["returncode"] == 0


def _confirmation_required(tool: str, actions: list[str]) -> str:
    """Response returned when a destructive tool is called without confirmation.

    The calling agent MUST surface these actions to the human user and obtain
    explicit consent before re-invoking the tool with ``confirmed=True``.
    """
    return json.dumps(
        {
            "executed": False,
            "requires_confirmation": True,
            "tool": tool,
            "destructive": True,
            "actions": actions,
            "message": (
                "This is a destructive operation and was NOT executed. Present the "
                "listed actions to the user, obtain explicit confirmation, then call "
                "this tool again with confirmed=true. Use dry_run=true to preview "
                "the impact without executing."
            ),
        },
        indent=2,
        ensure_ascii=False,
    )


def _dry_run_preview(tool: str, actions: list[str], extra: dict[str, Any] | None = None) -> str:
    """Response returned for a dry run: lists impact without executing anything."""
    payload: dict[str, Any] = {
        "executed": False,
        "dry_run": True,
        "tool": tool,
        "destructive": True,
        "actions": actions,
        "timestamp": datetime.now().isoformat(),
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def docker_status() -> str:
    """Get Docker system disk usage and container/image/volume counts.

    Returns a summary of `docker system df` plus running container list.
    Useful for understanding current Docker resource usage before cleanup.
    """
    if not _is_docker_running():
        return json.dumps({"error": "Docker is not running"}, indent=2)

    df = _run_cmd("docker system df")
    ps = _run_cmd("docker ps --format '{{.ID}}  {{.Image}}  {{.Status}}  {{.Names}}'")

    return json.dumps(
        {
            "disk_usage": df["stdout"],
            "running_containers": ps["stdout"] or "No running containers",
        },
        indent=2,
        ensure_ascii=False,
    )


_QUICK_CLEANUP_ACTIONS = [
    "Remove all stopped containers",
    "Remove unused (dangling) images",
    "Remove unused volumes",
    "Remove unused networks",
    "Prune build cache",
]


@mcp.tool()
def docker_quick_cleanup(confirmed: bool = False, dry_run: bool = False) -> str:
    """Run a quick Docker cleanup: prune containers, images, volumes, networks, and build cache.

    ⚠️  DESTRUCTIVE: removes all stopped containers, unused images, unused
    volumes, unused networks, and build cache. Running containers are preserved.

    Guardrails (the agent MUST respect these):
    - Without ``confirmed=True`` the tool does NOT execute; it returns the list
      of actions so you can ask the user for explicit confirmation first.
    - ``dry_run=True`` previews the impact (and current disk usage) without
      removing anything.

    Args:
        confirmed: Set True only after the user has explicitly approved the cleanup.
        dry_run: Preview the actions and current Docker disk usage without executing.

    Returns the space reclaimed by each step (when executed).
    """
    if dry_run:
        usage = _run_cmd("docker system df")["stdout"] if _is_docker_running() else None
        return _dry_run_preview(
            "docker_quick_cleanup",
            _QUICK_CLEANUP_ACTIONS,
            {"current_disk_usage": usage or "Docker is not running"},
        )

    if not confirmed:
        return _confirmation_required("docker_quick_cleanup", _QUICK_CLEANUP_ACTIONS)

    if not _is_docker_running():
        return json.dumps(
            {"executed": False, "success": False, "error": "Docker is not running"},
            indent=2,
            ensure_ascii=False,
        )

    cleaner = WSLDockerCleaner()
    success = cleaner.docker_cleanup(
        steps=("containers", "images", "volumes", "networks", "system", "builder")
    )
    return json.dumps(
        {
            "executed": True,
            "success": success,
            "running_containers_preserved": True,
            "steps": [result.to_dict() for result in cleaner.last_cleanup_results],
            "timestamp": datetime.now().isoformat(),
        },
        indent=2,
        ensure_ascii=False,
    )


_FULL_CLEANUP_ACTIONS = [
    *_QUICK_CLEANUP_ACTIONS,
    "Stop Docker Desktop and shut down WSL",
    "Compact VHDX disk files (Windows, requires administrator privileges)",
]


@mcp.tool()
def docker_full_cleanup(confirmed: bool = False, dry_run: bool = False) -> str:
    """Run full Docker cleanup including WSL shutdown and VHDX compaction (Windows).

    ⚠️  DESTRUCTIVE & REQUIRES ADMIN: In addition to quick cleanup, this also:
    1. Stops Docker Desktop and WSL
    2. Compacts VHDX disk files to reclaim physical disk space

    On Linux/macOS, performs quick cleanup + Docker service restart.
    VHDX compaction requires administrator privileges on Windows.

    Guardrails (the agent MUST respect these):
    - Without ``confirmed=True`` the tool does NOT execute; it returns the list
      of actions so you can ask the user for explicit confirmation first.
    - ``dry_run=True`` previews the impact without executing anything.

    Args:
        confirmed: Set True only after the user has explicitly approved the full cleanup.
        dry_run: Preview the actions without executing.
    """
    if dry_run:
        return _dry_run_preview("docker_full_cleanup", _FULL_CLEANUP_ACTIONS)

    if not confirmed:
        return _confirmation_required("docker_full_cleanup", _FULL_CLEANUP_ACTIONS)

    cleaner = WSLDockerCleaner()
    quick_success = cleaner.docker_cleanup(
        steps=("containers", "images", "volumes", "networks", "system", "builder")
    )
    quick_steps = [result.to_dict() for result in cleaner.last_cleanup_results]
    stop_success = cleaner.stop_docker_wsl()
    compact_success = cleaner.compact_vhdx_files()

    full_result: dict[str, Any] = {
        "executed": True,
        "success": quick_success and stop_success and compact_success,
        "running_containers_preserved": True,
        "quick_cleanup": {
            "success": quick_success,
            "steps": quick_steps,
        },
        "docker_wsl_shutdown": {"success": stop_success},
        "vhdx_compaction": {
            "success": compact_success,
            "steps": [result.to_dict() for result in cleaner.last_compaction_results],
        },
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(full_result, indent=2, ensure_ascii=False)


@mcp.tool()
def port_scan() -> str:
    """Scan listening TCP/UDP ports and top processes by connection count.

    Returns structured data with:
    - Listening TCP ports (port, process, address)
    - Listening UDP ports
    - Top processes by established connection count
    - Summary totals
    """
    try:
        from monitor.port_scanner import run_full_scan

        state = run_full_scan()
        data = {
            "total_tcp": state.total_tcp,
            "total_udp": state.total_udp,
            "total_established": state.total_established,
            "last_scan_time": state.last_scan_time,
            "listening_tcp": [
                {"port": p.porta, "process": p.processo, "address": p.endereco}
                for p in state.listening_tcp[:20]
            ],
            "listening_udp": [
                {"port": p.porta, "process": p.processo, "address": p.endereco}
                for p in state.listening_udp[:20]
            ],
            "top_connections": [
                {
                    "process": pc.nome,
                    "connections": pc.conexoes,
                    "ram_mb": round(pc.memoria_mb, 1),
                }
                for pc in state.top_connections
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_logs(lines: int = 50) -> str:
    """Get recent Varedura log entries.

    Args:
        lines: Number of recent log lines to return (default 50, max 500).

    Reads from the daily log file in the logs/ directory.
    """
    lines_count = min(max(1, lines), 500)
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return json.dumps({"message": "No logs directory found"}, indent=2)

    # Find most recent log file
    log_files = sorted(logs_dir.glob("*.log"), reverse=True)
    if not log_files:
        return json.dumps({"message": "No log files found"}, indent=2)

    log_file = log_files[0]
    try:
        all_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        recent = all_lines[-lines_count:]
        return json.dumps(
            {
                "file": str(log_file),
                "total_lines": len(all_lines),
                "returned_lines": len(recent),
                "content": "\n".join(recent),
            },
            indent=2,
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
