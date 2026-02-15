"""GIF generator — converts Rich SVG snapshots to animated GIF."""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
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
    except Exception:
        # Retry with smaller width if Cairo rejects the size
        try:
            import cairosvg

            return cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"),
                output_width=width // 2,
            )
        except Exception:
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


def _prepare_images(
    svg_frames: list[str],
    width: int,
    fps: int,
):
    from PIL import Image

    images: list[Image.Image] = []
    for svg in svg_frames:
        svg_clean = _strip_svg_animation(svg)
        png_bytes = _svg_to_png_bytes(svg_clean, width=width)
        if png_bytes:
            image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            images.append(image)

    if not images:
        return [], []

    import statistics

    target_width = max(image.width for image in images)
    heights = [image.height for image in images]
    median_h = statistics.median(heights)
    stdev_h = statistics.stdev(heights) if len(heights) > 1 else 0
    target_height = int(median_h + stdev_h)
    background = images[0].getpixel((0, 0))

    normalized_images: list[Image.Image] = []
    for image in images:
        if image.size == (target_width, target_height):
            normalized_images.append(image)
            continue

        cropped = image.crop((0, 0, min(image.width, target_width), min(image.height, target_height)))
        canvas = Image.new("RGBA", (target_width, target_height), background)
        canvas.paste(cropped, (0, 0))
        normalized_images.append(canvas)

    import hashlib

    def _frame_hash(img: Image.Image) -> str:
        return hashlib.md5(img.tobytes()).hexdigest()

    frame_ms = max(1, int(1000 / max(1, fps)))
    deduped: list[Image.Image] = [normalized_images[0]]
    durations: list[int] = [frame_ms]

    prev_hash = _frame_hash(normalized_images[0])

    for img in normalized_images[1:]:
        h = _frame_hash(img)
        if h == prev_hash:
            durations[-1] += frame_ms
        else:
            deduped.append(img)
            durations.append(frame_ms)
            prev_hash = h

    return deduped, durations


def _finalize_durations(
    durations: list[int],
    fps: int,
    last_frame_duration: float,
) -> list[int]:
    if not durations:
        return []
    frame_ms = max(1, int(1000 / max(1, fps)))
    normalized = [max(frame_ms, d) for d in durations]
    normalized[-1] = max(normalized[-1], int(last_frame_duration * 1000))
    return normalized


def _expand_for_constant_fps(images, durations: list[int], fps: int):
    frame_ms = max(1, int(1000 / max(1, fps)))
    expanded = []
    for image, duration in zip(images, durations):
        repeats = max(1, int(round(duration / frame_ms)))
        expanded.extend([image] * repeats)
    return expanded


def _save_with_pillow(images, durations: list[int], output: Path) -> bool:
    from PIL import Image

    palette_images: list[Image.Image] = []
    for image in images:
        converted = image.convert("P", palette=Image.ADAPTIVE, colors=256)
        palette_images.append(converted)

    palette_images[0].save(
        output,
        save_all=True,
        append_images=palette_images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    return True


def _save_with_gifski(images, fps: int, output: Path) -> bool:
    gifski_bin = shutil.which("gifski") or shutil.which("gifski.exe")
    if not gifski_bin:
        return False

    with tempfile.TemporaryDirectory(prefix="varedura_gif_") as temp_dir:
        temp_path = Path(temp_dir)
        frame_paths: list[str] = []
        for idx, image in enumerate(images):
            frame_file = temp_path / f"frame_{idx:06d}.png"
            image.save(frame_file, format="PNG")
            frame_paths.append(str(frame_file))

        cmd = [gifski_bin, "-o", str(output), "--fps", str(max(1, fps)), *frame_paths]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and output.exists()


def _save_with_ffmpeg(images, fps: int, output: Path) -> bool:
    ffmpeg_bin = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not ffmpeg_bin:
        return False

    with tempfile.TemporaryDirectory(prefix="varedura_gif_") as temp_dir:
        temp_path = Path(temp_dir)
        for idx, image in enumerate(images):
            frame_file = temp_path / f"frame_{idx:06d}.png"
            image.save(frame_file, format="PNG")

        palette_file = temp_path / "palette.png"
        input_pattern = str(temp_path / "frame_%06d.png")

        gen_palette = [
            ffmpeg_bin,
            "-y",
            "-framerate",
            str(max(1, fps)),
            "-i",
            input_pattern,
            "-vf",
            "palettegen=stats_mode=diff",
            str(palette_file),
        ]

        use_palette = [
            ffmpeg_bin,
            "-y",
            "-framerate",
            str(max(1, fps)),
            "-i",
            input_pattern,
            "-i",
            str(palette_file),
            "-lavfi",
            "paletteuse=dither=sierra2_4a",
            "-loop",
            "0",
            str(output),
        ]

        p1 = subprocess.run(gen_palette, capture_output=True, text=True)
        if p1.returncode != 0:
            return False

        p2 = subprocess.run(use_palette, capture_output=True, text=True)
        return p2.returncode == 0 and output.exists()


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

    prepared_images, base_durations = _prepare_images(svg_frames, width=width, fps=fps)
    if not prepared_images:
        return None

    durations = _finalize_durations(
        durations=base_durations,
        fps=fps,
        last_frame_duration=last_frame_duration,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    constant_fps_images = _expand_for_constant_fps(prepared_images, durations, fps)

    if constant_fps_images and _save_with_gifski(constant_fps_images, fps=fps, output=output):
        return output

    if constant_fps_images and _save_with_ffmpeg(constant_fps_images, fps=fps, output=output):
        return output

    if _save_with_pillow(prepared_images, durations=durations, output=output):
        return output

    return None
