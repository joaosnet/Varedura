"""Perfis de plano na TUI: formulário em Configurações e plano ativo por rede.

Mixin leve — só importa ``monitor.plan_profiles`` (dados puros).  Detecção de
rede, contadores de franquia e histórico de velocidade são carregados sob
demanda, depois do primeiro frame.
"""

from __future__ import annotations

import datetime

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Input, Label, Select

from i18n import t
from monitor.plan_profiles import (
    ActiveNetwork,
    NetworkKind,
    PlanKind,
    PlanProfile,
    bind_to_network,
    describe_binding,
    find_profile,
    new_profile_id,
    profiles_from_prefs,
    profiles_to_prefs,
    quota_status,
    select_profile,
)
from varedura import termux_env

_NEW_PLAN = "__new__"
_AUTO = "__auto__"

PLANS_CSS = """
#plan-binding { color: $text-muted; height: auto; padding: 0 1; }
#network-plan-status { color: $text-muted; width: 100%; height: auto; padding: 0 1; margin-bottom: 1; }
"""


def _fmt_number(value: float) -> str:
    return f"{value:g}"


def _fmt_speed(value: float) -> str:
    return f"{value:g}" if value > 0 else "—"


class PlansMixin:
    """Formulário de planos, seleção automática e acompanhamento de franquia."""

    def _init_plans_state(self) -> None:
        self._active_network: ActiveNetwork | None = None
        self._active_profile: PlanProfile | None = None
        self._active_profile_reason = ""
        self._plan_form_id = ""
        self._plan_form_binding: PlanProfile | None = None
        self._mobile_usage_bytes: int | None = None

    # -- dados ---------------------------------------------------------------
    def _plan_profiles(self) -> list[PlanProfile]:
        return profiles_from_prefs(self._network_config.get("plan_profiles"))

    def _manual_profile_id(self) -> str:
        return str(self._network_config.get("active_profile_id", "") or "")

    def _mobile_profile(self) -> PlanProfile | None:
        """Perfil que recebe o consumo de dados móveis do aparelho."""
        profile, _reason = select_profile(
            [p for p in self._plan_profiles() if p.kind is PlanKind.MOBILE],
            ActiveNetwork(NetworkKind.MOBILE),
        )
        return profile

    # -- plano ativo ---------------------------------------------------------
    def _refresh_active_plan(self) -> None:
        """Recalcula o plano aplicável e o propaga para teste e relatório."""
        profile, reason = select_profile(
            self._plan_profiles(), self._active_network, self._manual_profile_id()
        )
        self._active_profile, self._active_profile_reason = profile, reason
        try:
            from monitor.plan_profiles import apply_profile

            apply_profile(profile, self._active_network)
        except Exception:
            pass
        self._update_plan_status_label()

    @work(thread=True, exclusive=True, group="plan-network")
    def _detect_active_network_bg(self) -> None:
        from monitor.netinfo import detect_active_network

        network = detect_active_network()
        self.call_from_thread(self._on_active_network, network)

    def _on_active_network(self, network: ActiveNetwork) -> None:
        changed = network != self._active_network
        self._active_network = network
        if changed or self._active_profile is None:
            self._refresh_active_plan()

    def _poll_plan_usage(self) -> None:
        """Chamado pelo poller (thread): acumula o consumo de dados móveis."""
        raw = termux_env.read_mobile_data_bytes() if termux_env.is_android() else None
        if raw is None:
            return
        profile = self._mobile_profile()
        if profile is None or not profile.has_quota:
            return
        from monitor.data_usage import get_usage_tracker

        self._mobile_usage_bytes = get_usage_tracker().update(profile, raw)

    def _record_speed_result(self, result) -> None:
        """Persiste a medição com o plano e a rede em que ela foi feita."""
        try:
            from monitor.data_usage import record_speed_sample
            from monitor.plan_profiles import SpeedSample

            network = self._active_network
            record_speed_sample(
                SpeedSample(
                    timestamp=getattr(result, "timestamp", None)
                    or datetime.datetime.now(),
                    down_mbps=float(result.download_mbps),
                    up_mbps=float(result.upload_mbps),
                    ping_ms=float(getattr(result, "ping_ms", 0.0) or 0.0),
                    provider=str(getattr(result, "provider_name", "") or ""),
                    server=str(getattr(result, "servidor", "") or ""),
                    profile_id=self._active_profile.id if self._active_profile else "",
                    network_kind=network.kind.value if network else "",
                )
            )
        except Exception:
            pass

    def _plan_status_text(self, *, prefix: bool = True) -> str:
        profile = self._active_profile
        network = self._active_network
        net_txt = network.describe() if network is not None else ""
        if profile is None:
            base = t("plans.status_none")
            return f"{base} · {net_txt}" if net_txt else base
        parts = [t("plans.status_plan", name=profile.name) if prefix else profile.name]
        if profile.has_speed_reference:
            parts.append(
                t(
                    "plans.status_speed",
                    down=_fmt_speed(profile.down_mbps),
                    up=_fmt_speed(profile.up_mbps),
                )
            )
        if profile.has_quota:
            parts.append(self._quota_text(profile))
        if net_txt:
            parts.append(net_txt)
        if self._active_profile_reason == "manual":
            parts.append(t("plans.status_manual"))
        return " · ".join(parts)

    def _quota_text(self, profile: PlanProfile) -> str:
        measured = self._mobile_usage_bytes
        if measured is None:
            try:
                from monitor.data_usage import get_usage_tracker

                measured = get_usage_tracker().cycle_bytes(profile)
            except Exception:
                measured = 0
        status = quota_status(profile, measured)
        return t(
            "plans.status_quota",
            used=f"{status.used_gb:.2f}",
            total=_fmt_number(status.quota_gb),
            pct=f"{status.used_pct:.0f}",
            days=status.days_left,
        )

    def _update_plan_status_label(self) -> None:
        try:
            self.query_one("#network-plan-status", Label).update(self._plan_status_text())
        except Exception:
            pass

    # -- formulário ----------------------------------------------------------
    def _plan_select_options(self) -> list[tuple[str, str]]:
        options = [(profile.name, profile.id) for profile in self._plan_profiles()]
        options.append((t("plans.new_option"), _NEW_PLAN))
        return options

    def _plan_active_options(self) -> list[tuple[str, str]]:
        return [(t("plans.active_auto"), _AUTO)] + [
            (profile.name, profile.id) for profile in self._plan_profiles()
        ]

    def _compose_plan_settings(self) -> ComposeResult:
        profiles = self._plan_profiles()
        current = find_profile(profiles, self._plan_form_id) or (
            profiles[0] if profiles else None
        )
        self._plan_form_id = current.id if current else ""
        self._plan_form_binding = current
        kind_options = [
            (t("plans.kind_fixed"), PlanKind.FIXED.value),
            (t("plans.kind_mobile"), PlanKind.MOBILE.value),
        ]
        yield Label(t("plans.section_title"), classes="section-title")
        with Horizontal(classes="form-row"):
            yield Label(t("plans.active_label"))
            yield Select(
                self._plan_active_options(),
                value=self._manual_profile_id() or _AUTO,
                allow_blank=False,
                id="plan-active-select",
            )
        with Horizontal(classes="form-row"):
            yield Label(t("plans.select_label"))
            yield Select(
                self._plan_select_options(),
                value=current.id if current else _NEW_PLAN,
                allow_blank=False,
                id="plan-select",
            )
        with Horizontal(classes="form-row"):
            yield Label(t("plans.name"))
            yield Input(value=current.name if current else "", id="plan-name")
        with Horizontal(classes="form-row"):
            yield Label(t("plans.kind"))
            yield Select(
                kind_options,
                value=(current.kind if current else PlanKind.FIXED).value,
                allow_blank=False,
                id="plan-kind",
            )
        with Horizontal(classes="form-row"):
            yield Label(t("plans.operadora"))
            yield Input(value=current.operadora if current else "", id="plan-operadora")
        with Horizontal(classes="form-row"):
            yield Label(t("plans.plano"))
            yield Input(value=current.plano if current else "", id="plan-plano")
        with Horizontal(classes="form-row"):
            yield Label(t("settings.net_contracted_down"))
            yield Input(
                value=_fmt_number(current.down_mbps) if current else "",
                placeholder="0",
                id="net-down",
                type="number",
            )
        with Horizontal(classes="form-row"):
            yield Label(t("settings.net_contracted_up"))
            yield Input(
                value=_fmt_number(current.up_mbps) if current else "",
                placeholder="0",
                id="net-up",
                type="number",
            )
        with Horizontal(classes="form-row"):
            yield Label(t("plans.quota"))
            yield Input(
                value=_fmt_number(current.quota_gb) if current else "",
                placeholder="0",
                id="plan-quota",
                type="number",
            )
        with Horizontal(classes="form-row"):
            yield Label(t("plans.cycle_start"))
            yield Input(
                value=current.cycle_start if current else "",
                placeholder="AAAA-MM-DD",
                id="plan-cycle-start",
            )
        with Horizontal(classes="form-row"):
            yield Label(t("plans.cycle_days"))
            yield Input(
                value=str(current.cycle_days) if current else "30",
                id="plan-cycle-days",
                type="integer",
            )
        with Horizontal(classes="form-row"):
            yield Label(t("plans.used_offset"))
            yield Input(
                value=_fmt_number(current.used_offset_gb) if current else "",
                placeholder="0",
                id="plan-used-offset",
                type="number",
            )
        yield Label(self._plan_binding_text(current), id="plan-binding")
        with Horizontal(classes="button-row"):
            yield Button(t("plans.btn_bind"), id="plan-bind")
            yield Button(t("plans.btn_unbind"), id="plan-unbind")
            yield Button(t("plans.btn_delete"), id="plan-delete", variant="error")

    def _plan_binding_text(self, profile: PlanProfile | None) -> str:
        binding = describe_binding(profile) if profile else ""
        return t("plans.binding_label", binding=binding or t("plans.binding_none"))

    def _plan_fill_form(self, profile: PlanProfile | None) -> None:
        self._plan_form_id = profile.id if profile else ""
        self._plan_form_binding = profile
        values = {
            "#plan-name": profile.name if profile else "",
            "#plan-operadora": profile.operadora if profile else "",
            "#plan-plano": profile.plano if profile else "",
            "#net-down": _fmt_number(profile.down_mbps) if profile else "",
            "#net-up": _fmt_number(profile.up_mbps) if profile else "",
            "#plan-quota": _fmt_number(profile.quota_gb) if profile else "",
            "#plan-cycle-start": profile.cycle_start if profile else "",
            "#plan-cycle-days": str(profile.cycle_days) if profile else "30",
            "#plan-used-offset": _fmt_number(profile.used_offset_gb) if profile else "",
        }
        try:
            for selector, value in values.items():
                self.query_one(selector, Input).value = value
            self.query_one("#plan-kind", Select).value = (
                profile.kind if profile else PlanKind.FIXED
            ).value
            self.query_one("#plan-binding", Label).update(
                self._plan_binding_text(profile)
            )
        except Exception:
            pass

    def _plan_reload_selects(self) -> None:
        try:
            select = self.query_one("#plan-select", Select)
            with select.prevent(Select.Changed):
                select.set_options(self._plan_select_options())
                select.value = self._plan_form_id or _NEW_PLAN
            active = self.query_one("#plan-active-select", Select)
            with active.prevent(Select.Changed):
                active.set_options(self._plan_active_options())
                active.value = self._manual_profile_id() or _AUTO
        except Exception:
            pass

    def _plan_read_form(self) -> PlanProfile | None:
        """Lê o formulário; ``None`` = nada a salvar. Levanta ValueError se inválido."""

        def text(selector: str) -> str:
            return self.query_one(selector, Input).value.strip()

        def number(selector: str) -> float:
            raw = text(selector).replace(",", ".")
            value = float(raw) if raw else 0.0
            if value < 0:
                raise ValueError(selector)
            return value

        down, up = number("#net-down"), number("#net-up")
        quota, offset = number("#plan-quota"), number("#plan-used-offset")
        name = text("#plan-name")
        if not self._plan_form_id and not name and not (down or up or quota):
            return None
        cycle_start = text("#plan-cycle-start")
        if cycle_start:
            cycle_start = datetime.date.fromisoformat(cycle_start).isoformat()
        cycle_days = int(text("#plan-cycle-days") or 30)
        if not 1 <= cycle_days <= 366:
            raise ValueError("cycle_days")
        kind_value = self.query_one("#plan-kind", Select).value
        kind = PlanKind(kind_value) if isinstance(kind_value, str) else PlanKind.FIXED
        if not name:
            name = t(
                "plans.default_mobile_name"
                if kind is PlanKind.MOBILE
                else "plans.default_fixed_name"
            )
        if quota and not cycle_start:
            cycle_start = datetime.date.today().isoformat()
        base = self._plan_form_binding
        data = base.to_dict() if base is not None else {}
        data.update(
            id=self._plan_form_id or new_profile_id(name),
            name=name,
            kind=kind.value,
            operadora=text("#plan-operadora"),
            plano=text("#plan-plano"),
            down_mbps=down,
            up_mbps=up,
            quota_gb=quota,
            cycle_start=cycle_start,
            cycle_days=cycle_days,
            used_offset_gb=offset,
        )
        if base is None and kind is PlanKind.MOBILE:
            data["match_kind"] = NetworkKind.MOBILE.value
        profile = PlanProfile.from_dict(data)
        if profile is None:
            raise ValueError("name")
        return profile

    def _plans_collect_into(self, cfg: dict) -> bool:
        """Grava o formulário em ``cfg``. Devolve False (e notifica) se inválido."""
        try:
            self.query_one("#plan-select", Select)
        except Exception:
            return True  # aba Configurações ainda não montada
        try:
            profile = self._plan_read_form()
        except ValueError:
            self.notify(t("plans.invalid"), severity="error")
            return False
        profiles = profiles_from_prefs(cfg.get("plan_profiles"))
        if profile is not None:
            previous = find_profile(profiles, profile.id)
            if previous is None:
                profiles.append(profile)
            else:
                profiles[profiles.index(previous)] = profile
                if previous.cycle_start != profile.cycle_start:
                    try:
                        from monitor.data_usage import get_usage_tracker

                        get_usage_tracker().reset(profile)
                    except Exception:
                        pass
            self._plan_form_id = profile.id
            self._plan_form_binding = profile
        cfg["plan_profiles"] = profiles_to_prefs(profiles)
        active = self.query_one("#plan-active-select", Select).value
        cfg["active_profile_id"] = (
            active
            if isinstance(active, str) and find_profile(profiles, active) is not None
            else ""
        )
        # Compatibilidade: ``contracted_*`` espelham o perfil fixo principal.
        fixed = next((p for p in profiles if p.kind is PlanKind.FIXED), None)
        if fixed is not None:
            cfg["contracted_down"] = fixed.down_mbps
            cfg["contracted_up"] = fixed.up_mbps
        return True

    def _plans_after_save(self) -> None:
        self._plan_reload_selects()
        self._plan_fill_form(find_profile(self._plan_profiles(), self._plan_form_id))
        self._refresh_active_plan()

    # -- eventos -------------------------------------------------------------
    # Mixins comuns não registram ``@on``: usamos o handler por nome (despachado
    # por classe no MRO) e o roteamento de botões do app.
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "plan-select":
            return
        value = event.value if isinstance(event.value, str) else _NEW_PLAN
        profile = None if value == _NEW_PLAN else find_profile(self._plan_profiles(), value)
        self._plan_fill_form(profile)

    def _plans_handle_button(self, button_id: str | None) -> bool:
        handler = {
            "plan-bind": self._on_plan_bind,
            "plan-unbind": self._on_plan_unbind,
            "plan-delete": self._on_plan_delete,
        }.get(button_id or "")
        if handler is None:
            return False
        handler()
        return True

    def _on_plan_bind(self) -> None:
        network = self._active_network
        if network is None or network.kind is NetworkKind.UNKNOWN:
            self.notify(t("plans.bind_unknown"), severity="warning")
            self._detect_active_network_bg()
            return
        base = self._plan_form_binding or PlanProfile(id="", name="-")
        self._plan_form_binding = bind_to_network(base, network)
        self.query_one("#plan-binding", Label).update(
            self._plan_binding_text(self._plan_form_binding)
        )
        self.notify(t("plans.bound_pending", network=network.describe()))

    def _on_plan_unbind(self) -> None:
        base = self._plan_form_binding
        if base is None:
            return
        data = base.to_dict()
        data.update(match_kind="", match_ssid="", match_gateway="")
        self._plan_form_binding = PlanProfile.from_dict(data) or base
        self.query_one("#plan-binding", Label).update(
            self._plan_binding_text(self._plan_form_binding)
        )

    def _on_plan_delete(self) -> None:
        if not self._plan_form_id:
            self._plan_fill_form(None)
            return
        from cli.ui_shared import save_network_config

        cfg = dict(self._network_config)
        profiles = [p for p in self._plan_profiles() if p.id != self._plan_form_id]
        cfg["plan_profiles"] = profiles_to_prefs(profiles)
        if cfg.get("active_profile_id") == self._plan_form_id:
            cfg["active_profile_id"] = ""
        save_network_config(cfg)
        self._network_config = cfg
        self._plan_form_id = profiles[0].id if profiles else ""
        self._plans_after_save()
        self.notify(t("plans.deleted"))
