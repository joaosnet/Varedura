"""Termux: macros das teclas extras, tecla de teclado e digitação por diálogo.

Três problemas de toda TUI com mouse no Termux, resolvidos aqui:

1. As teclas extras do usuário digitam comandos de shell (``"\\nmenu\\n"``).
   Dentro da TUI essas letras acionavam atalhos aleatórios.  Agora o Enter
   inicial é segurado por um instante; se o que vem a seguir é um macro
   conhecido, ele é executado como ação do Varedura.
2. Com o mouse do terminal ativo, tocar na tela não abre o teclado.  Enquanto
   o Varedura roda, a barra extra-keys ganha uma tecla ⌨ (removida ao sair).
3. Tocar num campo com o teclado fechado abre o diálogo nativo do Android
   (Termux:API) para digitar o valor.
"""

from __future__ import annotations

import atexit
import shlex

from textual import events, work
from textual.widgets import Input, Label

from i18n import t
from varedura import termux_env

_MACRO_WINDOW_SECONDS = 0.15
# As teclas extras enviam LF ("\\n"), que o Textual lê como ctrl+j; um Enter de
# verdade é CR.  Os dois delimitam um macro.
_MACRO_DELIMITERS = ("enter", "ctrl+j")
_KEYBOARD_OPEN_RATIO = 0.75


class TermuxKeysMixin:
    def _init_termux_keys_state(self) -> None:
        self._macro_commands: tuple[str, ...] = ()
        self._macro_capturing = False
        self._macro_buf = ""
        self._macro_held = None
        self._macro_timer = None
        self._keyboard_key_installed = False
        self._native_dialog_active = False
        self._max_rows_seen = 0

    # -- ciclo de vida -------------------------------------------------------
    @work(thread=True, exclusive=True, group="termux-keys")
    def _termux_keys_start(self) -> None:
        self._macro_commands = termux_env.extra_key_macros()
        # Remove restos de uma execução interrompida antes de instalar de novo.
        termux_env.set_keyboard_key(False, reload=False)
        if termux_env.set_keyboard_key(True):
            self._keyboard_key_installed = True
            atexit.register(termux_env.set_keyboard_key, False)

    def _termux_keys_reinstall(self) -> None:
        if not self._keyboard_key_installed:
            return
        self._macro_commands = termux_env.extra_key_macros()
        termux_env.set_keyboard_key(True)

    def _termux_keys_stop(self) -> None:
        if self._keyboard_key_installed:
            self._keyboard_key_installed = False
            termux_env.set_keyboard_key(False)

    # -- macros --------------------------------------------------------------
    def _termux_macro_enabled(self) -> bool:
        return (
            bool(self._macro_commands)
            and termux_env.is_termux()
            and not isinstance(self.focused, Input)
        )

    async def on_event(self, event) -> None:
        """Filtra as teclas ANTES do despacho normal.

        Tem de ser aqui: atalhos prioritários rodam na chegada do evento, mas
        as letras só voltam ao app depois de passar pelo widget em foco.  Com
        um binding para o LF, os dois LF de ``"\\nmenu\\n"`` eram tratados
        antes das letras, e estas viravam atalhos.
        """
        if isinstance(event, events.Key) and await self._termux_macro_filter(event):
            return
        await super().on_event(event)

    async def _termux_macro_filter(self, event) -> bool:
        """Devolve True se a tecla foi consumida pela captura de macro."""
        delimiter = event.key in _MACRO_DELIMITERS
        if not self._macro_capturing:
            if delimiter and self._termux_macro_enabled():
                self._macro_capturing = True
                self._macro_held = event
                self._macro_buf = ""
                self._macro_arm_timer()
                return True
            return False

        if delimiter:
            command, self._macro_buf = self._macro_buf, ""
            held = self._macro_take_held()
            if command in self._macro_commands:
                self._run_termux_macro(command)
                return True
            if not command and held is not None:
                # Dois Enter seguidos: entrega o primeiro e segura o segundo.
                await super().on_event(held)
                if self._termux_macro_enabled():
                    self._macro_capturing = True
                    self._macro_held = event
                    self._macro_arm_timer()
                    return True
                return False
            return True  # texto que não é macro: descarta

        char = event.character
        if isinstance(char, str) and len(char) == 1 and char.isprintable():
            candidate = self._macro_buf + char
            if any(command.startswith(candidate) for command in self._macro_commands):
                self._macro_buf = candidate
                self._macro_arm_timer()
                return True

        # Não é um macro: devolve o Enter segurado e deixa a tecla seguir.
        untouched = not self._macro_buf
        self._macro_buf = ""
        held = self._macro_take_held()
        if untouched and held is not None:
            await super().on_event(held)
        return False

    def _macro_arm_timer(self) -> None:
        if self._macro_timer is not None:
            self._macro_timer.stop()
        self._macro_timer = self.set_timer(_MACRO_WINDOW_SECONDS, self._macro_timeout)

    def _macro_take_held(self):
        """Encerra a captura e devolve a tecla que estava segurada."""
        self._macro_capturing = False
        if self._macro_timer is not None:
            self._macro_timer.stop()
            self._macro_timer = None
        held, self._macro_held = self._macro_held, None
        return held

    async def _macro_timeout(self) -> None:
        if not self._macro_capturing:
            return
        untouched = not self._macro_buf
        self._macro_buf = ""
        held = self._macro_take_held()
        if untouched and held is not None:
            await super().on_event(held)  # era um Enter comum

    def _run_termux_macro(self, command: str) -> None:
        """Traduz o comando de shell do botão para uma ação do Varedura."""
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        if not parts:
            return
        name = parts[0]
        if name in {"menu", "varedura"}:
            self._switch_main_tab("dashboard")
        elif name == "toggle-page":
            self.action_toggle_keyboard_page()
        elif name == "clear":
            return
        else:
            self.notify(t("termux.launching", label=command))
            try:
                rc = self._run_suspended_command(parts, pause=True)
                self.notify(t("termux.returned", label=command, code=rc))
            except OSError as exc:
                self.notify(str(exc), severity="error")

    # -- digitação por diálogo nativo ---------------------------------------
    def _keyboard_probably_open(self) -> bool:
        """O Termux encolhe o terminal quando o teclado virtual está aberto."""
        rows = self.size.height
        self._max_rows_seen = max(self._max_rows_seen, rows)
        return rows < self._max_rows_seen * _KEYBOARD_OPEN_RATIO

    def on_click(self, event) -> None:
        if not termux_env.is_termux():
            return
        widget = getattr(event, "widget", None)
        while widget is not None and not isinstance(widget, Input):
            widget = widget.parent
        if widget is None or widget.disabled or self._native_dialog_active:
            return
        if self._keyboard_probably_open() or not termux_env.has_native_dialog():
            return
        self._native_dialog_active = True
        self._ask_native_input(
            widget,
            self._input_title(widget),
            str(widget.value or widget.placeholder or ""),
            getattr(widget, "type", "text") == "integer",
            bool(getattr(widget, "password", False)),
        )

    @staticmethod
    def _input_title(widget: Input) -> str:
        """Rótulo do campo: o Label vizinho na mesma linha do formulário."""
        parent = widget.parent
        if parent is not None:
            for sibling in parent.children:
                if isinstance(sibling, Label):
                    text = str(getattr(sibling, "content", "") or "").strip()
                    if text:
                        return text
        return str(widget.placeholder or "Varedura")

    @work(thread=True, exclusive=True, group="termux-dialog")
    def _ask_native_input(
        self, widget: Input, title: str, hint: str, numeric: bool, password: bool
    ) -> None:
        try:
            value = termux_env.native_text_dialog(
                title, hint, numeric=numeric, password=password
            )
        finally:
            self._native_dialog_active = False
        if value is not None:
            self.call_from_thread(self._apply_native_input, widget, value)

    def _apply_native_input(self, widget: Input, value: str) -> None:
        try:
            widget.value = value
            widget.focus()
        except Exception:
            pass
