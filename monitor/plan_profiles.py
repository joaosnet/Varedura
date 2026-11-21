"""Perfis de plano de internet (banda larga fixa e móvel/pré-pago).

Fonte única do que foi contratado: velocidade de referência, franquia de dados
e a rede (SSID, gateway ou tipo) à qual cada plano se aplica.  Módulo de dados
puros — só stdlib e nenhum I/O no import — para poder ser usado pelas prefs da
TUI sem carregar o monitor.
"""

from __future__ import annotations

import datetime
import hashlib
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from statistics import fmean
from typing import Iterable, Mapping, Sequence

MAX_PROFILES = 8
DEFAULT_CYCLE_DAYS = 30
# Regulamento de qualidade da ANATEL para banda larga: média do período e
# medição instantânea mínimas, em % da velocidade contratada.
AVERAGE_MIN_PCT = 80.0
INSTANT_MIN_PCT = 40.0


class PlanKind(StrEnum):
    FIXED = "fixed"
    MOBILE = "mobile"


class NetworkKind(StrEnum):
    WIFI = "wifi"
    MOBILE = "mobile"
    ETHERNET = "ethernet"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ActiveNetwork:
    """Rede pela qual o tráfego está saindo agora."""

    kind: NetworkKind = NetworkKind.UNKNOWN
    ssid: str = ""
    gateway: str = ""
    interface: str = ""

    def describe(self) -> str:
        if self.kind is NetworkKind.WIFI:
            return f"Wi-Fi {self.ssid}".strip() if self.ssid else "Wi-Fi"
        if self.kind is NetworkKind.MOBILE:
            return "Dados móveis"
        if self.kind is NetworkKind.ETHERNET:
            return "Cabo (Ethernet)"
        return "Rede não identificada"


def _text(value: object, limit: int = 80) -> str:
    cleaned = "".join(ch for ch in str(value or "") if ch.isprintable()).strip()
    return cleaned[:limit]


def _number(value: object, default: float = 0.0, *, minimum: float = 0.0) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return number if number >= minimum else default


def _iso_date(value: object) -> str:
    try:
        return datetime.date.fromisoformat(str(value or "").strip()[:10]).isoformat()
    except ValueError:
        return ""


@dataclass(frozen=True, slots=True)
class PlanProfile:
    id: str
    name: str
    kind: PlanKind = PlanKind.FIXED
    operadora: str = ""
    plano: str = ""
    down_mbps: float = 0.0  # 0 = sem velocidade de referência
    up_mbps: float = 0.0
    quota_gb: float = 0.0  # 0 = sem franquia
    cycle_start: str = ""  # ISO (AAAA-MM-DD); vazio = ainda não informado
    cycle_days: int = DEFAULT_CYCLE_DAYS
    used_offset_gb: float = 0.0  # consumo do ciclo já informado pela operadora
    telefone: str = ""
    email: str = ""
    match_kind: str = ""  # "", "wifi", "mobile", "ethernet"
    match_ssid: str = ""
    match_gateway: str = ""

    @property
    def has_speed_reference(self) -> bool:
        return self.down_mbps > 0 or self.up_mbps > 0

    @property
    def has_quota(self) -> bool:
        return self.quota_gb > 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "PlanProfile | None":
        name = _text(raw.get("name"))
        if not name:
            return None
        try:
            kind = PlanKind(str(raw.get("kind") or PlanKind.FIXED.value))
        except ValueError:
            kind = PlanKind.FIXED
        match_kind = str(raw.get("match_kind") or "").strip().lower()
        if match_kind not in {"wifi", "mobile", "ethernet"}:
            match_kind = ""
        try:
            cycle_days = int(_number(raw.get("cycle_days"), DEFAULT_CYCLE_DAYS))
        except (OverflowError, ValueError):
            cycle_days = DEFAULT_CYCLE_DAYS
        profile_id = _text(raw.get("id"), 40) or new_profile_id(name)
        return cls(
            id=profile_id,
            name=name,
            kind=kind,
            operadora=_text(raw.get("operadora")),
            plano=_text(raw.get("plano")),
            down_mbps=_number(raw.get("down_mbps")),
            up_mbps=_number(raw.get("up_mbps")),
            quota_gb=_number(raw.get("quota_gb")),
            cycle_start=_iso_date(raw.get("cycle_start")),
            cycle_days=cycle_days if 1 <= cycle_days <= 366 else DEFAULT_CYCLE_DAYS,
            used_offset_gb=_number(raw.get("used_offset_gb")),
            telefone=_text(raw.get("telefone"), 40),
            email=_text(raw.get("email"), 120),
            match_kind=match_kind,
            match_ssid=_text(raw.get("match_ssid"), 64),
            match_gateway=_text(raw.get("match_gateway"), 45),
        )


def new_profile_id(seed: str) -> str:
    stamp = datetime.datetime.now().isoformat()
    digest = hashlib.sha256(f"{seed}|{stamp}".encode("utf-8")).hexdigest()[:10]
    return f"plan_{digest}"


def profiles_from_prefs(raw: object) -> list[PlanProfile]:
    """Valida a lista salva nas prefs, descartando entradas inválidas/duplicadas."""
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    profiles: list[PlanProfile] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        profile = PlanProfile.from_dict(item)
        if profile is None or profile.id in seen:
            continue
        seen.add(profile.id)
        profiles.append(profile)
        if len(profiles) >= MAX_PROFILES:
            break
    return profiles


def profiles_to_prefs(profiles: Iterable[PlanProfile]) -> list[dict]:
    return [profile.to_dict() for profile in profiles]


def legacy_fixed_profile(down_mbps: float, up_mbps: float) -> PlanProfile:
    """Perfil criado na migração a partir de ``contracted_down``/``contracted_up``."""
    return PlanProfile(
        id="plan_legacy_fixed",
        name="Banda larga",
        kind=PlanKind.FIXED,
        down_mbps=max(0.0, float(down_mbps)),
        up_mbps=max(0.0, float(up_mbps)),
    )


def find_profile(profiles: Sequence[PlanProfile], profile_id: str) -> PlanProfile | None:
    return next((item for item in profiles if item.id == profile_id), None)


def select_profile(
    profiles: Sequence[PlanProfile],
    network: ActiveNetwork | None,
    manual_id: str = "",
) -> tuple[PlanProfile | None, str]:
    """Escolhe o perfil aplicável e devolve ``(perfil, motivo)``.

    Prioridade: escolha manual > SSID > gateway > tipo de rede > perfil único.
    ``motivo`` é um de ``manual``, ``ssid``, ``gateway``, ``kind``, ``only``, ``""``.
    """
    if manual_id:
        manual = find_profile(profiles, manual_id)
        if manual is not None:
            return manual, "manual"
    if network is not None:
        ssid = network.ssid.strip().casefold()
        if ssid:
            for profile in profiles:
                if profile.match_ssid and profile.match_ssid.casefold() == ssid:
                    return profile, "ssid"
        if network.gateway and network.kind is not NetworkKind.MOBILE:
            for profile in profiles:
                if profile.match_gateway and profile.match_gateway == network.gateway:
                    return profile, "gateway"
        if network.kind is not NetworkKind.UNKNOWN:
            generic = [
                profile
                for profile in profiles
                if profile.match_kind == network.kind.value
                and not profile.match_ssid
                and not profile.match_gateway
            ]
            if generic:
                return generic[0], "kind"
            if network.kind is NetworkKind.MOBILE:
                mobile = [p for p in profiles if p.kind is PlanKind.MOBILE]
                if len(mobile) == 1:
                    return mobile[0], "kind"
                # Nunca confere dados móveis contra um plano de banda larga fixa.
                return None, ""
    # Fora dos dados móveis, um único plano fixo vale para a rede atual — desde
    # que não esteja associado explicitamente a outra rede conhecida.
    fixed = [p for p in profiles if p.kind is PlanKind.FIXED]
    if len(fixed) == 1 and (network is None or network.kind is not NetworkKind.MOBILE):
        only = fixed[0]
        elsewhere = network is not None and (
            (
                only.match_ssid
                and network.ssid
                and only.match_ssid.casefold() != network.ssid.casefold()
            )
            or (
                only.match_gateway
                and network.gateway
                and only.match_gateway != network.gateway
            )
        )
        if not elsewhere:
            return only, "only"
    return None, ""


def bind_to_network(profile: PlanProfile, network: ActiveNetwork) -> PlanProfile:
    """Associa o perfil à rede atual (SSID quando houver, senão gateway/tipo)."""
    data = profile.to_dict()
    kind = network.kind.value if network.kind is not NetworkKind.UNKNOWN else ""
    data["match_kind"] = kind
    data["match_ssid"] = network.ssid if network.kind is NetworkKind.WIFI else ""
    data["match_gateway"] = (
        network.gateway
        if network.kind in {NetworkKind.WIFI, NetworkKind.ETHERNET} and not network.ssid
        else ""
    )
    return PlanProfile.from_dict(data) or profile


def describe_binding(profile: PlanProfile) -> str:
    if profile.match_ssid:
        return f"Wi-Fi {profile.match_ssid}"
    if profile.match_gateway:
        return f"gateway {profile.match_gateway}"
    return {
        "wifi": "qualquer Wi-Fi",
        "mobile": "dados móveis",
        "ethernet": "cabo (Ethernet)",
    }.get(profile.match_kind, "")


# ---------------------------------------------------------------------------
# Conformidade de velocidade
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SpeedSample:
    timestamp: datetime.datetime
    down_mbps: float
    up_mbps: float
    ping_ms: float = 0.0
    provider: str = ""
    server: str = ""
    profile_id: str = ""
    network_kind: str = ""


@dataclass(frozen=True, slots=True)
class SpeedVerdict:
    samples: int = 0
    has_reference: bool = False
    avg_down: float = 0.0
    avg_up: float = 0.0
    min_down: float = 0.0
    min_up: float = 0.0
    max_down: float = 0.0
    max_up: float = 0.0
    pct_down: float | None = None  # média em % do contratado
    pct_up: float | None = None
    average_ok: bool | None = None  # None = sem dados ou sem referência
    instant_violations: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def status(self) -> str:
        """``no_data`` | ``no_reference`` | ``ok`` | ``below``."""
        if self.samples == 0:
            return "no_data"
        if not self.has_reference:
            return "no_reference"
        return "ok" if self.average_ok and not self.instant_violations else "below"


def evaluate_speed(
    profile: PlanProfile | None,
    samples: Sequence[SpeedSample],
    *,
    average_min_pct: float = AVERAGE_MIN_PCT,
    instant_min_pct: float = INSTANT_MIN_PCT,
) -> SpeedVerdict:
    """Compara as medições com a velocidade de referência do plano."""
    has_reference = bool(profile and profile.has_speed_reference)
    if not samples:
        return SpeedVerdict(has_reference=has_reference)
    downs = [max(0.0, sample.down_mbps) for sample in samples]
    # Upload 0 = não medido pelo provedor: fica fora de média e veredito.
    ups = [sample.up_mbps for sample in samples if sample.up_mbps > 0] or [0.0]
    base = dict(
        samples=len(samples),
        has_reference=has_reference,
        avg_down=fmean(downs),
        avg_up=fmean(ups),
        min_down=min(downs),
        min_up=min(ups),
        max_down=max(downs),
        max_up=max(ups),
    )
    if not has_reference or profile is None:
        return SpeedVerdict(**base)

    pct_down = base["avg_down"] / profile.down_mbps * 100 if profile.down_mbps else None
    pct_up = base["avg_up"] / profile.up_mbps * 100 if profile.up_mbps else None
    checks = [pct for pct in (pct_down, pct_up) if pct is not None]
    violations = 0
    for sample in samples:
        down, up = max(0.0, sample.down_mbps), sample.up_mbps
        below_down = profile.down_mbps and down / profile.down_mbps * 100 < instant_min_pct
        below_up = (
            profile.up_mbps and up > 0 and up / profile.up_mbps * 100 < instant_min_pct
        )
        if below_down or below_up:
            violations += 1
    return SpeedVerdict(
        **base,
        pct_down=pct_down,
        pct_up=pct_up,
        average_ok=all(pct >= average_min_pct for pct in checks),
        instant_violations=violations,
    )


# ---------------------------------------------------------------------------
# Ciclo de franquia
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class CycleWindow:
    start: datetime.date
    end: datetime.date  # exclusivo: primeiro dia do ciclo seguinte

    def days_total(self) -> int:
        return max(1, (self.end - self.start).days)

    def days_elapsed(self, today: datetime.date) -> int:
        return min(self.days_total(), max(0, (today - self.start).days))

    def days_left(self, today: datetime.date) -> int:
        return max(0, (self.end - today).days)


def current_cycle(
    profile: PlanProfile, today: datetime.date | None = None
) -> CycleWindow:
    """Janela do ciclo vigente, avançando em passos de ``cycle_days``."""
    today = today or datetime.date.today()
    days = profile.cycle_days if profile.cycle_days > 0 else DEFAULT_CYCLE_DAYS
    try:
        start = datetime.date.fromisoformat(profile.cycle_start)
    except ValueError:
        start = today
    if start > today:
        start = today
    elapsed_cycles = (today - start).days // days
    start = start + datetime.timedelta(days=elapsed_cycles * days)
    return CycleWindow(start, start + datetime.timedelta(days=days))


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    quota_gb: float
    used_gb: float
    cycle: CycleWindow
    days_left: int
    projected_gb: float | None  # consumo projetado ao fim do ciclo

    @property
    def remaining_gb(self) -> float:
        return max(0.0, self.quota_gb - self.used_gb)

    @property
    def used_pct(self) -> float:
        return self.used_gb / self.quota_gb * 100 if self.quota_gb > 0 else 0.0

    @property
    def exceeded(self) -> bool:
        return self.quota_gb > 0 and self.used_gb >= self.quota_gb

    @property
    def will_exceed(self) -> bool:
        return (
            self.quota_gb > 0
            and self.projected_gb is not None
            and self.projected_gb > self.quota_gb
        )


def quota_status(
    profile: PlanProfile,
    measured_bytes: int,
    today: datetime.date | None = None,
) -> QuotaStatus:
    """Consumo do ciclo = contador medido + ajuste informado pelo usuário."""
    today = today or datetime.date.today()
    cycle = current_cycle(profile, today)
    used_gb = max(0, int(measured_bytes)) / 1024**3 + profile.used_offset_gb
    elapsed = cycle.days_elapsed(today)
    projected = used_gb / elapsed * cycle.days_total() if elapsed >= 1 else None
    return QuotaStatus(
        quota_gb=profile.quota_gb,
        used_gb=used_gb,
        cycle=cycle,
        days_left=cycle.days_left(today),
        projected_gb=projected,
    )


def apply_profile(profile: PlanProfile | None, network: ActiveNetwork | None = None) -> None:
    """Único ponto que propaga o plano para o teste de velocidade e o relatório."""
    from monitor.speed_tester import speed_config

    speed_config.velocidade_contratada_down = profile.down_mbps if profile else 0.0
    speed_config.velocidade_contratada_up = profile.up_mbps if profile else 0.0

    import monitor.stalker as stalker

    stalker.set_contract(profile, network)


__all__ = [
    "AVERAGE_MIN_PCT",
    "INSTANT_MIN_PCT",
    "ActiveNetwork",
    "CycleWindow",
    "NetworkKind",
    "PlanKind",
    "PlanProfile",
    "QuotaStatus",
    "SpeedSample",
    "SpeedVerdict",
    "apply_profile",
    "bind_to_network",
    "current_cycle",
    "describe_binding",
    "evaluate_speed",
    "find_profile",
    "legacy_fixed_profile",
    "new_profile_id",
    "profiles_from_prefs",
    "profiles_to_prefs",
    "quota_status",
    "select_profile",
]
