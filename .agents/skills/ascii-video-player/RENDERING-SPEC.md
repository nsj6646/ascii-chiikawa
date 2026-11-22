# Rendering & Encoding Reference for `ascii_player.py`

Consult this specification when implementing Step 3 or Step 4 of [`SKILL.md`](SKILL.md).

## 1. Glyph Ramp, Atlas & Fonts

- **Density ramp** (darkest → brightest): `GLYPHS = " .,:;irsXA253hMHGS#9B&@"` (`23` glyphs)
- **Cell size**: `CELL_W = 4`, `CELL_H = 5` (pixel size of each rendered glyph in GIF export)
- **macOS monospace font search order**:
  1. `/System/Library/Fonts/SFNSMono.ttf`
  2. `/System/Library/Fonts/Menlo.ttc`
  3. `/System/Library/Fonts/Monaco.ttf`
  4. `/System/Library/Fonts/Supplemental/Courier New Bold.ttf`
  5. Fallback: `ImageFont.load_default()`
- **HUD character caveat**: `SFNSMono.ttf` lacks musical note glyphs (`♪`); use ASCII `~` or `*` in PIL-drawn HUD text.
- **Glyph atlas (`build_glyph_atlas`)**: render each non-space glyph at `4x` supersampling (`cell_w * 4`, `cell_h * 4`) using font size `cell_h * 4` so glyphs fill the cell, downsample with `BILINEAR` to `(cell_h, cell_w)`, normalize by `arr.max()`, and scale by `1.15` clipped to `[0.0, 1.0]`. Result shape: `(len(GLYPHS), CELL_H, CELL_W)` `float32`.

## 2. Luma Mapping & Terminal Aspect Ratio

- **ITU-R BT.601 luma**:
  ```python
  lum = (0.299 * grgb[..., 0] + 0.587 * grgb[..., 1] + 0.114 * grgb[..., 2]) / 255.0
  gi = np.clip((lum * (len(GLYPHS) - 1)).astype(np.int32), 0, len(GLYPHS) - 1)
  ```
- **Terminal grid fitting**: monospace cells are ~2x taller than wide (`char_aspect = 0.5`):
  ```python
  avail_cols = max(32, term_cols)
  avail_rows = max(12, term_rows - 3)
  cols = avail_cols
  rows = int(round(cols * (src_h / src_w) * 0.5))
  if rows > avail_rows:
      rows = avail_rows
      cols = int(round(rows * (src_w / src_h) / 0.5))
  ```
- **Terminal TrueColor ANSI + RLE optimization**:
  - Emit `\033[38;2;{r};{g};{b}m{ch}` only when `(r, g, b)` differs from the previous cell in the same row; emit raw `{ch}` when unchanged.
  - Spawn `ffmpeg` with `stdin=subprocess.DEVNULL`, `stderr=subprocess.DEVNULL`, and `start_new_session=True`. On teardown (`finally`), close `dec.stdout` before `dec.terminate()`, wait with a short timeout (`kill` fallback), and always restore cursor + reset (`\033[?25h\033[0m\n`) so `Ctrl+C` exits silently with zero `Broken pipe` noise or hidden cursor.

## 3. Vectorized 5D Glyph Splatting & Bloom Glow (GIF Export)

```python
def letters_to_pixels(gi: np.ndarray, grgb: np.ndarray, atlas: np.ndarray) -> np.ndarray:
    rows, cols = gi.shape
    ch, cw = atlas.shape[1], atlas.shape[2]
    m = atlas[gi]                                        # (rows, cols, ch, cw)
    img = m[..., None] * grgb[:, :, None, None, :]       # (rows, cols, ch, cw, 3)
    img = img.transpose(0, 2, 1, 3, 4).reshape(rows * ch, cols * cw, 3)
    base = np.clip(img, 0, 255).astype(np.uint8)
    glow = np.asarray(
        Image.fromarray(base).filter(ImageFilter.GaussianBlur(radius=1.5)),
        dtype=np.float32,
    )
    return np.clip(base.astype(np.float32) + 0.58 * glow, 0, 255).astype(np.uint8)
```

## 4. Export Canvas Layout & Even-Height Constraint

- `cols = max(60, out_width // CELL_W)`, `art_w = cols * CELL_W`
- `rows = max(30, int(round(art_w * (src_h / src_w) / CELL_H)))`
- Even-height snap for `libx264` (`yuv420p`): `if (rows * CELL_H) % 2 != 0: rows += 1`
- `hud_h = 72` (even), `code_h = 156` (even), `total_h = hud_h + rows * CELL_H + code_h`
- Background fill: `(7, 9, 13)`; bottom code panel fill: `(14, 18, 26)` with highlighted active line rotating at `int(t * 3.0) % len(CODE_SNIPPET)`.

## 5. FFmpeg Streaming & 2-Pass Palette GIF Commands

- **Decoder pipe** (streams `cols * rows * 3` bytes/frame):
  ```bash
  ffmpeg -v error -ss <START> -t <DURATION> -i <SOURCE> \
    -vf "fps=<FPS>,scale=<COLS>:<ROWS>:flags=bilinear" \
    -f rawvideo -pix_fmt rgb24 -
  ```
- **Intermediate lossless-ish MP4 pipe** (inside `tempfile.TemporaryDirectory()`):
  ```bash
  ffmpeg -y -v error -f rawvideo -pix_fmt rgb24 -s <W>x<H> -r <FPS> -i - \
    -c:v libx264 -preset ultrafast -crf 16 -pix_fmt yuv420p ascii_tmp.mp4
  ```
- **2-pass GIF quantization** (for both original GIF and ASCII GIF):
  ```bash
  ffmpeg -y -v error -i ascii_tmp.mp4 -vf "palettegen=stats_mode=diff" palette.png
  ffmpeg -y -v error -i ascii_tmp.mp4 -i palette.png \
    -lavfi "paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" out.gif
  ```
- **Practical defaults for ~30–120s clips**: `fps=10`, original GIF width `480px`, ASCII GIF width `600px` (`~10,200` letters/frame on 16:9).
