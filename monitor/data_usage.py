"""Consumo de dados por ciclo de franquia e histórico persistente de velocidade.

O Android só expõe contadores acumulados desde o boot (``/proc/net/dev``).
Este módulo transforma esses contadores em consumo por ciclo: guarda o último
valor bruto visto e soma apenas o delta.  Se o contador regride (reboot ou
reset da interface), a base é reiniciada sem perder o acumulado.

Limitação conhecida: o tráfego entre a última leitura e um reboot não é
contado.  ``PlanProfile.used_offset_gb`` permite acertar com o valor informado
pela operadora.

Só stdlib e nenhum I/O no import.
"""

from __future__ import annotations

import datetime
import json
import os
import threading
import time
from pathlib import Path
from typing import Iterable

from monitor.plan_profiles import PlanProfile, SpeedSample, current_cycle

USAGE_FILE = Path.home() / ".varedura_usage.json"
SPEED_HISTORY_FILE = Path.home() / ".varedura_speed_history.jsonl"
SAVE_INTERVAL_SECONDS = 60.0
MAX_SPEED_RECORDS = 5000


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class DataUsageTracker:
    """Acumula bytes de dados móveis por perfil dentro do ciclo vigente."""

    def __init__(self, path: Path | None = None) -> None:
        self._explicit_path = path
        self._lock = threading.Lock()
        self._state: dict[str, dict] | None = None
        self._dirty = False
        self._last_save = 0.0

    @property
    def _path(self) -> Path:
        # Resolvido na hora do uso para os testes poderem redirecionar USAGE_FILE.
        return self._explicit_path or USAGE_FILE

    def _load(self) -> dict[str, dict]:
        if self._state is None:
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raw = {}
            self._state = (
                {str(k): v for k, v in raw.items() if isinstance(v, dict)}
                if isinstance(raw, dict)
                else {}
            )
        return self._state

    def _entry(self, profile: PlanProfile, today: datetime.date) -> dict:
        state = self._load()
        cycle_start = current_cycle(profile, today).start.isoformat()
        entry = state.get(profile.id)
        if entry is None or entry.get("cycle_start") != cycle_start:
            # Ciclo novo: zera o acumulado, mas mantém a base do contador para
            # não contar de novo o que já trafegou antes da virada.
            entry = {
                "cycle_start": cycle_start,
                "bytes": 0,
                "last_raw": entry.get("last_raw") if entry else None,
            }
            state[profile.id] = entry
            self._dirty = True
        return entry

    def update(
        self,
        profile: PlanProfile,
        raw_bytes: int,
        today: datetime.date | None = None,
        *,
        force_save: bool = False,
    ) -> int:
        """Registra o contador bruto atual e devolve os bytes do ciclo."""
        today = today or datetime.date.today()
        raw = max(0, int(raw_bytes))
        with self._lock:
            entry = self._entry(profile, today)
            last = entry.get("last_raw")
            if isinstance(last, int) and raw >= last:
                delta = raw - last
            elif isinstance(last, int):
                delta = raw  # contador reiniciou: tudo desde o boot é novo
            else:
                delta = 0  # primeira leitura só define a base
            if delta or last != raw:
                entry["bytes"] = int(entry.get("bytes", 0)) + delta
                entry["last_raw"] = raw
                self._dirty = True
            self._save_locked(force_save)
            return int(entry["bytes"])

    def cycle_bytes(self, profile: PlanProfile, today: datetime.date | None = None) -> int:
        today = today or datetime.date.today()
        with self._lock:
            return int(self._entry(profile, today).get("bytes", 0))

    def reset(self, profile: PlanProfile) -> None:
        """Zera o acumulado do ciclo (usado ao editar o início do ciclo)."""
        with self._lock:
            entry = self._load().get(profile.id)
            if entry is not None:
                entry["bytes"] = 0
                self._dirty = True
                self._save_locked(True)

    def flush(self) -> None:
        with self._lock:
            self._save_locked(True)

    def _save_locked(self, force: bool) -> None:
        if not self._dirty or self._state is None:
            return
        now = time.monotonic()
        if not force and now - self._last_save < SAVE_INTERVAL_SECONDS:
            return
        try:
            _atomic_write(self._path, json.dumps(self._state, indent=2))
        except OSError:
            return
        self._dirty = False
        self._last_save = now


_tracker: DataUsageTracker | None = None
_tracker_lock = threading.Lock()


def get_usage_tracker() -> DataUsageTracker:
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = DataUsageTracker()
        return _tracker


# ---------------------------------------------------------------------------
# Histórico de velocidade (JSON Lines, uma medição por linha)
# ---------------------------------------------------------------------------
_speed_lock = threading.Lock()


def record_speed_sample(sample: SpeedSample, path: Path | None = None) -> None:
    """Acrescenta uma medição ao histórico persistente (falhas são ignoradas)."""
    target = path or SPEED_HISTORY_FILE
    line = json.dumps(
        {
            "ts": sample.timestamp.isoformat(timespec="seconds"),
            "down": round(float(sample.down_mbps), 3),
            "up": round(float(sample.up_mbps), 3),
            "ping": round(float(sample.ping_ms), 1),
            "provider": sample.provider,
            "server": sample.server,
            "profile": sample.profile_id,
            "net": sample.network_kind,
        },
        ensure_ascii=False,
    )
    with _speed_lock:
        try:
            with target.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass


def load_speed_samples(
    *,
    profile_id: str | None = None,
    since: datetime.datetime | None = None,
    path: Path | None = None,
) -> list[SpeedSample]:
    """Lê o histórico, filtrando por perfil e data; linhas inválidas são puladas."""
    target = path or SPEED_HISTORY_FILE
    with _speed_lock:
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
    samples: list[SpeedSample] = []
    for line in lines[-MAX_SPEED_RECORDS:]:
        try:
            raw = json.loads(line)
            stamp = datetime.datetime.fromisoformat(str(raw["ts"]))
            sample = SpeedSample(
                timestamp=stamp,
                down_mbps=float(raw["down"]),
                up_mbps=float(raw["up"]),
                ping_ms=float(raw.get("ping") or 0.0),
                provider=str(raw.get("provider") or ""),
                server=str(raw.get("server") or ""),
                profile_id=str(raw.get("profile") or ""),
                network_kind=str(raw.get("net") or ""),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if profile_id is not None and sample.profile_id != profile_id:
            continue
        if since is not None and sample.timestamp < since:
            continue
        samples.append(sample)
    return samples


def samples_for_report(
    profile: PlanProfile | None,
    session_samples: Iterable[SpeedSample] = (),
    *,
    now: datetime.datetime | None = None,
    path: Path | None = None,
) -> list[SpeedSample]:
    """Medições do perfil no ciclo vigente (ou últimos 30 dias sem ciclo).

    Junta o histórico persistido com as medições da sessão ainda não gravadas,
    sem duplicar pelo carimbo de tempo.
    """
    now = now or datetime.datetime.now()
    if profile is not None and profile.cycle_start:
        start = current_cycle(profile, now.date()).start
        since = datetime.datetime.combine(start, datetime.time.min)
    else:
        since = now - datetime.timedelta(days=30)
    stored = load_speed_samples(
        profile_id=profile.id if profile is not None else None,
        since=since,
        path=path,
    )
    seen = {sample.timestamp.replace(microsecond=0) for sample in stored}
    for sample in session_samples:
        key = sample.timestamp.replace(microsecond=0)
        if key not in seen and sample.timestamp >= since:
            stored.append(sample)
            seen.add(key)
    stored.sort(key=lambda item: item.timestamp)
    return stored


__all__ = [
    "DataUsageTracker",
    "SPEED_HISTORY_FILE",
    "USAGE_FILE",
    "get_usage_tracker",
    "load_speed_samples",
    "record_speed_sample",
    "samples_for_report",
]
