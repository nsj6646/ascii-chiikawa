#!/usr/bin/env python3
"""General-purpose Colored ASCII Video/GIF Player & HD ASCII GIF Exporter.

Streams any video (MP4/MOV/MKV/WEBM via ffmpeg) or animated GIF/image as
TrueColor ASCII art in the terminal, or renders a high-resolution glowing
colored ASCII GIF with HUD and live code panel.

Usage:
  1. Play default clip in terminal (chiikawa_hitorigotsu.mp4, 0:00-0:56):
       python3 ascii_player.py
  2. Play any video or GIF in terminal:
       python3 ascii_player.py /path/to/video.mp4
       python3 ascii_player.py /path/to/clip.gif --fps 15
  3. Export a video or GIF as a glowing colored ASCII GIF:
       python3 ascii_player.py video.mp4 --start 0 --duration 56 --export out.gif --preview preview.png
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from ascii_exporter import (
    GLYPHS,
    export_to_ascii_gif,
    find_bin,
    probe_video_dimensions,
    rgb_grid_to_glyph_indices,
)

# ANSI terminal helpers
RESET = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_SCREEN = "\033[2J\033[H"
CURSOR_HOME = "\033[H"

IMAGE_EXTS = {".gif", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_VIDEO_NAME = "chiikawa_hitorigotsu.mp4"
DEFAULT_CLIP_DURATION = 56.0  # 0:00 - 0:56


def format_ansi_frame(
    grgb_u8: np.ndarray,
    t: float,
    title: str,
    term_cols: int,
) -> str:
    """Convert an RGB uint8 grid [rows, cols, 3] into a TrueColor ANSI frame."""
    rows, cols, _ = grgb_u8.shape
    gi = rgb_grid_to_glyph_indices(grgb_u8.astype(np.float32), len(GLYPHS))
    chars_count = int(np.count_nonzero(gi > 0))

    mins, secs = divmod(t, 60.0)
    hud_l = f"ascii_player.py · {title}"
    hud_r = f"● {int(mins):02d}:{secs:05.2f}  {chars_count:,} chars"
    pad = max(1, term_cols - len(hud_l) - len(hud_r))
    header = (
        f"\033[1;38;2;214;220;230m{hud_l}{RESET}"
        f"{' ' * pad}"
        f"\033[1;38;2;148;232;160m{hud_r}{RESET}"
    )

    left_pad = " " * max(0, (term_cols - cols) // 2)
    glyph_list = GLYPHS
    lines = [header]
    for y in range(rows):
        row_gi = gi[y]
        row_rgb = grgb_u8[y]
        parts: list[str] = [left_pad] if left_pad else []
        last_rgb = None
        for x in range(cols):
            ch = glyph_list[row_gi[x]]
            if ch == " ":
                parts.append(" ")
                continue
            r, g, b = int(row_rgb[x, 0]), int(row_rgb[x, 1]), int(row_rgb[x, 2])
            if (r, g, b) != last_rgb:
                parts.append(f"\033[38;2;{r};{g};{b}m{ch}")
                last_rgb = (r, g, b)
            else:
                parts.append(ch)
        parts.append(RESET)
        lines.append("".join(parts))

    lines.append(
        f"\033[38;2;140;148;164m[Ctrl+C] Exit  |  --export out.gif to render HD ASCII GIF{RESET}"
    )
    return "\n".join(lines)


def fit_terminal_grid(
    src_w: int,
    src_h: int,
    term_cols: int,
    term_rows: int,
    char_aspect: float = 0.5,
) -> tuple[int, int]:
    """Compute aspect-ratio-preserving (cols, rows) inside the terminal."""
    avail_cols = max(32, term_cols)
    avail_rows = max(12, term_rows - 3)
    cols = avail_cols
    rows = int(round(cols * (src_h / src_w) * char_aspect))
    if rows > avail_rows:
        rows = avail_rows
        cols = int(round(rows * (src_w / src_h) / char_aspect))
    return max(16, min(cols, avail_cols)), max(8, min(rows, avail_rows))


def load_image_frames(path: Path) -> list[Image.Image]:
    """Load all frames from an animated GIF or single image."""
    img = Image.open(path)
    frames: list[Image.Image] = []
    try:
        while True:
            frames.append(img.convert("RGB").copy())
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    return frames or [img.convert("RGB")]


def play_video_terminal(
    video_path: Path,
    fps: int,
    start_sec: float,
    duration: float | None,
    loops: int,
    title: str,
) -> None:
    """Stream any video directly through ffmpeg into live TrueColor terminal ASCII."""
    ffmpeg = find_bin("ffmpeg")
    src_w, src_h = probe_video_dimensions(video_path)

    sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN)
    sys.stdout.flush()

    loop_count = 0
    dec: subprocess.Popen[bytes] | None = None
    try:
        while loops == 0 or loop_count < loops:
            term = shutil.get_terminal_size((120, 40))
            cols, rows = fit_terminal_grid(src_w, src_h, term.columns, term.lines)

            cmd = [ffmpeg, "-v", "error", "-ss", str(start_sec)]
            if duration is not None:
                cmd += ["-t", str(duration)]
            cmd += [
                "-i", str(video_path),
                "-vf", f"fps={fps},scale={cols}:{rows}:flags=bilinear",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "-",
            ]
            dec = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            assert dec.stdout is not None

            frame_bytes = cols * rows * 3
            loop_start = time.perf_counter()
            frame_idx = 0

            while True:
                raw = dec.stdout.read(frame_bytes)
                if len(raw) < frame_bytes:
                    break
                grgb_u8 = np.frombuffer(raw, dtype=np.uint8).reshape((rows, cols, 3))
                t = start_sec + frame_idx / fps
                out = format_ansi_frame(grgb_u8, t, title, term.columns)
                sys.stdout.write(CURSOR_HOME + out)
                sys.stdout.flush()

                frame_idx += 1
                next_tick = loop_start + frame_idx / fps
                sleep_s = next_tick - time.perf_counter()
                if sleep_s > 0:
                    time.sleep(sleep_s)

            dec.stdout.close()
            dec.wait()
            dec = None
            loop_count += 1
    except KeyboardInterrupt:
        pass
    finally:
        if dec is not None:
            try:
                if dec.stdout is not None:
                    dec.stdout.close()
                dec.terminate()
                dec.wait(timeout=1.0)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                dec.kill()
                try:
                    dec.wait(timeout=1.0)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
                    pass
        sys.stdout.write(SHOW_CURSOR + RESET + "\n")
        sys.stdout.flush()


def play_image_terminal(
    image_path: Path,
    fps: int,
    loops: int,
    title: str,
) -> None:
    """Play an animated GIF or image in the terminal as TrueColor ASCII."""
    frames = load_image_frames(image_path)
    src_w, src_h = frames[0].size

    sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN)
    sys.stdout.flush()

    start = time.perf_counter()
    frame_idx = 0
    total_target = len(frames) * loops if loops > 0 else 0
    try:
        while total_target == 0 or frame_idx < total_target:
            term = shutil.get_terminal_size((120, 40))
            cols, rows = fit_terminal_grid(src_w, src_h, term.columns, term.lines)
            src = frames[frame_idx % len(frames)]
            small = src.resize((cols, rows), Image.Resampling.BILINEAR)
            grgb_u8 = np.asarray(small, dtype=np.uint8)
            out = format_ansi_frame(grgb_u8, frame_idx / fps, title, term.columns)
            sys.stdout.write(CURSOR_HOME + out)
            sys.stdout.flush()

            frame_idx += 1
            next_tick = start + frame_idx / fps
            sleep_s = next_tick - time.perf_counter()
            if sleep_s > 0:
                time.sleep(sleep_s)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(SHOW_CURSOR + RESET + "\n")
        sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="General-purpose Colored ASCII Video/GIF Player & HD ASCII GIF Exporter."
    )
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=None,
        help=f"Video or GIF/image path (default: {DEFAULT_VIDEO_NAME})",
    )
    parser.add_argument("--fps", type=int, default=15, help="Playback/export FPS (default: 15)")
    parser.add_argument("--loops", type=int, default=0, help="Terminal loops; 0=infinite")
    parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds")
    parser.add_argument("--duration", type=float, default=None, help="Clip duration in seconds")
    parser.add_argument("--width", type=int, default=600, help="Output width for --export mode")
    parser.add_argument("--title", type=str, default=None, help="HUD subtitle text")
    parser.add_argument("--export", type=Path, default=None, help="Export HD glowing ASCII GIF path")
    parser.add_argument("--preview", type=Path, default=None, help="Export preview PNG path (with --export)")
    args = parser.parse_args()

    using_default = args.source is None
    source_path = args.source or Path(__file__).with_name(DEFAULT_VIDEO_NAME)
    if not source_path.exists():
        parser.error(f"Input file not found: {source_path}")

    duration = args.duration
    if duration is None and using_default:
        duration = DEFAULT_CLIP_DURATION

    title = args.title or ("hitorigotsu · chiikawa" if using_default else source_path.stem)

    if args.export is not None:
        export_to_ascii_gif(
            source_path=source_path,
            export_path=args.export,
            preview_path=args.preview,
            fps=args.fps,
            start_sec=args.start,
            duration=duration,
            out_width=args.width,
            title=title,
        )
        return

    if source_path.suffix.lower() in IMAGE_EXTS:
        play_image_terminal(source_path, args.fps, args.loops, title)
    else:
        play_video_terminal(source_path, args.fps, args.start, duration, args.loops, title)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write(SHOW_CURSOR + RESET + "\n")
        sys.stdout.flush()
        sys.exit(0)
