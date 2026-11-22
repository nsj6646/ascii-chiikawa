"""Core ASCII glyph rendering and 2-pass glowing HD ASCII GIF exporter."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Dense ASCII ramp ordered from darkest to brightest
GLYPHS = " .,:;irsXA253hMHGS#9B&@"
CELL_W = 4
CELL_H = 5

FONT_CANDIDATES = [
    "/System/Library/Fonts/SFNSMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
]

CODE_SNIPPET = [
    (112, "def letters_to_pixels(gi, grgb, atlas):"),
    (113, "    m = atlas[gi]"),
    (114, "    img = m[..., None] * grgb[:, :, None, None, :]"),
    (115, "    img = img.transpose(0, 2, 1, 3, 4).reshape(H, W, 3)"),
    (116, "    glow = GaussianBlur(img, radius=1.5)"),
    (117, "    return np.clip(img + 0.58 * glow, 0, 255)"),
]


def find_bin(name: str) -> str:
    """Locate ffmpeg/ffprobe in PATH or common Homebrew locations."""
    found = shutil.which(name)
    if found:
        return found
    for prefix in ("/opt/homebrew/bin", "/usr/local/bin"):
        candidate = os.path.join(prefix, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(
        f"'{name}' not found. Install ffmpeg (e.g., `brew install ffmpeg`)."
    )


def probe_video_dimensions(video_path: Path) -> tuple[int, int]:
    """Query video width and height via ffprobe."""
    ffprobe = find_bin("ffprobe")
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video_path),
    ]
    out = subprocess.check_output(cmd, text=True)
    stream = json.loads(out)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def rgb_grid_to_glyph_indices(grgb: np.ndarray, num_glyphs: int) -> np.ndarray:
    """Map an RGB float32 array [rows, cols, 3] to glyph indices [rows, cols]."""
    lum = (0.299 * grgb[..., 0] + 0.587 * grgb[..., 1] + 0.114 * grgb[..., 2]) / 255.0
    return np.clip((lum * (num_glyphs - 1)).astype(np.int32), 0, num_glyphs - 1)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def build_glyph_atlas(glyphs: str, cell_w: int, cell_h: int) -> np.ndarray:
    """Pre-render crisp grayscale alpha masks for every ASCII glyph."""
    scale = 4
    font = load_font(cell_h * scale)
    atlas = np.zeros((len(glyphs), cell_h, cell_w), dtype=np.float32)
    for i, ch in enumerate(glyphs):
        if ch == " ":
            continue
        im = Image.new("L", (cell_w * scale, cell_h * scale), 0)
        d = ImageDraw.Draw(im)
        d.text((1, -2), ch, fill=255, font=font)
        im = im.resize((cell_w, cell_h), Image.Resampling.BILINEAR)
        arr = np.asarray(im, dtype=np.float32) / 255.0
        mx = float(arr.max())
        if mx > 0.05:
            arr = np.clip(arr / mx * 1.15, 0.0, 1.0)
        atlas[i] = arr
    return atlas


def letters_to_pixels(
    gi: np.ndarray,
    grgb: np.ndarray,
    atlas: np.ndarray,
) -> np.ndarray:
    """Vectorized glyph-atlas splatting + subtle CRT bloom glow."""
    rows, cols = gi.shape
    ch, cw = atlas.shape[1], atlas.shape[2]
    m = atlas[gi]
    img = m[..., None] * grgb[:, :, None, None, :]
    img = img.transpose(0, 2, 1, 3, 4).reshape(rows * ch, cols * cw, 3)
    base = np.clip(img, 0, 255).astype(np.uint8)
    glow = np.asarray(
        Image.fromarray(base).filter(ImageFilter.GaussianBlur(radius=1.5)),
        dtype=np.float32,
    )
    return np.clip(base.astype(np.float32) + 0.58 * glow, 0, 255).astype(np.uint8)


def export_to_ascii_gif(
    source_path: Path,
    export_path: Path,
    preview_path: Path | None,
    fps: int,
    start_sec: float,
    duration: float | None,
    out_width: int,
    title: str,
) -> None:
    """Stream any video/GIF through ffmpeg -> glowing ASCII glyph engine -> 2-pass palette GIF."""
    ffmpeg = find_bin("ffmpeg")
    src_w, src_h = probe_video_dimensions(source_path)

    # Snap art dimensions to multiples of CELL_W and CELL_H, keeping even height for yuv420p
    cols = max(60, out_width // CELL_W)
    art_w = cols * CELL_W
    rows = max(30, int(round(art_w * (src_h / src_w) / CELL_H)))
    if (rows * CELL_H) % 2 != 0:
        rows += 1
    art_h = rows * CELL_H

    hud_h = 72
    code_h = 156
    total_h = hud_h + art_h + code_h

    atlas = build_glyph_atlas(GLYPHS, CELL_W, CELL_H)
    font_ui = load_font(16)
    font_sub = load_font(12)
    font_code = load_font(11)

    dec_cmd = [ffmpeg, "-v", "error", "-ss", str(start_sec)]
    if duration is not None:
        dec_cmd += ["-t", str(duration)]
    dec_cmd += [
        "-i", str(source_path),
        "-vf", f"fps={fps},scale={cols}:{rows}:flags=bilinear",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-",
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_mp4 = Path(tmpdir) / "ascii_tmp.mp4"
        tmp_pal = Path(tmpdir) / "palette.png"

        enc_cmd = [
            ffmpeg, "-y", "-v", "error",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{art_w}x{total_h}",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "16",
            "-pix_fmt", "yuv420p",
            str(tmp_mp4),
        ]

        dec = subprocess.Popen(dec_cmd, stdout=subprocess.PIPE)
        enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)

        frame_bytes = cols * rows * 3
        frame_idx = 0
        saved_preview = False
        last_canvas: Image.Image | None = None

        assert dec.stdout is not None and enc.stdin is not None
        try:
            while True:
                raw = dec.stdout.read(frame_bytes)
                if len(raw) < frame_bytes:
                    break
                grgb = np.frombuffer(raw, dtype=np.uint8).reshape((rows, cols, 3)).astype(np.float32)
                gi = rgb_grid_to_glyph_indices(grgb, len(GLYPHS))
                ascii_rgb = letters_to_pixels(gi, grgb, atlas)

                t = frame_idx / fps
                canvas = Image.new("RGB", (art_w, total_h), (7, 9, 13))
                canvas.paste(Image.fromarray(ascii_rgb), (0, hud_h))
                draw = ImageDraw.Draw(canvas)

                letters_count = int(np.count_nonzero(gi > 0))
                draw.text((16, 10), "ascii_player.py · ascii", font=font_ui, fill=(214, 220, 230))
                draw.ellipse((art_w - 134, 15, art_w - 126, 23), fill=(110, 225, 130))
                draw.text((art_w - 118, 10), f"t {t:06.2f}s", font=font_ui, fill=(148, 232, 160))
                draw.text((16, 34), f"~ {title}   |   letters {letters_count:,}", font=font_sub, fill=(168, 174, 188))

                # Bottom code panel
                y0 = hud_h + art_h
                draw.rectangle((0, y0, art_w, total_h), fill=(14, 18, 26))
                draw.line((0, y0, art_w, y0), fill=(36, 44, 58), width=2)
                draw.text((16, y0 + 8), "ascii_player.py", font=font_sub, fill=(192, 200, 214))
                draw.ellipse((art_w - 156, y0 + 11, art_w - 148, y0 + 19), fill=(240, 170, 74))
                draw.text((art_w - 140, y0 + 8), f"running · {fps} fps", font=font_sub, fill=(228, 184, 114))
                active_idx = int(t * 3.0) % len(CODE_SNIPPET)
                for idx, (lineno, text) in enumerate(CODE_SNIPPET):
                    ly = y0 + 32 + idx * 19
                    if idx == active_idx:
                        draw.rectangle((0, ly - 2, art_w, ly + 15), fill=(26, 34, 50))
                    draw.text((14, ly), f"{lineno:>3}", font=font_code, fill=(88, 98, 118))
                    col = (146, 198, 255) if text.startswith("def ") else (188, 198, 214)
                    draw.text((48, ly), text, font=font_code, fill=col)

                last_canvas = canvas
                if preview_path is not None and not saved_preview and frame_idx >= min(25, fps * 2):
                    canvas.save(preview_path)
                    saved_preview = True

                enc.stdin.write(canvas.tobytes())
                frame_idx += 1
        finally:
            dec.stdout.close()
            enc.stdin.close()
            dec.wait()
            enc.wait()

        if enc.returncode != 0:
            raise RuntimeError(f"ffmpeg encoder failed with exit code {enc.returncode}")

        if preview_path is not None and not saved_preview and last_canvas is not None:
            last_canvas.save(preview_path)

        subprocess.run(
            [
                ffmpeg, "-y", "-v", "error",
                "-i", str(tmp_mp4),
                "-vf", "palettegen=stats_mode=diff",
                str(tmp_pal),
            ],
            check=True,
        )
        subprocess.run(
            [
                ffmpeg, "-y", "-v", "error",
                "-i", str(tmp_mp4),
                "-i", str(tmp_pal),
                "-lavfi", "paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
                str(export_path),
            ],
            check=True,
        )
        print(f"Saved ASCII GIF: {export_path} ({frame_idx} frames @ {fps} fps, {art_w}x{total_h})")
