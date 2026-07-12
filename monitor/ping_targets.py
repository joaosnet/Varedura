"""Ping target catalogue, validation and ICMP probe primitives.

This module is deliberately independent from either TUI.  Importing it performs
no DNS lookup, starts no thread and creates no subprocess; callers opt in to
network activity by calling :func:`probe_ping`.
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import platform
import re
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping, Sequence


NETWORK_SCHEMA_VERSION = 3
MAX_PERSISTENT_TARGETS = 5
LEGACY_DEFAULT_HOST = "ec2.sa-east-1.amazonaws.com"


class TargetCategory(StrEnum):
    """Sections shown by a target picker."""

    INFRASTRUCTURE = "infrastructure"
    WEB = "web"
    GAME = "game"
    CUSTOM = "custom"
    LEAGUE_MATCH = "league_match"
    GATEWAY = "gateway"


class HostKind(StrEnum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    HOSTNAME = "hostname"


class PingStatus(StrEnum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    DNS_ERROR = "dns_error"
    PERMISSION_DENIED = "permission_denied"
    CANCELLED = "cancelled"
    TOOL_MISSING = "tool_missing"
    INVALID_TARGET = "invalid_target"
    ICMP_FILTERED = "icmp_filtered"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ValidatedTarget:
    """Canonical representation of user-provided ping input."""

    original: str
    host: str
    kind: HostKind
    is_private: bool = False
    is_loopback: bool = False
    is_link_local: bool = False

    def __str__(self) -> str:
        return self.host


def validate_host(value: str) -> ValidatedTarget:
    """Validate and canonicalize an IP address or IDNA hostname.

    URLs, ports, CIDRs, wildcards, shell-like options and control characters are
    rejected before they can become subprocess arguments.  Private and
    institutional addresses are intentionally accepted and flagged in the
    return value.
    """

    if not isinstance(value, str):
        raise ValueError("host must be text")
    original = value
    value = value.strip()
    if not value or len(value) > 1024:
        raise ValueError("host cannot be empty")
    if value.startswith("-"):
        raise ValueError("command options are not hosts")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("control characters are not allowed")
    if any(char.isspace() for char in value):
        raise ValueError("whitespace is not allowed inside a host")
    if any(token in value for token in ("://", "/", "?", "#", "@", "\\", "*")):
        raise ValueError("enter an IP or hostname, not a URL, CIDR or wildcard")
    if value.startswith("[") or value.endswith("]"):
        raise ValueError("IPv6 addresses must not use URL brackets")

    ip_value = value.split("%", 1)[0] if "%" in value else value
    if "%" in value:
        raise ValueError("IPv6 zone identifiers are not accepted")
    try:
        address = ipaddress.ip_address(ip_value)
    except ValueError:
        address = None

    if address is not None:
        if (
            address.is_unspecified
            or address.is_multicast
            or address == ipaddress.IPv4Address("255.255.255.255")
        ):
            raise ValueError(
                "unspecified, multicast and broadcast addresses are not valid targets"
            )
        kind = HostKind.IPV4 if address.version == 4 else HostKind.IPV6
        return ValidatedTarget(
            original=original,
            host=address.compressed,
            kind=kind,
            is_private=address.is_private,
            is_loopback=address.is_loopback,
            is_link_local=address.is_link_local,
        )

    if ":" in value:
        raise ValueError("hostnames cannot contain a port")
    hostname = value[:-1] if value.endswith(".") else value
    if not hostname or len(hostname) > 253:
        raise ValueError("hostname is too long")
    try:
        import idna

        ascii_host = idna.encode(
            hostname,
            uts46=True,
            std3_rules=True,
            transitional=False,
        ).decode("ascii")
    except (ImportError, UnicodeError, ValueError) as exc:
        raise ValueError("invalid IDNA hostname") from exc
    ascii_host = ascii_host.lower()
    labels = ascii_host.split(".")
    if any(
        not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
        for label in labels
    ):
        raise ValueError("invalid hostname label")
    return ValidatedTarget(original, ascii_host, HostKind.HOSTNAME)


@dataclass(frozen=True, slots=True)
class PingTarget:
    """A named ICMP destination.

    ``ephemeral`` targets (the gateway and the current League match) must never
    be persisted in :class:`TargetSelection`.
    """

    id: str
    label: str
    host: str
    category: TargetCategory
    description: str = ""
    warning: str = ""
    ephemeral: bool = False

    def __post_init__(self) -> None:
        if not self.id or not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{0,95}", self.id):
            raise ValueError("invalid target id")
        canonical = validate_host(self.host).host
        object.__setattr__(self, "host", canonical)
        label = self.label.strip()
        if not label:
            raise ValueError("target label cannot be empty")
        if (
            len(label) > 96
            or any(ord(char) < 32 or ord(char) == 127 for char in label)
            or "[" in label
            or "]" in label
        ):
            raise ValueError("target label contains unsafe formatting")
        object.__setattr__(self, "label", label)


@dataclass(frozen=True, slots=True)
class PingProbeResult:
    """Structured result used by the scheduler, UI and report exporters."""

    target_id: str
    generation: int
    host: str
    status: PingStatus
    started_monotonic: float
    completed_monotonic: float
    latency_ms: float | None = None
    method: str = "icmp"
    detail: str = ""
    returncode: int | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        return self.status is PingStatus.SUCCESS

    @property
    def duration_ms(self) -> float:
        return max(0.0, (self.completed_monotonic - self.started_monotonic) * 1000)


@dataclass(frozen=True, slots=True)
class PingSample:
    target_id: str
    generation: int
    observed_at: datetime
    latency_ms: float | None
    status: PingStatus

    @classmethod
    def from_result(cls, result: PingProbeResult) -> "PingSample":
        return cls(
            target_id=result.target_id,
            generation=result.generation,
            observed_at=result.observed_at,
            latency_ms=result.latency_ms,
            status=result.status,
        )


_FORTNITE_DESCRIPTION = "Endpoint regional de latencia publicado pela Epic."
_WEB_WARNING = "Frontends/CDNs podem bloquear ICMP mesmo quando o site funciona."
_LOL_WARNING = "Representa a rota publica/API BR1; nao e o servidor da partida atual."


TARGET_CATALOG: tuple[PingTarget, ...] = (
    PingTarget(
        "cloudflare_ipv4",
        "Cloudflare DNS (IPv4)",
        "1.1.1.1",
        TargetCategory.INFRASTRUCTURE,
    ),
    PingTarget(
        "cloudflare_ipv6",
        "Cloudflare DNS (IPv6)",
        "2606:4700:4700::1111",
        TargetCategory.INFRASTRUCTURE,
    ),
    PingTarget(
        "google_ipv4",
        "Google Public DNS (IPv4)",
        "8.8.8.8",
        TargetCategory.INFRASTRUCTURE,
    ),
    PingTarget(
        "google_ipv6",
        "Google Public DNS (IPv6)",
        "2001:4860:4860::8888",
        TargetCategory.INFRASTRUCTURE,
    ),
    PingTarget(
        "quad9_ipv4",
        "Quad9 DNS (IPv4)",
        "9.9.9.9",
        TargetCategory.INFRASTRUCTURE,
    ),
    PingTarget(
        "quad9_ipv6",
        "Quad9 DNS (IPv6)",
        "2620:fe::fe",
        TargetCategory.INFRASTRUCTURE,
    ),
    PingTarget(
        "web_google",
        "Google",
        "www.google.com",
        TargetCategory.WEB,
        warning=_WEB_WARNING,
    ),
    PingTarget(
        "web_youtube",
        "YouTube",
        "www.youtube.com",
        TargetCategory.WEB,
        warning=_WEB_WARNING,
    ),
    PingTarget(
        "web_github",
        "GitHub",
        "github.com",
        TargetCategory.WEB,
        warning=_WEB_WARNING,
    ),
    PingTarget(
        "web_microsoft",
        "Microsoft",
        "www.microsoft.com",
        TargetCategory.WEB,
        warning=_WEB_WARNING,
    ),
    PingTarget(
        "web_whatsapp",
        "WhatsApp Web",
        "web.whatsapp.com",
        TargetCategory.WEB,
        warning=_WEB_WARNING,
    ),
    PingTarget(
        "fortnite_br",
        "Fortnite - Brasil",
        "ping-br.ds.on.epicgames.com",
        TargetCategory.GAME,
        description=_FORTNITE_DESCRIPTION,
    ),
    PingTarget(
        "fortnite_nae",
        "Fortnite - America do Norte (Leste)",
        "ping-nae.ds.on.epicgames.com",
        TargetCategory.GAME,
        description=_FORTNITE_DESCRIPTION,
    ),
    PingTarget(
        "fortnite_nac",
        "Fortnite - America do Norte (Central)",
        "ping-nac.ds.on.epicgames.com",
        TargetCategory.GAME,
        description=_FORTNITE_DESCRIPTION,
    ),
    PingTarget(
        "fortnite_naw",
        "Fortnite - America do Norte (Oeste)",
        "ping-naw.ds.on.epicgames.com",
        TargetCategory.GAME,
        description=_FORTNITE_DESCRIPTION,
    ),
    PingTarget(
        "fortnite_eu",
        "Fortnite - Europa",
        "ping-eu.ds.on.epicgames.com",
        TargetCategory.GAME,
        description=_FORTNITE_DESCRIPTION,
    ),
    PingTarget(
        "fortnite_asia",
        "Fortnite - Asia",
        "ping-asia.ds.on.epicgames.com",
        TargetCategory.GAME,
        description=_FORTNITE_DESCRIPTION,
    ),
    PingTarget(
        "fortnite_oce",
        "Fortnite - Oceania",
        "ping-oce.ds.on.epicgames.com",
        TargetCategory.GAME,
        description=_FORTNITE_DESCRIPTION,
    ),
    PingTarget(
        "fortnite_me",
        "Fortnite - Oriente Medio",
        "ping-me.ds.on.epicgames.com",
        TargetCategory.GAME,
        description=_FORTNITE_DESCRIPTION,
    ),
    PingTarget(
        "lol_br1_api",
        "League of Legends - BR1",
        "br1.api.riotgames.com",
        TargetCategory.GAME,
        warning=_LOL_WARNING,
    ),
)

_CATALOG_BY_ID = {target.id: target for target in TARGET_CATALOG}


def target_catalog(
    category: TargetCategory | str | None = None,
) -> tuple[PingTarget, ...]:
    """Return the immutable built-in catalogue, optionally filtered."""

    if category is None:
        return TARGET_CATALOG
    wanted = TargetCategory(category)
    return tuple(target for target in TARGET_CATALOG if target.category is wanted)


def target_by_id(target_id: str) -> PingTarget | None:
    return _CATALOG_BY_ID.get(target_id)


def create_custom_target(host: str, label: str | None = None) -> PingTarget:
    validated = validate_host(host)
    digest = hashlib.blake2s(validated.host.encode("ascii"), digest_size=8).hexdigest()
    return PingTarget(
        id=f"custom_{digest}",
        label=(label or validated.host).strip(),
        host=validated.host,
        category=TargetCategory.CUSTOM,
        warning=(
            "Endereco privado/institucional; os resultados dependem da rede atual."
            if validated.is_private
            else ""
        ),
    )


@dataclass(frozen=True, slots=True)
class TargetSelection:
    """Validated persistent selection stored under the network preferences."""

    targets: tuple[PingTarget, ...] = ()
    primary_target_id: str | None = None
    league_auto_detect: bool = True
    onboarding_completed: bool = False

    def __post_init__(self) -> None:
        if len(self.targets) > MAX_PERSISTENT_TARGETS:
            raise ValueError(f"at most {MAX_PERSISTENT_TARGETS} targets are allowed")
        ids = [target.id for target in self.targets]
        if len(set(ids)) != len(ids):
            raise ValueError("target ids must be unique")
        if any(target.ephemeral for target in self.targets):
            raise ValueError("ephemeral targets cannot be persisted")
        if self.targets and self.primary_target_id not in ids:
            raise ValueError("the primary target must be selected")
        if not self.targets and self.primary_target_id is not None:
            raise ValueError("an empty selection cannot have a primary target")
        if self.onboarding_completed and not self.targets:
            raise ValueError("completed onboarding requires at least one target")

    @property
    def selected_target_ids(self) -> tuple[str, ...]:
        return tuple(target.id for target in self.targets)

    @property
    def primary_target(self) -> PingTarget | None:
        return next(
            (target for target in self.targets if target.id == self.primary_target_id),
            None,
        )

    def to_config(self) -> dict[str, Any]:
        custom_targets = [
            {"id": target.id, "label": target.label, "host": target.host}
            for target in self.targets
            if target.category is TargetCategory.CUSTOM
        ]
        return {
            "network_schema_version": NETWORK_SCHEMA_VERSION,
            "target_onboarding_completed": self.onboarding_completed,
            "selected_target_ids": list(self.selected_target_ids),
            "primary_target_id": self.primary_target_id,
            "custom_targets": custom_targets,
            "league_auto_detect": self.league_auto_detect,
        }

    @classmethod
    def from_config(cls, config: Mapping[str, Any] | None) -> "TargetSelection":
        """Load schema v3 or migrate the former single ``external_host`` value.

        Corrupt entries are ignored and the first valid selected target repairs a
        missing primary.  The legacy automatic EC2 default intentionally opens
        onboarding instead of silently starting external traffic.
        """

        raw: Mapping[str, Any] = config or {}
        nested = raw.get("network")
        if isinstance(nested, Mapping) and "network_schema_version" not in raw:
            raw = nested

        try:
            schema = int(raw.get("network_schema_version", 0) or 0)
        except (TypeError, ValueError):
            schema = 0
        if schema < NETWORK_SCHEMA_VERSION:
            return cls._from_legacy_config(raw)

        resolved: dict[str, PingTarget] = dict(_CATALOG_BY_ID)
        custom_items = raw.get("custom_targets", ())
        if isinstance(custom_items, Sequence) and not isinstance(
            custom_items, (str, bytes)
        ):
            for item in custom_items:
                if not isinstance(item, Mapping):
                    continue
                try:
                    custom = create_custom_target(
                        str(item.get("host", "")),
                        str(item.get("label", "")).strip() or None,
                    )
                except ValueError:
                    continue
                resolved[custom.id] = custom
                stored_id = item.get("id")
                if isinstance(stored_id, str) and stored_id.startswith("custom_"):
                    # Keep a prior stable id when it is syntactically safe.
                    try:
                        custom = PingTarget(
                            stored_id,
                            custom.label,
                            custom.host,
                            TargetCategory.CUSTOM,
                            warning=custom.warning,
                        )
                    except ValueError:
                        pass
                    else:
                        resolved[stored_id] = custom

        selected_ids = raw.get("selected_target_ids", ())
        if not isinstance(selected_ids, Sequence) or isinstance(
            selected_ids, (str, bytes)
        ):
            selected_ids = ()
        targets: list[PingTarget] = []
        seen: set[str] = set()
        for target_id in selected_ids:
            if not isinstance(target_id, str) or target_id in seen:
                continue
            target = resolved.get(target_id)
            if target is None or target.ephemeral:
                continue
            seen.add(target_id)
            targets.append(target)
            if len(targets) == MAX_PERSISTENT_TARGETS:
                break

        primary = raw.get("primary_target_id")
        if not isinstance(primary, str) or primary not in seen:
            primary = targets[0].id if targets else None
        return cls(
            targets=tuple(targets),
            primary_target_id=primary,
            league_auto_detect=bool(raw.get("league_auto_detect", True)),
            onboarding_completed=bool(
                targets and raw.get("target_onboarding_completed", False)
            ),
        )

    @classmethod
    def _from_legacy_config(cls, raw: Mapping[str, Any]) -> "TargetSelection":
        old_host = raw.get("external_host", raw.get("external_ip", ""))
        if not isinstance(old_host, str):
            old_host = ""
        if not old_host.strip() or old_host.strip().lower() == LEGACY_DEFAULT_HOST:
            return cls(
                league_auto_detect=bool(raw.get("league_auto_detect", True)),
                onboarding_completed=False,
            )
        try:
            target = create_custom_target(old_host)
        except ValueError:
            return cls(
                league_auto_detect=bool(raw.get("league_auto_detect", True)),
                onboarding_completed=False,
            )
        return cls(
            targets=(target,),
            primary_target_id=target.id,
            league_auto_detect=bool(raw.get("league_auto_detect", True)),
            onboarding_completed=True,
        )


_PING_TIME = re.compile(
    r"(?:time|tempo)\s*[=<]\s*(?P<value>\d+(?:[.,]\d+)?)\s*ms",
    re.IGNORECASE,
)
_GENERIC_PING_TIME = re.compile(r"(?P<value>\d+(?:[.,]\d+)?)\s*ms", re.IGNORECASE)


def parse_ping_latency(output: str | bytes) -> float | None:
    if isinstance(output, bytes):
        output = output.decode(errors="ignore")
    match = _PING_TIME.search(output)
    if not match:
        match = _GENERIC_PING_TIME.search(output)
    if not match:
        return None
    value = float(match.group("value").replace(",", "."))
    prefix = output[match.start() : match.end()]
    return min(value, 0.5) if "<" in prefix and value <= 1 else value


def build_ping_command(
    host: str,
    *,
    timeout_seconds: float = 1.0,
    system: str | None = None,
) -> list[str]:
    validated = validate_host(host)
    system_name = (system or platform.system()).lower()
    family_args = (
        ["-6"]
        if validated.kind is HostKind.IPV6
        else ["-4"]
        if validated.kind is HostKind.IPV4
        else []
    )
    if system_name == "windows":
        return [
            "ping",
            *family_args,
            "-n",
            "1",
            "-w",
            str(max(1, int(timeout_seconds * 1000))),
            validated.host,
        ]
    if system_name == "darwin":
        executable = "ping6" if validated.kind is HostKind.IPV6 else "ping"
        return [
            executable,
            "-c",
            "1",
            "-W",
            str(max(1, int(timeout_seconds * 1000))),
            validated.host,
        ]
    return [
        "ping",
        *family_args,
        "-c",
        "1",
        "-W",
        str(max(1, int(timeout_seconds + 0.999))),
        validated.host,
    ]


def _terminate_process(process: subprocess.Popen[str], *, grace: float = 0.2) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name != "nt" and getattr(process, "pid", None):
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=grace)
        return
    except Exception:
        pass
    try:
        if os.name != "nt" and getattr(process, "pid", None):
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=grace)
    except Exception:
        pass


def _failure_status(output: str, returncode: int | None) -> PingStatus:
    lowered = output.casefold()
    dns_markers = (
        "could not find host",
        "cannot resolve",
        "unknown host",
        "name or service not known",
        "temporary failure in name resolution",
        "nao pôde encontrar o host",
        "não pôde encontrar o host",
    )
    if any(marker in lowered for marker in dns_markers):
        return PingStatus.DNS_ERROR
    if any(
        marker in lowered
        for marker in ("permission denied", "operation not permitted", "acesso negado")
    ):
        return PingStatus.PERMISSION_DENIED
    if any(
        marker in lowered
        for marker in (
            "unreachable",
            "inacessível",
            "inacessivel",
            "general failure",
            "falha geral",
            "no route to host",
        )
    ):
        return PingStatus.UNREACHABLE
    return PingStatus.TIMEOUT if returncode else PingStatus.ERROR


def probe_ping(
    target: PingTarget | str,
    *,
    generation: int = 0,
    timeout_seconds: float = 1.25,
    cancel_event: threading.Event | None = None,
) -> PingProbeResult:
    """Run one bounded, cancellable ICMP probe without invoking a shell."""

    started = time.monotonic()
    target_id = target.id if isinstance(target, PingTarget) else "custom_probe"
    raw_host = target.host if isinstance(target, PingTarget) else target
    try:
        host = validate_host(raw_host).host
        command = build_ping_command(
            host,
            timeout_seconds=min(1.0, max(0.05, timeout_seconds)),
        )
    except ValueError as exc:
        return PingProbeResult(
            target_id,
            generation,
            str(raw_host),
            PingStatus.INVALID_TARGET,
            started,
            time.monotonic(),
            detail=str(exc),
        )

    if cancel_event is not None and cancel_event.is_set():
        return PingProbeResult(
            target_id,
            generation,
            host,
            PingStatus.CANCELLED,
            started,
            time.monotonic(),
        )

    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "text": True,
        "errors": "ignore",
        "shell": False,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(command, **kwargs)
    except FileNotFoundError as exc:
        return PingProbeResult(
            target_id,
            generation,
            host,
            PingStatus.TOOL_MISSING,
            started,
            time.monotonic(),
            detail=str(exc),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return PingProbeResult(
            target_id,
            generation,
            host,
            PingStatus.ERROR,
            started,
            time.monotonic(),
            detail=str(exc),
        )

    deadline = started + max(0.05, timeout_seconds)
    status: PingStatus | None = None
    while process.poll() is None:
        if cancel_event is not None and cancel_event.is_set():
            status = PingStatus.CANCELLED
            _terminate_process(process)
            break
        if time.monotonic() >= deadline:
            status = PingStatus.TIMEOUT
            _terminate_process(process)
            break
        if cancel_event is not None:
            cancel_event.wait(0.02)
        else:
            time.sleep(0.02)

    try:
        stdout, stderr = process.communicate(timeout=0.2)
    except subprocess.TimeoutExpired:
        _terminate_process(process)
        try:
            stdout, stderr = process.communicate(timeout=0.2)
        except Exception:
            stdout, stderr = "", ""
    except Exception:
        stdout, stderr = "", ""
    output = "\n".join(part for part in (stdout, stderr) if part)
    latency = parse_ping_latency(output)
    returncode = process.returncode
    if status is None:
        if returncode == 0 and latency is not None:
            status = PingStatus.SUCCESS
        else:
            status = _failure_status(output, returncode)
    if status is not PingStatus.SUCCESS:
        latency = None
    return PingProbeResult(
        target_id=target_id,
        generation=generation,
        host=host,
        status=status,
        started_monotonic=started,
        completed_monotonic=time.monotonic(),
        latency_ms=latency,
        detail=output.strip()[-500:],
        returncode=returncode,
    )


__all__ = [
    "HostKind",
    "LEGACY_DEFAULT_HOST",
    "MAX_PERSISTENT_TARGETS",
    "NETWORK_SCHEMA_VERSION",
    "PingProbeResult",
    "PingSample",
    "PingStatus",
    "PingTarget",
    "TARGET_CATALOG",
    "TargetCategory",
    "TargetSelection",
    "ValidatedTarget",
    "build_ping_command",
    "create_custom_target",
    "parse_ping_latency",
    "probe_ping",
    "target_by_id",
    "target_catalog",
    "validate_host",
]
