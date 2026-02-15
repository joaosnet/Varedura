"""ASCII art frames for the Varedura mascot — a modern cleaning robot."""

from __future__ import annotations

# ─── Idle frames (menu / waiting) ───────────────────────────────────

IDLE_FRAMES = [
    """\
      ╭━━━━━╮
      │ ◉ ◉ │
      │  ▽  │
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │ VAREDURA │
    ╰━━━┳┳━━━━╯
        ┃┃
       ━┛┗━""",
    """\
      ╭━━━━━╮
      │ ◉ ◉ │
      │  ◡  │
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │ VAREDURA │
    ╰━━━┳┳━━━━╯
        ┃┃
       ━┛┗━""",
    """\
      ╭━━━━━╮
      │ ● ◉ │
      │  ▽  │
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │ VAREDURA │
    ╰━━━┳┳━━━━╯
        ┃┃
       ━┛┗━""",
    """\
      ╭━━━━━╮
      │ ◉ ● │
      │  ◡  │
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │ VAREDURA │
    ╰━━━┳┳━━━━╯
        ┃┃
       ━┛┗━""",
]

# ─── Working frames (during tool execution) ─────────────────────────

WORKING_FRAMES = [
    """\
      ╭━━━━━╮
      │ ◉ ◉ │
      │  ◡  │  ⣿
      ╰━━┳━━╯ ╱
    ╭━━━━┻━━╮╱
    │LIMPANDO│
    ╰━━━┳┳━━╯
        ┃┃  ░░
       ━┛┗━ ░░""",
    """\
      ╭━━━━━╮
      │ ◉ ◉ │
      │  ◡  │  ⣿
      ╰━━┳━━╯╱
    ╭━━━━┻━╮╱
    │LIMPANDO│
    ╰━━━┳┳━━╯
        ┃┃ ▒▒
       ━┛┗━▒▒""",
    """\
      ╭━━━━━╮
      │ ◉ ◉ │    ⣿
      │  ◡  │  ╱
      ╰━━┳━━╯╱
    ╭━━━━┻━━━━╮
    │ LIMPANDO │
    ╰━━━┳┳━━━━╯
        ┃┃▓▓
       ━┛┗━""",
    """\
      ╭━━━━━╮  ⣿
      │ ◉ ◉ │╱
      │  ◡  ╱
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │ LIMPANDO │
    ╰━━━┳┳━━━━╯
        ┃┃ ░▒▓
       ━┛┗━""",
]

# ─── Success frame ──────────────────────────────────────────────────

SUCCESS_FRAMES = [
    """\
      ╭━━━━━╮
      │ ◉ ◉ │  ✅
      │  ◡  │
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │ ✨DONE✨ │
    ╰━━━┳┳━━━━╯
        ┃┃
       ━┛┗━""",
]

# ─── Error frame ────────────────────────────────────────────────────

ERROR_FRAMES = [
    """\
      ╭━━━━━╮
      │ ✖ ✖ │  ❌
      │  △  │
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │  ERRO!   │
    ╰━━━┳┳━━━━╯
        ┃┃
       ━┛┗━""",
]

# ─── Wave / goodbye frame ───────────────────────────────────────────

WAVE_FRAMES = [
    """\
      ╭━━━━━╮
      │ ◉ ◉ │ ╱
      │  ◡  │╱
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │  BYE! 👋 │
    ╰━━━┳┳━━━━╯
        ┃┃
       ━┛┗━""",
    """\
      ╭━━━━━╮  ╲
      │ ◉ ◉ │   ╲
      │  ◡  │
      ╰━━┳━━╯
    ╭━━━━┻━━━━╮
    │  BYE! 👋 │
    ╰━━━┳┳━━━━╯
        ┃┃
       ━┛┗━""",
]

# ─── Compact versions (for inline / sidebar) ────────────────────────

COMPACT_IDLE = [
    "╭◉◉╮ ▽ 🧹",
    "╭◉◉╮ ◡ 🧹",
]

COMPACT_WORKING = [
    "╭◉◉╮ ◡ ⣿░▒",
    "╭◉◉╮ ◡ ⣿▒▓",
]

COMPACT_SUCCESS = "╭◉◉╮ ◡ ✅"
COMPACT_ERROR = "╭✖✖╮ △ ❌"

# ─── State enum ──────────────────────────────────────────────────────


class STATES:
    """Mascot animation states."""

    IDLE = "idle"
    WORKING = "working"
    SUCCESS = "success"
    ERROR = "error"
    WAVE = "wave"


# ─── Frame registry ─────────────────────────────────────────────────

FRAMES: dict[str, list[str]] = {
    STATES.IDLE: IDLE_FRAMES,
    STATES.WORKING: WORKING_FRAMES,
    STATES.SUCCESS: SUCCESS_FRAMES,
    STATES.ERROR: ERROR_FRAMES,
    STATES.WAVE: WAVE_FRAMES,
}

COMPACT: dict[str, list[str] | str] = {
    STATES.IDLE: COMPACT_IDLE,
    STATES.WORKING: COMPACT_WORKING,
    STATES.SUCCESS: COMPACT_SUCCESS,
    STATES.ERROR: COMPACT_ERROR,
}
