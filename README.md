# ascii-chiikawa

> **English** | [한국어](README.ko.md)

Turn any YouTube clip or local video/GIF into a **TrueColor terminal ASCII animation** and a **glowing HD colored ASCII GIF**—just install the skill and send a prompt to your agent.

## Install

`SKILL.md` guides your agent to check and install all prerequisites (`ffmpeg`, `yt-dlp`, `numpy`, `Pillow`) automatically.

### 1. Get the skill

```bash
git clone https://github.com/nsj6646/ascii-chiikawa.git
cd ascii-chiikawa
```

*(Or copy `.agents/skills/ascii-video-player/` into your own project's `.agents/skills/` or global skills directory.)*

### 2. Prompt your agent

```text
/ascii-video-player https://youtu.be/<VIDEO_ID> from 3s to 16s
```

That's it—the agent handles dependency checks, clip download, `ascii_player.py` setup, and original + colored ASCII GIF export.

---

## Manual CLI Usage (without an agent)

If you want to run `ascii_player.py` directly, make sure `ffmpeg` (`ffprobe`) and Python 3.9+ (`numpy`, `Pillow`) are installed (`yt-dlp` is only needed for YouTube URLs):

```bash
# Play any video or GIF in the terminal (Ctrl+C to exit)
python3 ascii_player.py path/to/video.mp4 --start 3 --duration 13 --fps 15
python3 ascii_player.py path/to/clip.gif --fps 12

# Export a glowing HD colored ASCII GIF + preview PNG
python3 ascii_player.py path/to/video.mp4 \
  --start 3 --duration 13 --fps 10 --width 600 \
  --title "my clip · ascii" \
  --export out_ascii.gif \
  --preview out_preview.png
```

> **macOS note**: If Homebrew's `python3` lacks `numpy`/`Pillow`, run `/usr/bin/python3 ascii_player.py ...`.

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

- `.agents/skills/ascii-video-player/` — Reusable agent skill (`SKILL.md`, `RENDERING-SPEC.md`)
- `ascii_player.py` — CLI entry point and live TrueColor terminal player
- `ascii_exporter.py` — Glyph atlas builder, vectorized 5D renderer, and 2-pass GIF exporter
