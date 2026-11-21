"""Termux/Android hub tab mixin for VareduraTextualApp."""

from __future__ import annotations

from collections import deque
from contextlib import nullcontext
import datetime
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

from textual import work
from textual.app import ComposeResult, SuspendNotSupported
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.timer import Timer
from textual.widgets import (
    Button,
    Input,
    Label,
    Sparkline,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from i18n import t
from varedura import termux_env, updater

TERMUX_CSS = """
#termux .termux-scroll {
    height: 1fr;
    padding: 0 1;
}

#termux .termux-card {
    background: $panel;
    border: round $primary;
    padding: 1 2;
    margin: 0 0 1 0;
    height: auto;
}

#termux .termux-title {
    text-style: bold;
    color: $accent;
    height: auto;
    margin-bottom: 1;
}

#termux-traffic-spark,
#claro-spark {
    height: 3;
    margin: 1 0;
}

#termux-tools-grid {
    layout: grid;
    grid-size: 2;
    grid-gutter: 1;
    height: auto;
    margin-top: 1;
}

#termux-tools-grid.cols-1 {
    grid-size: 1;
}

#termux-tools-grid.cols-3 {
    grid-size: 3;
}

.termux-tool-btn {
    width: 100%;
    height: auto;
    min-height: 3;
}

.termux-svc-row {
    height: auto;
    margin-bottom: 1;
    align: left middle;
}

.termux-svc-row > Label {
    width: 1fr;
    content-align: left middle;
}

.termux-svc-badge {
    width: 10;
    content-align: center middle;
    margin-right: 1;
    text-style: bold;
}

.termux-svc-badge.svc-on {
    color: $success;
}

.termux-svc-badge.svc-off {
    color: $text-muted;
}

#termux-git-status {
    height: auto;
    margin-bottom: 1;
}

.oculto-termux {
    display: none;
}
"""


def _format_bytes(value: int) -> str:
    """Format a byte counter into a human-readable string."""
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


class TermuxMixin:
    """Native Termux Hub, Claro Suite and Services mixin."""

    def _init_termux_state(self) -> None:
        self._termux_timer: Timer | None = None
        self._termux_tools: list = []
        self._termux_tool_map: dict[str, object] = {}
        self._termux_traffic_hist: deque[float] = deque([0.0], maxlen=30)
        self._termux_claro_hist: deque[float] = deque([0.0], maxlen=30)
        self._termux_prev_bytes: tuple[int, int] | None = None
        self._termux_prev_mobile_bytes: tuple[int, int] | None = None
        self._termux_syncing_switches: bool = False
        self._termux_last_telemetry = None
        self._termux_git_busy: bool = False

    def _compose_termux(self) -> ComposeResult:
        services = termux_env.list_termux_services()
        svc_labels = {
            "sshd": t("termux.svc_sshd"),
            "claro_daemon": t("termux.svc_claro_daemon"),
            "crond": t("termux.svc_cron"),
            "wakelock": t("termux.svc_wakelock"),
        }
        cron_enabled = updater.is_cron_update_enabled()

        with TabbedContent(initial="termux-hub", id="termux-subtabs"):
            with TabPane(t("termux.subtab_hub"), id="termux-hub"):
                with VerticalScroll(classes="termux-scroll"):
                    with Vertical(classes="termux-card", id="termux-telemetry-card"):
                        yield Label(t("termux.telemetry_title"), classes="termux-title")
                        yield Label(
                            f"{t('termux.lbl_battery')}: —", id="termux-lbl-battery"
                        )
                        yield Label(f"{t('termux.lbl_wifi')}: —", id="termux-lbl-wifi")
                        yield Label(
                            f"{t('termux.lbl_mobile')}: —", id="termux-lbl-mobile"
                        )
                        yield Label(
                            f"{t('termux.lbl_memory')}: —", id="termux-lbl-memory"
                        )
                        yield Label(f"{t('termux.lbl_root')}: —", id="termux-lbl-root")
                        yield Label(
                            f"{t('termux.lbl_traffic')}: —", id="termux-lbl-traffic"
                        )
                        yield Sparkline(
                            [0.0], id="termux-traffic-spark", summary_function=max
                        )
                        with Horizontal(classes="button-row"):
                            yield Button(
                                t("termux.btn_refresh"),
                                id="termux-refresh-btn",
                                variant="primary",
                            )
                            yield Button(
                                t("termux.btn_shortcuts"), id="termux-kbd-page-btn"
                            )

                    with Vertical(classes="termux-card", id="termux-tools-card"):
                        yield Label(t("termux.tools_title"), classes="termux-title")
                        yield Input(
                            placeholder=t("termux.tools_arg_placeholder"),
                            id="termux-tool-arg",
                        )
                        yield Grid(id="termux-tools-grid")
                        yield Label(t("termux.tools_empty"), id="termux-tools-empty")

            if termux_env.has_claro_suite():
                with TabPane(t("termux.subtab_claro"), id="termux-claro"):
                    with VerticalScroll(classes="termux-scroll"):
                        with Vertical(classes="termux-card", id="termux-claro-card"):
                            yield Label(t("termux.claro_title"), classes="termux-title")
                            yield Label(
                                f"{t('termux.claro_rx')}: 0 B", id="claro-rx-lbl"
                            )
                            yield Label(
                                f"{t('termux.claro_tx')}: 0 B", id="claro-tx-lbl"
                            )
                            yield Sparkline(
                                [0.0], id="claro-spark", summary_function=max
                            )
                            with Horizontal(classes="button-row"):
                                yield Button(
                                    t("termux.btn_claro_mon"),
                                    id="termux-claro-mon",
                                    variant="primary",
                                )
                                yield Button(
                                    t("termux.btn_claro_aud"), id="termux-claro-aud"
                                )
                            with Horizontal(classes="button-row"):
                                yield Button(
                                    t("termux.btn_claro_ussd"), id="termux-claro-ussd"
                                )
                                yield Button(
                                    t("termux.btn_m35_legacy"), id="termux-m35-legacy"
                                )

            with TabPane(t("termux.subtab_services"), id="termux-services"):
                with VerticalScroll(classes="termux-scroll"):
                    with Vertical(classes="termux-card", id="termux-services-card"):
                        yield Label(t("termux.services_title"), classes="termux-title")
                        for svc in services:
                            if svc.id == "claro_daemon" and not svc.available:
                                continue
                            badge_text = (
                                t("termux.status_on")
                                if svc.active
                                else t("termux.status_off")
                            )
                            badge_cls = (
                                "termux-svc-badge svc-on"
                                if svc.active
                                else "termux-svc-badge svc-off"
                            )
                            with Horizontal(classes="termux-svc-row"):
                                yield Label(svc_labels.get(svc.id, svc.label))
                                yield Label(
                                    badge_text,
                                    id=f"badge-termux-{svc.id}",
                                    classes=badge_cls,
                                )
                                yield Switch(
                                    value=svc.active,
                                    id=f"sw-termux-{svc.id}",
                                )

                        cron_badge = (
                            t("termux.status_on")
                            if cron_enabled
                            else t("termux.status_off")
                        )
                        cron_cls = (
                            "termux-svc-badge svc-on"
                            if cron_enabled
                            else "termux-svc-badge svc-off"
                        )
                        with Horizontal(classes="termux-svc-row"):
                            yield Label(t("termux.svc_git_cron"))
                            yield Label(
                                cron_badge,
                                id="badge-termux-git-cron",
                                classes=cron_cls,
                            )
                            yield Switch(
                                value=cron_enabled,
                                id="sw-termux-git-cron",
                            )

                    with Vertical(classes="termux-card", id="termux-ssh-card"):
                        yield Label(t("termux.ssh_title"), classes="termux-title")
                        yield Label(
                            t("termux.ssh_wifi_cmd", cmd="ssh -p 8022 127.0.0.1"),
                            id="termux-ssh-wifi-lbl",
                        )
                        yield Label(
                            t(
                                "termux.ssh_adb_cmd",
                                cmd="adb forward tcp:8022 tcp:8022 && ssh -p 8022 127.0.0.1",
                            ),
                            id="termux-ssh-adb-lbl",
                        )
                        with Horizontal(classes="button-row"):
                            yield Button(
                                t("termux.btn_copy_ssh"), id="termux-copy-ssh"
                            )
                            yield Button(
                                t("termux.btn_restart_ssh"), id="termux-restart-ssh"
                            )

                    with Vertical(classes="termux-card", id="termux-git-card"):
                        yield Label(t("updater.section_title"), classes="termux-title")
                        yield Static(
                            t("updater.status_checking"), id="termux-git-status"
                        )
                        with Horizontal(classes="button-row"):
                            yield Button(
                                t("updater.btn_check_now"), id="termux-git-check"
                            )
                            yield Button(
                                t("updater.btn_update_now"),
                                id="termux-git-update",
                                variant="primary",
                            )

    def _termux_on_mount(self) -> None:
        self._refresh_termux_tools()
        self._termux_on_resize(self.size.width)
        self._refresh_termux_all_async()
        if self._termux_timer is None:
            self._termux_timer = self.set_interval(2.5, self._termux_timer_tick)

    def _termux_on_unmount(self) -> None:
        if self._termux_timer is not None:
            self._termux_timer.stop()
            self._termux_timer = None

    def _termux_timer_tick(self) -> None:
        if getattr(self, "_active_tab", "") == "termux":
            self._refresh_termux_telemetry_async()

    def _termux_on_resize(self, width: int) -> None:
        try:
            grid = self.query_one("#termux-tools-grid", Grid)
        except Exception:
            return
        grid.set_class(width < 68, "cols-1")
        grid.set_class(width >= 112, "cols-3")

    def _refresh_termux_tools(self) -> None:
        tools = termux_env.discover_termux_tools()
        self._termux_tools = tools
        self._termux_tool_map = {}
        try:
            grid = self.query_one("#termux-tools-grid", Grid)
            empty_lbl = self.query_one("#termux-tools-empty", Label)
        except Exception:
            return
        grid.remove_children()
        if not tools:
            empty_lbl.remove_class("oculto-termux")
            return
        empty_lbl.add_class("oculto-termux")
        buttons: list[Button] = []
        used_ids: set[str] = set()
        for tool in tools:
            safe = re.sub(r"[^a-zA-Z0-9_-]", "-", tool.id).strip("-") or "tool"
            btn_id = f"termux-tool-{safe}"
            if btn_id in used_ids:
                btn_id = f"{btn_id}-{len(used_ids)}"
            used_ids.add(btn_id)
            self._termux_tool_map[btn_id] = tool
            buttons.append(Button(tool.label, id=btn_id, classes="termux-tool-btn"))
        grid.mount(*buttons)

    @work(thread=True, exclusive=False)
    def _refresh_termux_all_async(self) -> None:
        telemetry = termux_env.collect_android_telemetry()
        services = termux_env.list_termux_services()
        cron_enabled = updater.is_cron_update_enabled()
        repo_status = updater.get_repo_status()
        self.call_from_thread(
            self._apply_termux_refresh,
            telemetry,
            services,
            cron_enabled,
            repo_status,
        )

    @work(thread=True, exclusive=False)
    def _refresh_termux_telemetry_async(self) -> None:
        telemetry = termux_env.collect_android_telemetry()
        self.call_from_thread(self._apply_termux_telemetry, telemetry)

    def _apply_termux_refresh(
        self,
        telemetry,
        services: list,
        cron_enabled: bool,
        repo_status: dict,
    ) -> None:
        self._apply_termux_telemetry(telemetry)
        self._apply_termux_services(services, cron_enabled)
        self._apply_termux_git_status(repo_status)

    def _apply_termux_telemetry(self, telemetry) -> None:
        self._termux_last_telemetry = telemetry
        if "termux" not in getattr(self, "_hydrated_tabs", set()):
            return
        pct = telemetry.battery_pct
        batt_parts = [f"{pct}%" if pct is not None else "—"]
        if telemetry.battery_status:
            batt_parts.append(telemetry.battery_status)
        if telemetry.battery_temp_c is not None:
            batt_parts.append(f"{telemetry.battery_temp_c:.1f}°C")
        batt_txt = " · ".join(batt_parts)
        wifi_txt = telemetry.wifi_ip or "—"
        mobile_txt = telemetry.mobile_ip or "—"
        mem_txt = (
            f"{telemetry.mem_used_mb:.0f} / {telemetry.mem_total_mb:.0f} MB"
            if telemetry.mem_total_mb > 0
            else "—"
        )
        if telemetry.uptime_str:
            mem_txt = f"{mem_txt} · up {telemetry.uptime_str}"
        root_txt = t("termux.status_on") if telemetry.has_root else t("termux.status_off")
        traffic_txt = (
            f"↓ {_format_bytes(telemetry.rx_bytes)}   ↑ {_format_bytes(telemetry.tx_bytes)}"
        )

        if self._termux_prev_bytes is None:
            delta_kb = 0.0
        else:
            prev_rx, prev_tx = self._termux_prev_bytes
            delta_kb = max(
                0,
                (telemetry.rx_bytes - prev_rx) + (telemetry.tx_bytes - prev_tx),
            ) / 1024.0
        self._termux_prev_bytes = (telemetry.rx_bytes, telemetry.tx_bytes)
        self._termux_traffic_hist.append(delta_kb)

        updates = {
            "#termux-lbl-battery": f"{t('termux.lbl_battery')}: {batt_txt}",
            "#termux-lbl-wifi": f"{t('termux.lbl_wifi')}: {wifi_txt}",
            "#termux-lbl-mobile": f"{t('termux.lbl_mobile')}: {mobile_txt}",
            "#termux-lbl-memory": f"{t('termux.lbl_memory')}: {mem_txt}",
            "#termux-lbl-root": f"{t('termux.lbl_root')}: {root_txt}",
            "#termux-lbl-traffic": f"{t('termux.lbl_traffic')}: {traffic_txt}",
        }
        for selector, text in updates.items():
            try:
                self.query_one(selector, Label).update(text)
            except Exception:
                pass
        try:
            self.query_one("#termux-traffic-spark", Sparkline).data = list(
                self._termux_traffic_hist
            ) or [0.0]
        except Exception:
            pass

        user = telemetry.user or "u0_a"
        ssh_host = telemetry.wifi_ip or "PHONE_IP"
        try:
            self.query_one("#termux-ssh-wifi-lbl", Label).update(
                t("termux.ssh_wifi_cmd", cmd=f"ssh -p 8022 {user}@{ssh_host}")
            )
        except Exception:
            pass

        # Claro rmnet* telemetry
        if self._termux_prev_mobile_bytes is None:
            mob_delta_kb = 0.0
        else:
            prev_mrx, prev_mtx = self._termux_prev_mobile_bytes
            mob_delta_kb = max(
                0,
                (telemetry.mobile_rx_bytes - prev_mrx)
                + (telemetry.mobile_tx_bytes - prev_mtx),
            ) / 1024.0
        self._termux_prev_mobile_bytes = (
            telemetry.mobile_rx_bytes,
            telemetry.mobile_tx_bytes,
        )
        self._termux_claro_hist.append(mob_delta_kb)
        try:
            self.query_one("#claro-rx-lbl", Label).update(
                f"{t('termux.claro_rx')}: {_format_bytes(telemetry.mobile_rx_bytes)}"
            )
            self.query_one("#claro-tx-lbl", Label).update(
                f"{t('termux.claro_tx')}: {_format_bytes(telemetry.mobile_tx_bytes)}"
            )
            self.query_one("#claro-spark", Sparkline).data = list(
                self._termux_claro_hist
            ) or [0.0]
        except Exception:
            pass

    def _apply_termux_services(self, services: list, cron_enabled: bool) -> None:
        self._termux_syncing_switches = True
        try:
            for svc in services:
                try:
                    sw = self.query_one(f"#sw-termux-{svc.id}", Switch)
                    sw.value = svc.active
                    badge = self.query_one(f"#badge-termux-{svc.id}", Label)
                    badge.update(
                        t("termux.status_on") if svc.active else t("termux.status_off")
                    )
                    badge.set_class(svc.active, "svc-on")
                    badge.set_class(not svc.active, "svc-off")
                except Exception:
                    pass
            try:
                cron_sw = self.query_one("#sw-termux-git-cron", Switch)
                cron_sw.value = cron_enabled
                cron_badge = self.query_one("#badge-termux-git-cron", Label)
                cron_badge.update(
                    t("termux.status_on") if cron_enabled else t("termux.status_off")
                )
                cron_badge.set_class(cron_enabled, "svc-on")
                cron_badge.set_class(not cron_enabled, "svc-off")
            except Exception:
                pass
        finally:
            self._termux_syncing_switches = False

    def _apply_termux_git_status(self, status: dict) -> None:
        branch = status.get("branch") or "—"
        commit = status.get("commit") or "—"
        dirty = " *" if status.get("dirty") else ""
        token_source = status.get("token_source") or "none"
        token_text = (
            t("updater.token_configured", source=token_source)
            if token_source != "none"
            else t("updater.token_missing")
        )
        last_ts = status.get("last_check")
        last_str = (
            datetime.datetime.fromtimestamp(float(last_ts)).strftime("%Y-%m-%d %H:%M")
            if last_ts
            else "—"
        )
        summary = (
            f"{t('updater.branch_label')}: {branch} ({commit}{dirty})\n"
            f"{t('updater.token_status_label')}: {token_text}\n"
            f"{t('updater.last_check_label')}: {last_str}"
        )
        try:
            self.query_one("#termux-git-status", Static).update(summary)
        except Exception:
            pass

    def _run_suspended_command(self, cmd: list[str], *, pause: bool = False) -> int:
        """Run an interactive CLI command while Textual yields the terminal."""
        try:
            ctx = self.suspend()
            suspended = True
        except Exception:
            ctx = nullcontext()
            suspended = False

        try:
            with ctx:
                proc = subprocess.run(cmd)
                if pause and suspended:
                    try:
                        input(t("menu.press_enter_short"))
                    except EOFError:
                        pass
                return proc.returncode
        except SuspendNotSupported:
            proc = subprocess.run(cmd, stdin=subprocess.DEVNULL)
            return proc.returncode

    def _launch_termux_tool(self, tool) -> None:
        arg_text = ""
        try:
            arg_input = self.query_one("#termux-tool-arg", Input)
            arg_text = arg_input.value.strip()
        except Exception:
            arg_input = None

        if getattr(tool, "needs_arg", False) and not arg_text:
            self.notify(
                t("termux.arg_required", label=tool.label), severity="warning"
            )
            if arg_input is not None:
                arg_input.focus()
            return

        cmd = list(tool.command)
        if arg_text:
            try:
                cmd.extend(shlex.split(arg_text))
            except ValueError:
                cmd.append(arg_text)

        self.notify(t("termux.launching", label=tool.label))
        if tool.mode == "background":
            try:
                subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except OSError as exc:
                self.notify(str(exc), severity="error")
            return

        pause = tool.mode == "suspend_pause"
        try:
            rc = self._run_suspended_command(cmd, pause=pause)
            self.notify(t("termux.returned", label=tool.label, code=rc))
        except OSError as exc:
            self.notify(str(exc), severity="error")

    def _launch_claro_command(
        self, binary_name: str, script_name: str, *, label: str, pause: bool = False
    ) -> None:
        exe = shutil.which(binary_name)
        if exe:
            cmd = [exe]
        else:
            script = Path.home() / ".claro_suite" / script_name
            cmd = [sys.executable, str(script)]
        self.notify(t("termux.launching", label=label))
        try:
            rc = self._run_suspended_command(cmd, pause=pause)
            self.notify(t("termux.returned", label=label, code=rc))
        except OSError as exc:
            self.notify(str(exc), severity="error")

    @work(thread=True, exclusive=False)
    def _run_claro_ussd_worker(self) -> None:
        try:
            proc = subprocess.run(
                ["cmd", "phone", "ussd", "*1052#"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=15,
            )
            if proc.returncode == 0:
                self.call_from_thread(self.notify, t("termux.claro_ussd_sent"))
            else:
                detail = (proc.stderr or proc.stdout or "USSD failed").strip()
                self.call_from_thread(self.notify, detail, severity="warning")
        except (OSError, subprocess.SubprocessError) as exc:
            self.call_from_thread(self.notify, str(exc), severity="error")

    @work(thread=True, exclusive=False)
    def _toggle_termux_service_worker(self, service_id: str, enable: bool) -> None:
        ok, msg = termux_env.toggle_termux_service(service_id, enable)
        services = termux_env.list_termux_services()
        cron_enabled = updater.is_cron_update_enabled()
        self.call_from_thread(
            self._finish_service_toggle, services, cron_enabled, ok, msg
        )

    @work(thread=True, exclusive=False)
    def _toggle_git_cron_worker(self, enable: bool) -> None:
        ok, msg = updater.set_cron_update_enabled(enable)
        services = termux_env.list_termux_services()
        cron_enabled = updater.is_cron_update_enabled()
        self.call_from_thread(
            self._finish_service_toggle, services, cron_enabled, ok, msg
        )

    @work(thread=True, exclusive=False)
    def _restart_sshd_worker(self) -> None:
        termux_env.toggle_termux_service("sshd", False)
        ok, msg = termux_env.toggle_termux_service("sshd", True)
        services = termux_env.list_termux_services()
        cron_enabled = updater.is_cron_update_enabled()
        self.call_from_thread(
            self._finish_service_toggle,
            services,
            cron_enabled,
            ok,
            t("termux.ssh_restarted") if ok else msg,
        )

    def _finish_service_toggle(
        self, services: list, cron_enabled: bool, ok: bool, msg: str
    ) -> None:
        self._apply_termux_services(services, cron_enabled)
        self.notify(msg, severity="information" if ok else "warning")

    def _copy_ssh_command(self) -> None:
        telemetry = self._termux_last_telemetry
        user = getattr(telemetry, "user", "") or "u0_a"
        wifi_ip = getattr(telemetry, "wifi_ip", "") or "127.0.0.1"
        cmd = f"ssh -p 8022 {user}@{wifi_ip}"
        copied = termux_env.copy_to_clipboard(cmd)
        if not copied and hasattr(self, "copy_to_clipboard"):
            try:
                self.copy_to_clipboard(cmd)
                copied = True
            except Exception:
                copied = False
        if copied:
            self.notify(t("termux.ssh_copied"))
        else:
            self.notify(cmd)

    @work(thread=True, exclusive=False)
    def _run_termux_git_worker(self, *, check_only: bool) -> None:
        result = updater.update_repository(check_only=check_only, force=True)
        status = updater.get_repo_status()
        self.call_from_thread(self._finish_termux_git, result, status)

    def _finish_termux_git(self, result, repo_status: dict) -> None:
        self._termux_git_busy = False
        self._apply_termux_git_status(repo_status)
        if result.status == "up_to_date":
            self.notify(t("updater.status_up_to_date"))
        elif result.status == "update_available":
            self.notify(t("updater.status_available", count=result.commits_behind))
        elif result.status == "updated":
            self.notify(t("updater.status_updated", count=result.commits_pulled))
        elif result.status == "dirty":
            self.notify(t("updater.status_dirty"), severity="warning")
        elif result.status == "cooldown":
            self.notify(t("updater.status_cooldown"))
        else:
            self.notify(
                t("updater.status_error", error=result.message or "error"),
                severity="error",
            )

    def _termux_handle_switch(self, switch_id: str, value: bool) -> bool:
        if getattr(self, "_termux_syncing_switches", False):
            return switch_id.startswith("sw-termux-")
        if switch_id == "sw-termux-git-cron":
            self._toggle_git_cron_worker(value)
            return True
        if switch_id.startswith("sw-termux-"):
            service_id = switch_id[len("sw-termux-") :]
            self._toggle_termux_service_worker(service_id, value)
            return True
        return False

    def _termux_handle_button(self, button_id: str) -> bool:
        if button_id == "termux-refresh-btn":
            self._refresh_termux_tools()
            self._refresh_termux_all_async()
            return True
        if button_id == "termux-kbd-page-btn":
            if hasattr(self, "action_toggle_keyboard_page"):
                self.action_toggle_keyboard_page()
            return True
        if button_id in getattr(self, "_termux_tool_map", {}):
            self._launch_termux_tool(self._termux_tool_map[button_id])
            return True
        if button_id == "termux-claro-mon":
            self._launch_claro_command(
                "claro-monitor",
                "claro_monitor.py",
                label=t("termux.btn_claro_mon"),
                pause=False,
            )
            return True
        if button_id == "termux-claro-aud":
            self._launch_claro_command(
                "claro-audit",
                "claro_audit.py",
                label=t("termux.btn_claro_aud"),
                pause=True,
            )
            return True
        if button_id == "termux-claro-ussd":
            self._run_claro_ussd_worker()
            return True
        if button_id == "termux-m35-legacy":
            self._launch_claro_command(
                "m35-center",
                "m35_tui.py",
                label=t("termux.btn_m35_legacy"),
                pause=False,
            )
            return True
        if button_id == "termux-copy-ssh":
            self._copy_ssh_command()
            return True
        if button_id == "termux-restart-ssh":
            self._restart_sshd_worker()
            return True
        if button_id == "termux-git-check":
            self.notify(t("updater.status_checking"))
            self._run_termux_git_worker(check_only=True)
            return True
        if button_id == "termux-git-update":
            self.notify(t("updater.status_checking"))
            self._run_termux_git_worker(check_only=False)
            return True
        return False
