"""GIF generator — converts Rich SVG snapshots to animated GIF."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Optional


def _svg_to_png_bytes(svg_content: str, width: int = 800) -> Optional[bytes]:
    """Convert SVG string to PNG bytes.

    Tries cairosvg first, falls back to svglib+reportlab.
    """
    # Try cairosvg (best quality)
    try:
        import cairosvg

        return cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            output_width=width,
        )
    except ImportError:
        pass

    # Fallback: svglib + reportlab (already in project deps)
    try:
        from svglib.svglib import renderSVG
        from reportlab.graphics import renderPM

        drawing = renderSVG.render(svg_content)
        if drawing:
            buf = io.BytesIO()
            renderPM.drawToFile(drawing, buf, fmt="PNG")
            return buf.getvalue()
    except Exception:
        pass

    # Last resort: simple HTML-to-image approach not available
    return None


def _strip_svg_animation(svg: str) -> str:
    """Remove CSS animations from SVG so each frame is a static snapshot."""
    svg = re.sub(r"<animate[^>]*/>", "", svg)
    svg = re.sub(r"@keyframes[^}]*\{[^}]*\}", "", svg)
    return svg


def generate_gif(
    svg_frames: list[str],
    output_path: str | Path,
    fps: int = 2,
    last_frame_duration: float = 3.0,
    width: int = 800,
) -> Optional[Path]:
    """Convert a list of SVG strings into an animated GIF.

    Args:
        svg_frames: List of SVG content strings (one per frame).
        output_path: Where to save the GIF.
        fps: Frames per second for the animation.
        last_frame_duration: How long to hold the last frame (seconds).
        width: Output width in pixels.

    Returns:
        Path to generated GIF, or None on failure.
    """
    try:
        from PIL import Image
    except ImportError:
        return None

    if not svg_frames:
        return None

    images: list[Image.Image] = []

    for svg in svg_frames:
        svg_clean = _strip_svg_animation(svg)
        png_bytes = _svg_to_png_bytes(svg_clean, width=width)
        if png_bytes:
            img = Image.open(io.BytesIO(png_bytes))
            # Convert to RGBA then to palette mode for GIF
            img = img.convert("RGBA")
            images.append(img)

    if not images:
        return None

    max_width = max(image.width for image in images)
    max_height = max(image.height for image in images)
    background = images[0].getpixel((0, 0))

    normalized_images: list[Image.Image] = []
    for image in images:
        if image.size == (max_width, max_height):
            normalized_images.append(image)
            continue

        canvas = Image.new("RGBA", (max_width, max_height), background)
        canvas.paste(image, (0, 0))
        normalized_images.append(canvas)

    # Deduplicate consecutive identical frames
    deduped: list[Image.Image] = [normalized_images[0]]
    durations: list[int] = [int(1000 / fps)]

    for img in normalized_images[1:]:
        if list(img.getdata()) == list(deduped[-1].getdata()):
            durations[-1] += int(1000 / fps)
        else:
            deduped.append(img)
            durations.append(int(1000 / fps))

    # Extend last frame duration
    durations[-1] = max(durations[-1], int(last_frame_duration * 1000))

    # Convert to palette mode for GIF compatibility
    palette_images = []
    for img in deduped:
        converted = img.convert("P", palette=Image.ADAPTIVE, colors=256)
        palette_images.append(converted)

    output = Path(output_path)

    palette_images[0].save(
        output,
        save_all=True,
        append_images=palette_images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )

    return output
