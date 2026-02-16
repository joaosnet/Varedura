"""Generate pixel-art sprites for the Varedura Roomba mascot.

Run once:  uv run python -m mascot.generate_sprites
Output:    mascot/images/*.png  (48x48, RGBA)
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "images"
SIZE = 48

# ── Palette ──────────────────────────────────────────────────────────
T = (0, 0, 0, 0)          # transparent

TEAL      = (0, 190, 170, 255)     # body main
TEAL_L    = (60, 220, 200, 255)    # body highlight
TEAL_D    = (0, 140, 125, 255)     # body shadow
TEAL_DD   = (0, 100, 90, 255)      # body deep shadow
VISOR_BG  = (15, 30, 40, 255)      # visor/face dark bg
WHITE     = (255, 255, 255, 255)
BLACK     = (10, 10, 10, 255)
EYE_CYAN  = (80, 220, 255, 255)    # LED eyes
EYE_GLOW  = (180, 240, 255, 255)   # eye highlight
GREY      = (100, 105, 115, 255)   # metal parts
GREY_L    = (160, 165, 175, 255)   # metal highlight
GREY_D    = (60, 65, 70, 255)      # metal shadow
RED_LED   = (255, 50, 50, 255)     # antenna LED
RED_GLOW  = (255, 100, 100, 255)
GREEN_LED = (50, 255, 100, 255)    # success
GREEN_GL  = (100, 255, 150, 255)
RED_ERR   = (255, 60, 60, 255)     # error
YELLOW    = (255, 230, 50, 255)    # sparkle
SPARK     = (255, 255, 200, 255)
ORANGE    = (255, 150, 30, 255)    # broom bristles
BROWN     = (160, 110, 60, 255)    # broom handle
BUMPER    = (0, 160, 145, 255)     # bumper ring


def _new() -> Image.Image:
    return Image.new("RGBA", (SIZE, SIZE), T)


def _draw_antenna(d: ImageDraw.ImageDraw, led_color=RED_LED, glow_color=RED_GLOW) -> None:
    """Draw antenna stalk + LED on top."""
    # Stalk
    d.rectangle([22, 6, 25, 14], fill=GREY)
    d.rectangle([23, 6, 24, 14], fill=GREY_L)
    # LED ball
    d.ellipse([20, 2, 27, 8], fill=led_color)
    d.ellipse([22, 3, 25, 6], fill=glow_color)


def _draw_body(d: ImageDraw.ImageDraw) -> None:
    """Draw the Roomba disc body."""
    # Main disc body — outer bumper ring
    d.ellipse([5, 20, 42, 42], fill=BUMPER)
    # Inner body
    d.ellipse([7, 21, 40, 41], fill=TEAL)
    # Top highlight band
    d.ellipse([9, 22, 38, 34], fill=TEAL_L)
    # Bottom shadow
    d.chord([8, 34, 39, 42], start=0, end=180, fill=TEAL_D)
    # Vent lines on body
    for y in [36, 38]:
        d.line([(14, y), (33, y)], fill=TEAL_DD, width=1)
    # Wheels
    d.ellipse([8, 40, 15, 45], fill=GREY_D)
    d.ellipse([9, 41, 14, 44], fill=GREY)
    d.ellipse([32, 40, 39, 45], fill=GREY_D)
    d.ellipse([33, 41, 38, 44], fill=GREY)


def _draw_visor(d: ImageDraw.ImageDraw) -> None:
    """Draw the face visor plate on the top-front of the body."""
    d.rounded_rectangle([11, 14, 36, 28], radius=4, fill=VISOR_BG)
    # Visor border highlight
    d.rounded_rectangle([12, 15, 35, 27], radius=3, fill=(25, 45, 60, 255))


def _draw_eyes(d: ImageDraw.ImageDraw, color=EYE_CYAN, glow=EYE_GLOW,
               left_open=True, right_open=True) -> None:
    """Draw expressive LED eyes inside the visor."""
    if left_open:
        # Left eye
        d.ellipse([15, 17, 22, 25], fill=BLACK)
        d.ellipse([16, 18, 21, 24], fill=color)
        d.ellipse([17, 18, 19, 21], fill=glow)  # highlight
    else:
        # Closed/blink — just a line
        d.rectangle([15, 20, 22, 22], fill=color)

    if right_open:
        # Right eye
        d.ellipse([25, 17, 32, 25], fill=BLACK)
        d.ellipse([26, 18, 31, 24], fill=color)
        d.ellipse([27, 18, 29, 21], fill=glow)
    else:
        d.rectangle([25, 20, 32, 22], fill=color)


def _draw_smile(d: ImageDraw.ImageDraw) -> None:
    d.arc([18, 26, 29, 33], start=10, end=170, fill=EYE_CYAN, width=1)


def _draw_open_mouth(d: ImageDraw.ImageDraw) -> None:
    d.ellipse([20, 27, 27, 32], fill=VISOR_BG)
    d.ellipse([21, 27, 26, 30], fill=EYE_CYAN)


def _draw_sad_mouth(d: ImageDraw.ImageDraw) -> None:
    d.arc([18, 29, 29, 35], start=190, end=350, fill=RED_ERR, width=1)


def _draw_sparkle(d: ImageDraw.ImageDraw, cx: int, cy: int, color=YELLOW, size=2) -> None:
    """Draw a 4-point star sparkle."""
    d.line([(cx - size, cy), (cx + size, cy)], fill=color, width=1)
    d.line([(cx, cy - size), (cx, cy + size)], fill=color, width=1)
    d.point((cx, cy), fill=SPARK)


def _draw_broom(d: ImageDraw.ImageDraw, x_offset=0) -> None:
    """Draw a broom next to the robot."""
    bx = 40 + x_offset
    # Handle
    d.line([(bx, 5), (bx, 32)], fill=BROWN, width=2)
    # Bristles
    for dx in range(-3, 4):
        d.line([(bx + dx, 33), (bx + dx, 40)], fill=ORANGE, width=1)
    # Bristle tips
    for dx in range(-2, 3):
        d.point((bx + dx, 41), fill=YELLOW)


# ── Sprite generators ────────────────────────────────────────────────

def gen_idle_1() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d)
    _draw_smile(d)
    return img


def gen_idle_2() -> Image.Image:
    """Blink frame."""
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d, left_open=False, right_open=False)
    return img


def gen_idle_3() -> Image.Image:
    """Look right frame."""
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d)
    _draw_body(d)
    _draw_visor(d)
    # Eyes shifted right
    d.ellipse([17, 17, 24, 25], fill=BLACK)
    d.ellipse([18, 18, 23, 24], fill=EYE_CYAN)
    d.ellipse([20, 18, 22, 21], fill=EYE_GLOW)
    d.ellipse([27, 17, 34, 25], fill=BLACK)
    d.ellipse([28, 18, 33, 24], fill=EYE_CYAN)
    d.ellipse([30, 18, 32, 21], fill=EYE_GLOW)
    _draw_smile(d)
    return img


def gen_working_1() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d, led_color=YELLOW, glow_color=SPARK)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d)
    _draw_open_mouth(d)
    _draw_broom(d, x_offset=0)
    _draw_sparkle(d, 4, 8)
    _draw_sparkle(d, 2, 25)
    return img


def gen_working_2() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d, led_color=YELLOW, glow_color=SPARK)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d)
    _draw_smile(d)
    _draw_broom(d, x_offset=-2)
    _draw_sparkle(d, 3, 14, color=SPARK)
    _draw_sparkle(d, 5, 30)
    return img


def gen_working_3() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d, led_color=ORANGE, glow_color=YELLOW)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d, left_open=True, right_open=False)
    _draw_open_mouth(d)
    _draw_broom(d, x_offset=1)
    _draw_sparkle(d, 2, 18, color=YELLOW)
    _draw_sparkle(d, 6, 6, color=SPARK)
    return img


def gen_success() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d, led_color=GREEN_LED, glow_color=GREEN_GL)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d, color=GREEN_LED, glow=GREEN_GL)
    _draw_smile(d)
    # Checkmark
    d.line([(36, 4), (39, 8), (45, 0)], fill=GREEN_LED, width=2)
    # Sparkles
    _draw_sparkle(d, 4, 5, color=GREEN_LED)
    _draw_sparkle(d, 44, 18, color=GREEN_GL)
    _draw_sparkle(d, 3, 35, color=GREEN_LED)
    _draw_sparkle(d, 44, 38, color=GREEN_GL)
    return img


def gen_error() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d, led_color=RED_ERR, glow_color=(255, 120, 120, 255))
    _draw_body(d)
    _draw_visor(d)
    # X eyes
    for (ex, ey) in [(15, 17), (25, 17)]:
        d.line([(ex + 1, ey + 1), (ex + 6, ey + 6)], fill=RED_ERR, width=2)
        d.line([(ex + 6, ey + 1), (ex + 1, ey + 6)], fill=RED_ERR, width=2)
    _draw_sad_mouth(d)
    # X mark
    d.line([(37, 3), (44, 10)], fill=RED_ERR, width=2)
    d.line([(44, 3), (37, 10)], fill=RED_ERR, width=2)
    return img


def gen_wave_1() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d)
    _draw_smile(d)
    # Arm waving up-right
    d.line([(38, 24), (44, 14)], fill=TEAL, width=3)
    d.ellipse([43, 10, 47, 14], fill=TEAL_L)
    return img


def gen_wave_2() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d)
    _draw_smile(d)
    # Arm waving higher
    d.line([(38, 24), (45, 10)], fill=TEAL, width=3)
    d.ellipse([44, 6, 48, 10], fill=TEAL_L)
    return img


def gen_scanning_1() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d, led_color=EYE_CYAN, glow_color=EYE_GLOW)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d, color=EYE_GLOW, glow=WHITE)
    _draw_smile(d)
    # Radar waves
    d.arc([14, 0, 33, 10], start=200, end=340, fill=EYE_CYAN, width=1)
    d.arc([10, -2, 37, 8], start=210, end=330, fill=(80, 220, 255, 120), width=1)
    return img


def gen_scanning_2() -> Image.Image:
    img = _new()
    d = ImageDraw.Draw(img)
    _draw_antenna(d, led_color=EYE_GLOW, glow_color=WHITE)
    _draw_body(d)
    _draw_visor(d)
    _draw_eyes(d, color=EYE_CYAN, glow=EYE_GLOW)
    _draw_smile(d)
    d.arc([12, -1, 35, 9], start=200, end=340, fill=EYE_GLOW, width=1)
    d.arc([8, -4, 39, 7], start=210, end=330, fill=(180, 240, 255, 100), width=1)
    return img


# ── Registry & main ──────────────────────────────────────────────────

SPRITES: dict[str, list] = {
    "idle":     [gen_idle_1, gen_idle_2, gen_idle_3],
    "working":  [gen_working_1, gen_working_2, gen_working_3],
    "success":  [gen_success],
    "error":    [gen_error],
    "wave":     [gen_wave_1, gen_wave_2],
    "scanning": [gen_scanning_1, gen_scanning_2],
}


def generate_all() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for state, generators in SPRITES.items():
        for i, gen_fn in enumerate(generators, 1):
            img = gen_fn()
            path = OUT / f"{state}_{i}.png"
            img.save(path)
            print(f"  ✓ {path.relative_to(Path(__file__).parent.parent)}")
    total = sum(len(v) for v in SPRITES.values())
    print(f"\n  {total} sprites generated in {OUT}")


if __name__ == "__main__":
    generate_all()
