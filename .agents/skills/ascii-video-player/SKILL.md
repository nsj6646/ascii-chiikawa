---
name: ascii-video-player
description: >-
  Build a universal colored ASCII video player (`ascii_player.py`) and glowing HD ASCII GIFs
  from any YouTube clip or local video/GIF via ffmpeg rawvideo pipes. Use when the user asks
  to turn a YouTube link or video range into a terminal TrueColor ASCII animation, export a
  colored ASCII GIF with HUD/code panel, or recreate an `ascii_player.py` pipeline from scratch.
---

# Universal Colored ASCII Video Player Workflow

Build a format-agnostic TrueColor ASCII terminal player and glowing HD ASCII GIF exporter (`ascii_player.py`) from a YouTube URL or local media file.

## Step 1: Confirm scope and runtime environment

1. Confirm three inputs with the user if any are missing:
   - **Source**: YouTube URL or local video/GIF path.
   - **Clip range**: `start` and `duration` (seconds).
   - **Deliverables**: live terminal player (`ascii_player.py`), original GIF, and/or glowing colored ASCII GIF.
2. Verify dependencies in one command:
   - `ffmpeg` and `ffprobe` (and `yt-dlp` when sourcing from YouTube). If missing on macOS, install via Homebrew (`yes | brew install yt-dlp ffmpeg` to avoid interactive `[y/n]` stalls).
   - A Python interpreter with `numpy` and `PIL` (`Pillow`). On macOS, Homebrew `python3` in `/opt/homebrew/bin` often lacks `numpy`/`PIL` while `/usr/bin/python3` has them; select the interpreter that passes `python -c "import numpy, PIL"` and prepend `/opt/homebrew/bin` to `PATH` for `ffmpeg`/`ffprobe`.

**Done when**: source, range, deliverables, `ffmpeg`/`ffprobe` paths, and a verified `numpy`+`PIL` Python path are all confirmed.

## Step 2: Acquire and probe the source clip

1. **YouTube source**: fetch title/duration and download a `<=720p` video-only stream covering `[start, start + duration + 4]` (4-second keyframe buffer) to a clean local filename (e.g., `<slug>.mp4`):
   ```bash
   yt-dlp -f "bv*[height<=720][ext=mp4]/b[height<=720][ext=mp4]/best[height<=720]" \
     --download-sections "*0:00-1:00" -o "<slug>.%(ext)s" "<YOUTUBE_URL>"
   ```
2. **Probe**: run `ffprobe` to record `width`, `height`, `start_time`, and `duration`.
3. **Loop check (optional, for long/1-hour MVs)**: if the clip exceeds 60s and may repeat internally, sample 1 fps frames and check mean absolute error against `t=2s` to surface natural loop boundaries before encoding large GIFs.

**Done when**: local source file exists and `ffprobe` confirms `width > 0`, `height > 0`, and `duration >= requested_duration`.

## Step 3: Implement `ascii_player.py`

Read [`RENDERING-SPEC.md`](RENDERING-SPEC.md) for the exact glyph ramp, atlas builder, BT.601 luma formula, terminal aspect-ratio math, 5D NumPy splatting, HUD/code-panel layout, and 2-pass GIF commands.

Implement `ascii_player.py` with these invariants:
- Start with `from __future__ import annotations` for Python 3.9+ compatibility.
- Resolve `ffmpeg`/`ffprobe` via `shutil.which` with fallback to `/opt/homebrew/bin` and `/usr/local/bin`.
- Stream decoded frames over `ffmpeg -f rawvideo -pix_fmt rgb24 -` one frame at a time (`O(1)` memory) for both terminal playback and `--export`.
- Support positional optional `source` defaulting to the downloaded clip with `DEFAULT_CLIP_DURATION` set to the requested range, while passing any other video or GIF works unmodified.
- Snap `--export` grid height so `(rows * CELL_H) % 2 == 0` (required by `libx264` with `yuv420p` when `CELL_H` is odd).
- Check `enc.returncode == 0` after piping frames to `ffmpeg`.

Verify in one chained command:
```bash
<PYTHON> -m py_compile ascii_player.py && \
<PYTHON> ascii_player.py --duration 0.4 --loops 1 --fps 10 | wc -c && \
<PYTHON> ascii_player.py --duration 0.5 --fps 10 --export /tmp/smoke_ascii.gif --preview /tmp/smoke_prev.png && \
rm -f /tmp/smoke_ascii.gif /tmp/smoke_prev.png
```

**Done when**: syntax check, terminal smoke test (non-zero byte count), and export smoke test all exit 0.

## Step 4: Render deliverables and verify

1. **Original GIF** (if requested): run 2-pass `ffmpeg` (`fps=10,scale=480:-1:flags=lanczos`) using the palette flags in [`RENDERING-SPEC.md`](RENDERING-SPEC.md).
2. **Colored ASCII GIF + preview PNG** (if requested): run `<PYTHON> ascii_player.py <source> --start <S> --duration <D> --fps 10 --width 600 --title "<label>" --export <out.gif> --preview <preview.png>`.
3. **Verify**:
   - Inspect `<preview.png>` visually to confirm silhouette clarity, color fidelity, and HUD/code-panel legibility.
   - Run `ls -lh` and `ffprobe` (`width,height,nb_frames,duration`) on every generated GIF to confirm exact duration and frame count.

**Done when**: every requested GIF matches the requested duration in `ffprobe`, the preview PNG is visually verified, and deliverables + CLI usage are reported to the user.
