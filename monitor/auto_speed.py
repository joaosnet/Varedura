"""Teste de velocidade automático para alimentar o laudo.

Um único agendador, usado pela TUI (enquanto aberta) e pelo comando headless
``varedura-speedtest`` (cron no Termux, Agendador de Tarefas no Windows).  O
estado em ``~/.varedura_auto_speed.json`` garante que os dois não rodem em
dobro: quem chegar primeiro depois do intervalo executa.

Regras:

- Desligado por padrão (``auto_speed_minutes = 0`` nas preferências de rede).
- **Nunca** roda em dados móveis nem sem rede identificada: cada teste gasta
  dezenas a centenas de MB.
- Cada execução usa um provedor diferente (rodízio) e grava a medição no
  histórico do plano ativo — a mesma fonte que o laudo PDF lê.

Só stdlib no import; os backends pesados são carregados na execução.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

STATE_FILE = Path.home() / ".varedura_auto_speed.json"
MIN_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 1440
BUSY_SECONDS = 600  # uma execução travada deixa de bloquear depois disso
CRON_MARKER = "# VAREDURA-AUTO-SPEEDTEST"
CRON_SCHEDULE = "*/15 * * * *"
WINDOWS_TASK_NAME = "Varedura Speedtest"


def normalize_minutes(value: object) -> int:
    """0 = desligado; valores positivos ficam entre 15 min e 24 h."""
    try:
        minutes = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    if minutes <= 0:
        return 0
    return max(MIN_INTERVAL_MINUTES, min(MAX_INTERVAL_MINUTES, minutes))


def _load_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(state: dict) -> None:
    try:
        tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, STATE_FILE)
    except OSError:
        pass


def last_run(state: dict | None = None) -> float:
    try:
        return float((state if state is not None else _load_state()).get("last_run", 0))
    except (TypeError, ValueError):
        return 0.0


def is_due(minutes: int, now: float | None = None) -> bool:
    """Já passou o intervalo desde a última execução (de quem quer que seja)?"""
    minutes = normalize_minutes(minutes)
    if minutes <= 0:
        return False
    now = time.time() if now is None else now
    return now - last_run() >= minutes * 60


def network_block_reason(network) -> str:
    """``""`` se a rede permite teste automático; senão o motivo."""
    kind = str(getattr(getattr(network, "kind", None), "value", "") or "unknown")
    if kind == "mobile":
        return "mobile"
    if kind == "unknown":
        return "no_network"
    return ""


def run_scheduled(
    *,
    force: bool = False,
    network=None,
    profile=None,
    minutes: int | None = None,
    now: float | None = None,
) -> dict:
    """Executa um teste se for a hora. Devolve ``{"status": ..., ...}``.

    Status: ``disabled``, ``not_due``, ``mobile``, ``no_network``, ``busy``,
    ``failed`` ou ``ok``.  ``force`` ignora o intervalo e o "desligado", mas
    nunca a regra de dados móveis.
    """
    from monitor.plan_profiles import profiles_from_prefs, select_profile

    now = time.time() if now is None else now
    if minutes is None or (profile is None and network is None):
        from cli.ui_shared import load_network_config

        config = load_network_config()
        if minutes is None:
            minutes = normalize_minutes(config.get("auto_speed_minutes", 0))
        if network is None:
            from monitor.netinfo import detect_active_network

            network = detect_active_network()
        if profile is None:
            profile, _reason = select_profile(
                profiles_from_prefs(config.get("plan_profiles")),
                network,
                str(config.get("active_profile_id", "") or ""),
            )
    minutes = normalize_minutes(minutes)
    if not force:
        if minutes <= 0:
            return {"status": "disabled"}
        if not is_due(minutes, now):
            return {"status": "not_due"}
    blocked = network_block_reason(network)
    if blocked:
        return {"status": blocked}

    state = _load_state()
    try:
        running_since = float(state.get("running_since", 0) or 0)
    except (TypeError, ValueError):
        running_since = 0.0
    if now - running_since < BUSY_SECONDS:
        return {"status": "busy"}
    state["running_since"] = now
    _save_state(state)

    result = None
    error = ""
    try:
        from monitor.speed_tester import get_speed_tester

        tester = get_speed_tester()
        # Rodízio entre execuções (cada processo headless começaria do zero).
        tester._provider_index = int(state.get("runs", 0) or 0)
        if not tester.prepare_single_test():
            error = "busy"
        else:
            result = tester.run_once(prepared=True)
            if result is None:
                error = str(tester.get_stats_snapshot().get("last_error") or "failed")
    except Exception as exc:  # backend opcional ausente, rede caiu etc.
        error = str(exc)[:120]
    finally:
        state = _load_state()
        state["running_since"] = 0
        state["runs"] = int(state.get("runs", 0) or 0) + 1
        if result is not None:
            state["last_run"] = now
        else:
            # Falhou: tenta de novo em 15 min, não no intervalo cheio.
            state["last_run"] = now - max(0, minutes - MIN_INTERVAL_MINUTES) * 60
        _save_state(state)

    if result is None:
        return {"status": "busy" if error == "busy" else "failed", "error": error}

    from monitor.data_usage import record_speed_sample
    from monitor.plan_profiles import SpeedSample

    kind = str(getattr(getattr(network, "kind", None), "value", "") or "")
    record_speed_sample(
        SpeedSample(
            timestamp=getattr(result, "timestamp", None) or datetime.datetime.now(),
            down_mbps=float(result.download_mbps),
            up_mbps=float(result.upload_mbps),
            ping_ms=float(getattr(result, "ping_ms", 0.0) or 0.0),
            provider=str(getattr(result, "provider_name", "") or ""),
            server=str(getattr(result, "servidor", "") or ""),
            profile_id=profile.id if profile is not None else "",
            network_kind=kind,
        )
    )
    return {
        "status": "ok",
        "provider": str(getattr(result, "provider_name", "")),
        "download_mbps": round(float(result.download_mbps), 2),
        "upload_mbps": round(float(result.upload_mbps), 2),
        "profile": profile.name if profile is not None else "",
        "network": kind,
    }


# ---------------------------------------------------------------------------
# Segundo plano: cron (Termux/Linux) e Agendador de Tarefas (Windows)
# ---------------------------------------------------------------------------
def _command() -> str:
    exe = shutil.which("varedura-speedtest")
    return exe or f"{sys.executable} -m monitor.auto_speed"


def _read_crontab() -> tuple[bool, list[str], str]:
    exe = shutil.which("crontab")
    if not exe:
        return False, [], "crontab not found"
    try:
        proc = subprocess.run(
            [exe, "-l"], capture_output=True, text=True, errors="replace", timeout=5
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, [], str(exc)
    if proc.returncode != 0:
        if "no crontab" in (proc.stderr or "").lower():
            return True, [], ""
        return False, [], (proc.stderr or "Failed to read crontab").strip()
    return True, proc.stdout.splitlines(), ""


def is_cron_enabled() -> bool:
    ok, lines, _ = _read_crontab()
    return ok and any(
        CRON_MARKER in line and not line.lstrip().startswith("#") for line in lines
    )


def set_cron_enabled(enabled: bool) -> tuple[bool, str]:
    """Instala/remove a entrada do cron, preservando as demais."""
    exe = shutil.which("crontab")
    if not exe:
        return False, "crontab not found"
    ok, lines, err = _read_crontab()
    if not ok:
        return False, err
    kept = [line for line in lines if CRON_MARKER not in line]
    if enabled:
        # A cada 15 min o comando só confere se já é hora (intervalo das prefs).
        kept.append(
            f"{CRON_SCHEDULE} {_command()} --scheduled >/dev/null 2>&1 {CRON_MARKER}"
        )
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
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "Failed to update crontab").strip()
    return True, "cron enabled" if enabled else "cron disabled"


def _windows_task_run() -> str:
    """Linha de comando da tarefa: ``pythonw`` para não piscar uma janela."""
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{runner}" -m monitor.auto_speed --scheduled'


def _schtasks(*args: str) -> tuple[bool, str]:
    exe = shutil.which("schtasks")
    if not exe:
        return False, "schtasks not found"
    try:
        proc = subprocess.run(
            [exe, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    return proc.returncode == 0, (proc.stderr or proc.stdout or "").strip()


def windows_task_command() -> str:
    """Equivalente em linha de comando do interruptor da TUI (referência)."""
    return (
        f'schtasks /Create /F /SC MINUTE /MO 15 /TN "{WINDOWS_TASK_NAME}" '
        f"/TR '{_windows_task_run()}'"
    )


def is_background_enabled() -> bool:
    """Há agendamento em segundo plano? (tarefa no Windows, cron nos demais)."""
    if os.name == "nt":
        return _schtasks("/Query", "/TN", WINDOWS_TASK_NAME)[0]
    return is_cron_enabled()


def set_background_enabled(enabled: bool) -> tuple[bool, str]:
    """Liga/desliga o teste com o app fechado, do jeito de cada sistema.

    Windows: tarefa do usuário atual no Agendador (sem elevação), a cada
    15 min.  Termux/Linux/macOS: entrada no crontab.  Em ambos o comando só
    mede quando o intervalo configurado venceu.
    """
    if os.name != "nt":
        return set_cron_enabled(enabled)
    if enabled:
        return _schtasks(
            "/Create", "/F", "/SC", "MINUTE", "/MO", "15",
            "/TN", WINDOWS_TASK_NAME, "/TR", _windows_task_run(),
        )
    if not is_background_enabled():
        return True, "already disabled"
    return _schtasks("/Delete", "/F", "/TN", WINDOWS_TASK_NAME)


def describe_status() -> dict:
    """Resumo para a TUI: última execução e se o segundo plano está ligado."""
    stamp = last_run()
    return {
        "last_run": datetime.datetime.fromtimestamp(stamp) if stamp else None,
        "background": is_background_enabled(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="varedura-speedtest",
        description="Teste de velocidade automático do Varedura (alimenta o laudo).",
    )
    parser.add_argument(
        "--scheduled", action="store_true", help="Roda só se já passou o intervalo"
    )
    parser.add_argument("--once", action="store_true", help="Roda agora, uma vez")
    parser.add_argument("--status", action="store_true", help="Mostra a configuração")
    parser.add_argument("--cron-on", action="store_true", help="Ativa o cron (Termux/Linux)")
    parser.add_argument("--cron-off", action="store_true", help="Remove o cron")
    parser.add_argument(
        "--windows-task",
        action="store_true",
        help="Imprime o comando do Agendador de Tarefas",
    )
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    args = parser.parse_args(argv)

    if args.cron_on or args.cron_off:
        ok, message = set_cron_enabled(bool(args.cron_on))
        print(message)
        return 0 if ok else 1
    if args.windows_task:
        print(windows_task_command())
        return 0
    if args.status or not (args.scheduled or args.once):
        from cli.ui_shared import load_network_config

        minutes = normalize_minutes(load_network_config().get("auto_speed_minutes", 0))
        stamp = last_run()
        info = {
            "interval_minutes": minutes,
            "last_run": datetime.datetime.fromtimestamp(stamp).isoformat(timespec="seconds")
            if stamp
            else None,
            "cron": is_cron_enabled(),
        }
        print(json.dumps(info) if args.json else " ".join(f"{k}={v}" for k, v in info.items()))
        return 0

    outcome = run_scheduled(force=bool(args.once))
    print(json.dumps(outcome) if args.json else " ".join(f"{k}={v}" for k, v in outcome.items()))
    return 0 if outcome["status"] in {"ok", "not_due", "disabled"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
