# ascii-chiikawa

A universal **TrueColor ASCII video/GIF player** and **glowing HD ASCII GIF exporter** powered by `ffmpeg` rawvideo pipes, NumPy vectorized glyph splatting, and Pillow.

Works with any local video (`MP4`, `MOV`, `MKV`, `WEBM`) or animated `GIF`, plus an included Antigravity agent skill (`.agents/skills/ascii-video-player/`) to automate downloading a YouTube time range and converting it end-to-end.

## Prerequisites

- **FFmpeg (`ffmpeg`, `ffprobe`)** — required for video decoding and 2-pass GIF encoding
- **Python 3.9+** with `numpy` and `Pillow`
- **`yt-dlp`** — optional, only needed when downloading clips from YouTube URLs

```bash
# macOS (Homebrew)
brew install ffmpeg
brew install yt-dlp   # optional: only for YouTube URLs

# Python dependencies (if not already installed)
python3 -m pip install numpy pillow
```

## Quick Start

### 1. Play any video or GIF in the terminal (TrueColor ASCII)

```bash
python3 ascii_player.py path/to/video.mp4
python3 ascii_player.py path/to/video.mp4 --start 3 --duration 13 --fps 15
python3 ascii_player.py path/to/clip.gif --fps 12
```

Press `Ctrl+C` to exit cleanly.

> **macOS note**: If Homebrew's `python3` is first in your `PATH` and lacks `numpy`/`Pillow`, run with `/usr/bin/python3 ascii_player.py ...`.

### 2. Export a glowing HD colored ASCII GIF + preview PNG

```bash
python3 ascii_player.py path/to/video.mp4 \
  --start 3 --duration 13 --fps 10 --width 600 \
  --title "my clip · ascii" \
  --export out_ascii.gif \
  --preview out_preview.png
```

### 3. (Optional) Download a YouTube clip range first

```bash
yt-dlp -f "bv*[height<=720][ext=mp4]/b[height<=720][ext=mp4]/best[height<=720]" \
  --download-sections "*0:00-0:20" \
  -o "clip.%(ext)s" "https://youtu.be/<VIDEO_ID>"

python3 ascii_player.py clip.mp4 --start 3 --duration 13
```

## CLI Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `source` | `chiikawa_hitorigotsu.mp4` | Input video or GIF/image path (optional positional argument) |
| `--fps` | `15` | Playback or export frame rate |
| `--loops` | `0` | Terminal playback loop count (`0` = infinite) |
| `--start` | `0.0` | Start timestamp in seconds |
| `--duration` | full clip (`56.0` for default) | Clip duration in seconds |
| `--width` | `600` | Output pixel width for `--export` mode |
| `--title` | input filename stem | HUD subtitle text |
| `--export` | — | Output path for glowing HD ASCII GIF |
| `--preview` | — | Output path for still PNG snapshot (used with `--export`) |

## How It Works

```text
Any Video / GIF (MP4, MOV, WEBM, GIF)
        │
        ▼  ffmpeg -vf fps=R,scale=C:H -f rawvideo -pix_fmt rgb24 -
  Uniform RGB24 stream (1 frame = rows × cols × 3 bytes, O(1) RAM)
        │
        ▼  ITU-R BT.601 Luma (0.299R + 0.587G + 0.114B) → ASCII density ramp
        ├──▶ Terminal: ANSI 24-bit TrueColor (\033[38;2;R;G;Bm) + same-color RLE skip
        └──▶ GIF Export: NumPy 5D glyph-atlas splatting + Gaussian glow
                         → libx264 temp MP4 → FFmpeg 2-pass palettegen/paletteuse
```

## Project Layout

- `ascii_player.py` — CLI entry point and live TrueColor terminal player
- `ascii_exporter.py` — Glyph atlas builder, vectorized 5D renderer, and 2-pass GIF exporter
- `.agents/skills/ascii-video-player/` — Reusable agent skill (`SKILL.md` + `RENDERING-SPEC.md`)

## Agent Skill Usage

Clone this repository and invoke the workspace skill in Antigravity:

```text
/ascii-video-player <YOUTUBE_URL_OR_LOCAL_VIDEO> from 3s to 16s
```
