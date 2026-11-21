# Community 39

> 26 nodes · cohesion 0.13

## Key Concepts

- **gif_generator.py** (20 connections) — `recorder/gif_generator.py`
- **generate_gif()** (12 connections) — `recorder/gif_generator.py`
- **io** (7 connections)
- **_prepare_images()** (7 connections) — `recorder/gif_generator.py`
- **_save_with_ffmpeg()** (7 connections) — `recorder/gif_generator.py`
- **_save_with_gifski()** (7 connections) — `recorder/gif_generator.py`
- **tempfile** (7 connections)
- **_svg_to_png_bytes()** (5 connections) — `recorder/gif_generator.py`
- **recorder/__init__.py** (5 connections) — `recorder/__init__.py`
- **Path** (4 connections)
- **_render_svg_raw()** (4 connections) — `recorder/gif_generator.py`
- **_save_with_pillow()** (4 connections) — `recorder/gif_generator.py`
- **_strip_svg_animation()** (4 connections) — `recorder/gif_generator.py`
- **_expand_for_constant_fps()** (2 connections) — `recorder/gif_generator.py`
- **_finalize_durations()** (2 connections) — `recorder/gif_generator.py`
- **_frame_hash()** (1 connections) — `recorder/gif_generator.py`
- **GIF generator — converts Rich SVG snapshots to animated GIF. Backends tried in…** (1 connections) — `recorder/gif_generator.py`
- **Remove CSS animations from SVG so each frame is a static snapshot.** (1 connections) — `recorder/gif_generator.py`
- **Convert SVG frames to normalised RGBA images + per-frame durations.** (1 connections) — `recorder/gif_generator.py`
- **High-quality Pillow GIF with per-frame median-cut + Floyd-Steinberg.** (1 connections) — `recorder/gif_generator.py`
- **Use gifski for the best possible GIF quality (lossy encoder).** (1 connections) — `recorder/gif_generator.py`
- **Use ffmpeg palettegen/paletteuse with Floyd-Steinberg dithering.** (1 connections) — `recorder/gif_generator.py`
- **Convert a list of SVG strings into an animated GIF. Quality pipeline: - SVGs…** (1 connections) — `recorder/gif_generator.py`
- **Convert SVG string to high-quality PNG bytes. Renders at ``width * scale`` then…** (1 connections) — `recorder/gif_generator.py`
- **Low-level SVG → PNG using best available renderer.** (1 connections) — `recorder/gif_generator.py`
- *... and 1 more nodes in this community*

## Relationships

- [Community 15](Community_15.md) (7 shared connections)
- [Community 31](Community_31.md) (3 shared connections)
- [Community 51](Community_51.md) (3 shared connections)
- [Community 99](Community_99.md) (3 shared connections)
- [Community 12](Community_12.md) (2 shared connections)
- [Community 43](Community_43.md) (2 shared connections)
- [Community 14](Community_14.md) (1 shared connections)
- [Community 53](Community_53.md) (1 shared connections)

## Source Files

- `recorder/__init__.py`
- `recorder/gif_generator.py`

## Audit Trail

- EXTRACTED: 65 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*