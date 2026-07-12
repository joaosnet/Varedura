"""Lazy Textual screens for network target selection and safe repairs."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, SelectionList, Static

from i18n import t
from monitor.ping_targets import (
    MAX_PERSISTENT_TARGETS,
    PingTarget,
    TargetCategory,
    TargetSelection,
    create_custom_target,
    target_catalog,
)


def merge_visible_selection(
    current: set[str], visible: set[str], selected_visible: set[str]
) -> set[str]:
    """Apply filtered-list changes without dropping hidden selections."""
    return (current - visible) | selected_visible


class TargetPickerScreen(ModalScreen[dict | None]):
    """Select one to five persistent targets and exactly one primary."""

    CSS = """
    TargetPickerScreen {
        align: center middle;
    }
    #target-picker {
        width: 86;
        max-width: 95%;
        height: 90%;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #target-search, #target-custom {
        margin-bottom: 1;
    }
    #target-list {
        height: 1fr;
        border: solid $surface-lighten-2;
        margin-bottom: 1;
    }
    #target-primary-row, #target-custom-row, #target-actions {
        height: auto;
        margin-bottom: 1;
    }
    #target-primary-row Label, #target-custom-row Label {
        width: 18;
        content-align: left middle;
    }
    #target-primary, #target-custom {
        width: 1fr;
    }
    #target-custom-add, #target-actions Button {
        width: auto;
        margin-left: 1;
    }
    #target-message {
        height: auto;
        min-height: 2;
        color: $text-muted;
    }
    """

    def __init__(self, config: dict, *, onboarding: bool = False) -> None:
        super().__init__()
        self._config = dict(config)
        self._selection = TargetSelection.from_config(config)
        self._onboarding = onboarding
        self._targets: dict[str, PingTarget] = {
            target.id: target for target in target_catalog()
        }
        for target in self._selection.targets:
            self._targets[target.id] = target
        self._selected = set(self._selection.selected_target_ids)
        self._primary = self._selection.primary_target_id
        self._rebuilding = False

    @staticmethod
    def _option_label(target: PingTarget) -> str:
        category = {
            TargetCategory.INFRASTRUCTURE: t("network.category_infrastructure"),
            TargetCategory.WEB: t("network.category_web"),
            TargetCategory.GAME: t("network.category_game"),
            TargetCategory.CUSTOM: t("network.category_custom"),
        }.get(target.category, str(target.category))
        suffix = f" — {target.warning}" if target.warning else ""
        return f"[{category}] {target.label}  •  {target.host}{suffix}"

    def compose(self) -> ComposeResult:
        with Vertical(id="target-picker"):
            yield Label(
                t("network.onboarding_title")
                if self._onboarding
                else t("network.targets_title"),
                classes="section-title",
            )
            yield Static(t("network.targets_help"))
            yield Input(placeholder=t("network.targets_search"), id="target-search")
            yield SelectionList[str](
                *[
                    (self._option_label(target), target.id, target.id in self._selected)
                    for target in self._targets.values()
                ],
                id="target-list",
            )
            with Horizontal(id="target-primary-row"):
                yield Label(t("network.primary_target"))
                yield Select(
                    self._primary_options(),
                    value=self._primary
                    if self._primary in self._selected
                    else Select.NULL,
                    prompt=t("network.primary_target_prompt"),
                    id="target-primary",
                )
            with Horizontal(id="target-custom-row"):
                yield Label(t("network.custom_target"))
                yield Input(placeholder="1.1.1.1 ou host.exemplo", id="target-custom")
                yield Button(t("network.add_target"), id="target-custom-add")
            yield Static("", id="target-message")
            with Horizontal(id="target-actions"):
                yield Button(
                    t("network.targets_save"), id="target-save", variant="primary"
                )
                yield Button(
                    t("network.targets_later")
                    if self._onboarding
                    else t("network.targets_cancel"),
                    id="target-cancel",
                )

    def _primary_options(self) -> list[tuple[str, str]]:
        return [
            (self._targets[target_id].label, target_id)
            for target_id in self._targets
            if target_id in self._selected
        ]

    def _set_message(self, message: str, *, error: bool = False) -> None:
        widget = self.query_one("#target-message", Static)
        widget.update(message)
        widget.set_class(error, "ping-bad")

    def _refresh_primary(self) -> None:
        select = self.query_one("#target-primary", Select)
        select.set_options(self._primary_options())
        if self._primary not in self._selected:
            self._primary = next(iter(self._selected), None)
        select.value = self._primary if self._primary is not None else Select.NULL

    def _rebuild_list(self, query: str = "") -> None:
        words = query.casefold().split()
        selection_list = self.query_one("#target-list", SelectionList)
        self._rebuilding = True
        try:
            selection_list.clear_options()
            for target in self._targets.values():
                searchable = (
                    f"{target.label} {target.host} {target.category} {target.description}"
                ).casefold()
                if words and not all(word in searchable for word in words):
                    continue
                selection_list.add_option(
                    (self._option_label(target), target.id, target.id in self._selected)
                )
        finally:
            self._rebuilding = False

    @on(Input.Changed, "#target-search")
    def on_search_changed(self, event: Input.Changed) -> None:
        self._rebuild_list(event.value)

    @on(SelectionList.SelectedChanged, "#target-list")
    def on_targets_changed(self, event: SelectionList.SelectedChanged) -> None:
        if self._rebuilding:
            return
        visible = {str(option.value) for option in event.selection_list.options}
        selected_visible = {str(value) for value in event.selection_list.selected}
        selected = merge_visible_selection(self._selected, visible, selected_visible)
        if len(selected) > MAX_PERSISTENT_TARGETS:
            added = list(selected - self._selected)
            for target_id in added:
                event.selection_list.deselect(target_id)
            self._set_message(t("network.too_many_targets"), error=True)
            return
        self._selected = selected
        self._refresh_primary()
        self._set_message(t("network.targets_count", count=len(selected)))

    @on(Select.Changed, "#target-primary")
    def on_primary_changed(self, event: Select.Changed) -> None:
        if isinstance(event.value, str) and event.value in self._selected:
            self._primary = event.value

    def _add_custom(self) -> None:
        custom_input = self.query_one("#target-custom", Input)
        try:
            target = create_custom_target(custom_input.value)
        except ValueError as exc:
            self._set_message(str(exc), error=True)
            return
        if (
            target.id not in self._selected
            and len(self._selected) >= MAX_PERSISTENT_TARGETS
        ):
            self._set_message(t("network.too_many_targets"), error=True)
            return
        self._targets[target.id] = target
        self._selected.add(target.id)
        if self._primary is None:
            self._primary = target.id
        custom_input.value = ""
        self._rebuild_list(self.query_one("#target-search", Input).value)
        self._refresh_primary()
        self._set_message(target.warning or t("network.custom_added"))

    def _save(self) -> None:
        if not self._selected:
            self._set_message(t("network.choose_one_target"), error=True)
            return
        if self._primary not in self._selected:
            self._set_message(t("network.choose_primary"), error=True)
            return
        targets = tuple(
            target
            for target_id, target in self._targets.items()
            if target_id in self._selected
        )
        selection = TargetSelection(
            targets=targets,
            primary_target_id=self._primary,
            league_auto_detect=bool(self._config.get("league_auto_detect", True)),
            onboarding_completed=True,
        )
        self.dismiss(selection.to_config())

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "target-custom-add":
            self._add_custom()
        elif event.button.id == "target-save":
            self._save()
        elif event.button.id == "target-cancel":
            self.dismiss(None)

    @on(Input.Submitted, "#target-custom")
    def on_custom_submitted(self) -> None:
        self._add_custom()


class RepairConfirmationScreen(ModalScreen[bool]):
    """Require explicit confirmation for exactly one allow-listed repair."""

    CSS = """
    RepairConfirmationScreen { align: center middle; }
    #repair-confirmation {
        width: 76;
        height: auto;
        max-height: 80%;
        border: round $warning;
        background: $surface;
        padding: 1 2;
    }
    #repair-confirm-actions { height: auto; margin-top: 1; }
    #repair-confirm-actions Button { width: auto; margin-right: 1; }
    """

    def __init__(self, action) -> None:
        super().__init__()
        self._action = action

    def compose(self) -> ComposeResult:
        action = self._action
        preview = "\n".join(" ".join(command) for command in action.command_preview)
        if not preview:
            preview = t("network.no_system_command")
        elevation = (
            t("network.repair_requires_elevation")
            if action.requires_elevation
            else t("network.repair_no_elevation")
        )
        with Vertical(id="repair-confirmation"):
            yield Label(action.title, classes="section-title")
            yield Static(action.description)
            yield Static(f"{t('network.repair_scope')}: {action.scope}")
            yield Static(f"{t('network.repair_impact')}: {action.impact.value}")
            yield Static(elevation)
            yield Static(f"{t('network.repair_preview')}:\n{preview}")
            with Horizontal(id="repair-confirm-actions"):
                yield Button(
                    t("network.repair_confirm"), id="repair-confirm", variant="warning"
                )
                yield Button(t("network.targets_cancel"), id="repair-cancel")

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "repair-confirm":
            self.dismiss(True)
        elif event.button.id == "repair-cancel":
            self.dismiss(False)
