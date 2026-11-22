# ascii-chiikawa

> [English](README.md) | **한국어**

`ffmpeg` rawvideo 파이프, NumPy 벡터화 글리프 스플래팅, Pillow를 활용한 범용 **TrueColor 컬러 ASCII 영상/GIF 플레이어** 및 **글로우 HD ASCII GIF 변환기**입니다.

로컬 영상(`MP4`, `MOV`, `MKV`, `WEBM`)이나 애니메이션 `GIF`를 포맷 구분 없이 처리하며, 유튜브 링크에서 원하는 구간만 잘라 `ascii_player.py` 및 ASCII GIF로 자동 변환하는 Antigravity 에이전트 스킬(`.agents/skills/ascii-video-player/`)이 포함되어 있습니다.

## 사전 요구사항

- **FFmpeg (`ffmpeg`, `ffprobe`)** — 영상 디코딩 및 2-pass GIF 인코딩에 필수
- **Python 3.9+** (`numpy`, `Pillow` 설치 필요)
- **`yt-dlp`** — 선택 사항 (유튜브 URL에서 직접 다운로드할 때만 필요)

```bash
# macOS (Homebrew)
brew install ffmpeg
brew install yt-dlp   # 선택: 유튜브 링크 다운로드 시에만 필요

# Python 패키지 (미설치 시)
python3 -m pip install numpy pillow
```

## 빠른 시작

### 1. 터미널에서 영상/GIF 실시간 재생 (TrueColor ASCII)

```bash
python3 ascii_player.py path/to/video.mp4
python3 ascii_player.py path/to/video.mp4 --start 3 --duration 13 --fps 15
python3 ascii_player.py path/to/clip.gif --fps 12
```

`Ctrl+C`로 깔끔하게 종료할 수 있습니다.

> **macOS 참고**: Homebrew의 `python3`가 `PATH` 우선순위에 있어 `No module named 'numpy'`가 발생한다면 `/usr/bin/python3 ascii_player.py ...`로 실행하세요.

### 2. 글로우 HD 컬러 ASCII GIF + 프리뷰 PNG 내보내기

```bash
python3 ascii_player.py path/to/video.mp4 \
  --start 3 --duration 13 --fps 10 --width 600 \
  --title "my clip · ascii" \
  --export out_ascii.gif \
  --preview out_preview.png
```

### 3. (선택) 유튜브 링크에서 특정 구간만 다운로드

```bash
yt-dlp -f "bv*[height<=720][ext=mp4]/b[height<=720][ext=mp4]/best[height<=720]" \
  --download-sections "*0:00-0:20" \
  -o "clip.%(ext)s" "https://youtu.be/<VIDEO_ID>"

python3 ascii_player.py clip.mp4 --start 3 --duration 13
```

## CLI 옵션

| 옵션 | 기본값 | 설명 |
| :--- | :--- | :--- |
| `source` | `chiikawa_hitorigotsu.mp4` | 입력 영상 또는 GIF/이미지 경로 (선택적 위치 인자) |
| `--fps` | `15` | 재생 또는 내보내기 FPS |
| `--loops` | `0` | 터미널 반복 재생 횟수 (`0` = 무한 반복) |
| `--start` | `0.0` | 시작 시간(초) |
| `--duration` | 전체 길이 (기본 클립 `56.0`) | 재생/변환 구간 길이(초) |
| `--width` | `600` | `--export` 모드 출력 가로 해상도(px) |
| `--title` | 입력 파일명 | 상단 HUD 서브타이틀 문구 |
| `--export` | — | 글로우 HD ASCII GIF 저장 경로 |
| `--preview` | — | 스틸 미리보기 PNG 저장 경로 (`--export`와 함께 사용) |

## 동작 원리

```text
임의의 영상 / GIF (MP4, MOV, WEBM, GIF)
        │
        ▼  ffmpeg -vf fps=R,scale=C:H -f rawvideo -pix_fmt rgb24 -
  균일한 RGB24 바이트 스트림 (1프레임 = rows × cols × 3 bytes, O(1) 메모리)
        │
        ▼  ITU-R BT.601 루마 (0.299R + 0.587G + 0.114B) → ASCII 밀도 문자열 매핑
        ├──▶ 터미널: ANSI 24-bit TrueColor (\033[38;2;R;G;Bm) + 연속 동일색 RLE 생략
        └──▶ GIF 내보내기: NumPy 5D 글리프 아틀라스 스플래팅 + 가우시안 블룸
                           → libx264 임시 MP4 → FFmpeg 2-pass palettegen/paletteuse
```

## 프로젝트 구조

- `ascii_player.py` — CLI 진입점 및 터미널 실시간 TrueColor ASCII 플레이어
- `ascii_exporter.py` — 글리프 아틀라스 빌더, NumPy 5D 벡터 렌더러, 2-pass GIF 변환기
- `.agents/skills/ascii-video-player/` — 재사용 가능한 에이전트 스킬 (`SKILL.md`, `RENDERING-SPEC.md`)

## 에이전트 스킬 사용법

이 저장소를 클론한 뒤 Antigravity에서 워크스페이스 스킬을 호출할 수 있습니다.

```text
/ascii-video-player <유튜브_URL_또는_로컬_영상> 3초부터 16초까지
```
