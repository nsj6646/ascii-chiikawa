# ascii-chiikawa

> [English](README.md) | **한국어**

유튜브 링크나 로컬 영상/GIF를 **터미널 TrueColor 컬러 ASCII 애니메이션**과 **글로우 HD ASCII GIF**로 바꿔주는 도구입니다. 스킬을 내려받고 에이전트에게 프롬프트 한 줄만 보내면 끝납니다.

## Install

`SKILL.md`에 모든 사전 요구사항(`ffmpeg`, `yt-dlp`, `numpy`, `Pillow`) 확인 및 설치 가이드가 포함되어 있어, 에이전트가 환경 준비부터 변환까지 자동으로 처리합니다.

### 1. 스킬 다운로드

```bash
git clone https://github.com/nsj6646/ascii-chiikawa.git
cd ascii-chiikawa
```

*(또는 `.agents/skills/ascii-video-player/` 폴더만 본인 프로젝트의 `.agents/skills/`나 전역 스킬 폴더로 복사해서 사용할 수 있습니다.)*

### 2. 에이전트에게 프롬프트 전송

```text
/ascii-video-player https://youtu.be/<VIDEO_ID> 3초부터 16초까지
```

의존성 확인, 영상 구간 다운로드, `ascii_player.py` 실행 및 원본·컬러 ASCII GIF 생성까지 자동으로 완료됩니다.

---

## 직접 CLI로 실행하기 (에이전트 없이)

직접 실행하려면 `ffmpeg`(`ffprobe`)과 Python 3.9+(`numpy`, `Pillow`)가 필요합니다. (`yt-dlp`는 유튜브 URL을 받을 때만 필요)

```bash
# 터미널에서 영상/GIF 실시간 재생 (Ctrl+C로 종료)
python3 ascii_player.py path/to/video.mp4 --start 3 --duration 13 --fps 15
python3 ascii_player.py path/to/clip.gif --fps 12

# 글로우 HD 컬러 ASCII GIF + 프리뷰 PNG 내보내기
python3 ascii_player.py path/to/video.mp4 \
  --start 3 --duration 13 --fps 10 --width 600 \
  --title "my clip · ascii" \
  --export out_ascii.gif \
  --preview out_preview.png
```

> **macOS 참고**: Homebrew `python3`에 `numpy`/`Pillow`가 없다면 `/usr/bin/python3 ascii_player.py ...`로 실행하세요.

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

- `.agents/skills/ascii-video-player/` — 재사용 가능한 에이전트 스킬 (`SKILL.md`, `RENDERING-SPEC.md`)
- `ascii_player.py` — CLI 진입점 및 터미널 실시간 TrueColor ASCII 플레이어
- `ascii_exporter.py` — 글리프 아틀라스 빌더, NumPy 5D 벡터 렌더러, 2-pass GIF 변환기
