#!/bin/bash
# abrain 사전 설치 스크립트 (macOS + Homebrew)
# 여러 번 실행해도 안전하다. 이미 설치된 것은 건너뛴다.
#
#   ./INSTALL.sh                  기본 설치. 음성 인식 모델은 받을지 묻는다 (기본: 받지 않음)
#   ./INSTALL.sh --codex-rules    설치된 MLX의 Codex 전역 허용 규칙만 설정한다
#   ./INSTALL.sh --models         음성 인식 모델만 받는다 (나중에 회의 녹음을 전사할 때)
#   ./INSTALL.sh --check-models   음성 인식 모델이 있는지 확인만 한다 (있으면 0, 없으면 1로 끝남)
#
# 설치하는 것
#   brew   : uv, ffmpeg, poppler, yt-dlp
#   uv tool: markitdown (docx/pptx/xlsx/pdf/html → 마크다운)
#            pyhwp (hwp → html)
#            mlx-whisper (음성·영상 → 텍스트, Apple Silicon GPU)
#            whisper-ctranslate2 (음성·영상 → 텍스트, CPU. 예비용)
#   모델   : (선택) Whisper large-v3 (MLX, 약 3GB) + large-v3-turbo (CPU, 약 1.6GB)
#   설정   : .codex/config.toml (Codex 샌드박스 네트워크 허용)
#            ${CODEX_HOME:-~/.codex}/rules/abrain-mlx-whisper.rules (전역 MLX 실행 허용)
#   폴더   : raw/, wiki/ 와 빈 index·log·용어집 (없을 때만 만든다. 기존 내용은 건드리지 않는다)

set -uo pipefail

PY=3.11                     # 모든 도구를 이 버전에서 확인했다
# 음성 인식은 두 가지를 설치한다.
#  - mlx-whisper + large-v3 : 한국어 대화체 정확도가 가장 좋고 GPU로 빠르다 (실시간의 약 11배).
#  - whisper-ctranslate2 + large-v3-turbo : CPU 전용 (약 4.7배).
#    MLX를 샌드박스 밖에서도 실행할 수 없을 때와 Intel 맥에서 쓰는 예비 경로다.
MLX_MODEL=mlx-community/whisper-large-v3-mlx
CPU_MODEL=large-v3-turbo
CPU_MODEL_REPO=mobiuslabsgmbh/faster-whisper-large-v3-turbo   # faster-whisper가 large-v3-turbo를 받는 저장소
HF_CACHE="${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}"
ARCH="$(uname -m)"
ROOT="$(cd "$(dirname "$0")" && pwd)"
FAILED=""

say()  { printf "\n\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$1"; FAILED="$FAILED\n  - $1"; }

# ── 음성 인식 모델 확인 ──────────────────────────────────────
# Hugging Face 캐시에 모델 스냅샷이 있는지 본다. 네트워크를 쓰지 않는다.
model_cached() {  # model_cached <저장소 이름>
  local dir="$HF_CACHE/models--${1//\//--}/snapshots"
  [ -d "$dir" ] && [ -n "$(ls -A "$dir" 2>/dev/null)" ]
}
models_ready() {
  model_cached "$CPU_MODEL_REPO" || return 1
  if [ "$ARCH" = "arm64" ]; then model_cached "$MLX_MODEL" || return 1; fi
  return 0
}
print_model_status() {
  if [ "$ARCH" = "arm64" ]; then
    if model_cached "$MLX_MODEL"; then ok "large-v3 (MLX)"; else warn "large-v3 (MLX) 없음"; fi
  fi
  if model_cached "$CPU_MODEL_REPO"; then ok "$CPU_MODEL (CPU)"; else warn "$CPU_MODEL (CPU) 없음"; fi
}
MODELS_HINT="음성·영상 전사가 필요할 때 ./INSTALL.sh --models 로 모델(약 4.6GB)을 받으세요."

if [ "${1:-}" = "--check-models" ]; then
  print_model_status
  if models_ready; then exit 0; fi
  printf "\n  %s\n" "$MODELS_HINT"
  exit 1
fi

install_brew() {  # install_brew <패키지...>
  local pkg
  for pkg in "$@"; do
    if brew list --formula "$pkg" >/dev/null 2>&1; then
      ok "$pkg (이미 설치됨)"
    elif brew install "$pkg"; then
      ok "$pkg"
    else
      fail "brew install $pkg"
    fi
  done
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv 설치에 실패해 계속할 수 없습니다."; exit 1
  fi
}

# uvx로 매번 내려받지 않고 미리 설치해 둔다.
# Codex 샌드박스는 uv 캐시 폴더에 쓸 수 없어서 uvx가 실패하기 때문이다.
install_tool() {  # install_tool <표시 이름> <uv tool install 인자...>
  local name="$1"; shift
  if uv tool install --quiet --python "$PY" "$@"; then
    ok "$name"
  else
    fail "uv tool install $name"
  fi
}
install_whisper_tools() {
  install_tool whisper-ctranslate2  whisper-ctranslate2
  if [ "$ARCH" = "arm64" ]; then
    install_tool mlx-whisper        mlx-whisper
  else
    warn "Intel 맥이라 mlx-whisper는 건너뜁니다. 음성 전사는 CPU로 동작합니다."
  fi
}

# uv tool 실행 파일 폴더(~/.local/bin)가 PATH에 없으면 셸 설정에 추가한다.
ensure_tool_path() {
  local bin
  bin="$(uv tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"
  case ":$PATH:" in
    *":$bin:"*) ;;
    *)
      uv tool update-shell >/dev/null 2>&1
      export PATH="$bin:$PATH"
      warn "PATH에 $bin 을 추가했습니다. 터미널을 새로 열어야 적용됩니다."
      ;;
  esac
}

# 정확히 이 MLX 실행 파일만 허용한다. 다른 규칙과 전역 config.toml은 수정하지 않는다.
# 인자는 격리된 설치 검증에서도 사용할 수 있다.
install_codex_rules() {
  local config_home="${1:-${CODEX_HOME:-$HOME/.codex}}"
  local mlx bin escaped rules_dir target tmp backup
  if [ "$ARCH" != "arm64" ]; then
    ok "Intel 맥: Codex MLX 규칙은 건너뜁니다."
    return
  fi
  mlx="$(command -v mlx_whisper 2>/dev/null || true)"
  if [ -z "$mlx" ] && command -v uv >/dev/null 2>&1; then
    bin="$(uv tool dir --bin 2>/dev/null || true)"
    if [ -n "$bin" ] && [ -x "$bin/mlx_whisper" ]; then mlx="$bin/mlx_whisper"; fi
  fi
  if [ -z "$mlx" ] || [ ! -f "$mlx" ] || [ ! -x "$mlx" ]; then
    fail "mlx_whisper 실행 파일을 찾지 못했습니다. ./INSTALL.sh 로 먼저 설치하세요."
    return
  fi
  # 상대 PATH 항목도 절대 경로로 바꾸되 uv의 실행 파일 링크는 유지한다.
  case "$mlx" in
    /*) ;;
    *) mlx="$(cd "$(dirname "$mlx")" && pwd)/$(basename "$mlx")" ;;
  esac
  escaped="${mlx//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  escaped="${escaped//$'\n'/\\n}"
  escaped="${escaped//$'\r'/\\r}"
  escaped="${escaped//$'\t'/\\t}"
  rules_dir="$config_home/rules"
  target="$rules_dir/abrain-mlx-whisper.rules"
  if ! mkdir -p "$rules_dir"; then fail "Codex 규칙 폴더 생성: $rules_dir"; return; fi
  if [ -L "$target" ]; then fail "심볼릭 링크인 규칙 파일은 수정하지 않습니다: $target"; return; fi
  tmp="$(mktemp "$rules_dir/.abrain-mlx-whisper.XXXXXX")" || { fail "Codex 규칙 임시 파일 생성"; return; }
  if ! cat > "$tmp" <<EOF
# Managed by abrain INSTALL.sh. Re-run --codex-rules after moving mlx_whisper.
# This global rule allows only the named executable outside the sandbox.
prefix_rule(
    pattern = ["$escaped"],
    decision = "allow",
    justification = "Local audio transcription requires Metal GPU access",
)
EOF
  then
    rm -f "$tmp"; fail "Codex 규칙 작성"; return
  fi
  if [ -f "$target" ] && cmp -s "$tmp" "$target"; then
    rm -f "$tmp"
    ok "Codex MLX 전역 규칙 (이미 설정됨): $mlx"
    return
  fi
  if [ -e "$target" ]; then
    backup="$(mktemp "$rules_dir/abrain-mlx-whisper.backup.XXXXXX")" || { rm -f "$tmp"; fail "규칙 백업 생성"; return; }
    if ! cp -p "$target" "$backup"; then rm -f "$tmp" "$backup"; fail "규칙 백업 실패"; return; fi
    warn "기존 MLX 규칙 백업: $backup"
  fi
  if ! mv -f "$tmp" "$target"; then rm -f "$tmp"; fail "Codex 규칙 설치"; return; fi
  ok "Codex MLX 전역 규칙: $target → $mlx"
  warn "모든 Codex 프로젝트에 적용됩니다. Codex를 재시작하세요. 상위 관리 정책은 계속 적용됩니다."
}

# 1초짜리 무음 파일을 전사해 모델을 캐시에 받아 둔다. 처음에는 몇 분 걸린다.
download_models() {
  local tmp
  tmp="$(mktemp -d)"
  TMP_DIR="$tmp"
  trap 'rm -rf "$TMP_DIR"' EXIT
  if ! ffmpeg -loglevel error -f lavfi -i anullsrc=r=16000:cl=mono -t 1 "$tmp/silence.wav"; then
    fail "ffmpeg 로 시험 파일 만들기"
    return
  fi
  if [ "$ARCH" = "arm64" ]; then
    if model_cached "$MLX_MODEL"; then
      ok "large-v3 (MLX, 이미 있음)"
    elif mlx_whisper "$tmp/silence.wav" --model "$MLX_MODEL" --language ko \
           -f txt --output-dir "$tmp" >/dev/null 2>&1; then
      ok "large-v3 (MLX)"
    else
      fail "mlx-whisper 모델 내려받기 ($MLX_MODEL)"
    fi
  fi
  if model_cached "$CPU_MODEL_REPO"; then
    ok "$CPU_MODEL (CPU, 이미 있음)"
  elif whisper-ctranslate2 "$tmp/silence.wav" --model "$CPU_MODEL" --language ko \
         --output_dir "$tmp" --output_format txt >/dev/null 2>&1; then
    ok "$CPU_MODEL (CPU)"
  else
    fail "whisper-ctranslate2 모델 내려받기 ($CPU_MODEL)"
  fi
}

finish() {  # finish <성공 메시지>
  if [ -n "$FAILED" ]; then
    printf "\n\033[31m실패한 항목:\033[0m$FAILED\n\n위 항목을 해결한 뒤 다시 실행하세요.\n"
    exit 1
  fi
  printf "\n\033[32m%s\033[0m\n" "$1"
  exit 0
}

# 규칙만 설정할 때는 Homebrew나 모델 다운로드가 필요 없다.
if [ "${1:-}" = "--codex-rules" ]; then
  install_codex_rules
  finish "Codex MLX 허용 규칙 설정을 마쳤습니다."
fi

# ── 0. 환경 확인 ─────────────────────────────────────────────
if [ "$(uname -s)" != "Darwin" ]; then
  echo "이 스크립트는 macOS 전용입니다."; exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew가 필요합니다: https://brew.sh"; exit 1
fi

# ── 모델만 받기 (--models) ───────────────────────────────────
if [ "${1:-}" = "--models" ]; then
  say "1/2 음성 인식 도구"
  install_brew uv ffmpeg
  install_whisper_tools
  ensure_tool_path
  install_codex_rules
  say "2/2 음성 인식 모델 (약 4.6GB, 처음에는 몇 분 걸립니다)"
  download_models
  finish "음성 인식 모델을 받았습니다. 이제 음성·영상 파일을 ingest 할 수 있습니다."
fi

if [ -n "${1:-}" ]; then
  echo "알 수 없는 옵션: $1"
  echo "사용법: ./INSTALL.sh [--models | --check-models | --codex-rules]"
  exit 1
fi

# ── 1. Homebrew 패키지 ───────────────────────────────────────
say "1/6 Homebrew 패키지"
install_brew uv ffmpeg poppler yt-dlp

# ── 2. 변환 도구 (uv tool) ───────────────────────────────────
say "2/6 변환 도구"
install_tool markitdown           'markitdown[all]'
install_tool pyhwp                pyhwp --with six
install_whisper_tools
ensure_tool_path
install_codex_rules

# ── 3. 음성 인식 모델 (선택) ─────────────────────────────────
say "3/6 음성 인식 모델 (선택)"
if models_ready; then
  print_model_status
else
  ANSWER=""
  if [ -t 0 ]; then
    printf "  음성·영상 전사에 쓰는 모델(약 4.6GB)을 지금 받을까요? 나중에 받아도 됩니다. [y/N] "
    read -r ANSWER || ANSWER=""
  fi
  case "$ANSWER" in
    [yY]|[yY][eE][sS]) download_models ;;
    *) warn "건너뜁니다. $MODELS_HINT" ;;
  esac
fi

# ── 4. Codex 샌드박스 설정 ───────────────────────────────────
# Codex는 기본 샌드박스에서 네트워크를 막는다. 그러면 YouTube, 웹 URL,
# Google Drive 내보내기 파일을 받을 수 없다. 이 폴더에만 적용되는 설정 파일로
# 네트워크를 허용한다. 개인 전역 설정(~/.codex/config.toml)은 건드리지 않는다.
say "4/6 Codex 샌드박스 설정"
CODEX_CFG="$ROOT/.codex/config.toml"
if [ ! -f "$CODEX_CFG" ]; then
  mkdir -p "$ROOT/.codex"
  cat > "$CODEX_CFG" <<'EOF'
# abrain용 Codex 설정. 이 폴더에서 실행할 때만 적용된다.
# workspace-write 샌드박스 안에서 네트워크를 허용한다.
[sandbox_workspace_write]
network_access = true
EOF
  ok ".codex/config.toml 생성 (샌드박스 네트워크 허용)"
elif grep -Eq '^[[:space:]]*network_access[[:space:]]*=[[:space:]]*true' "$CODEX_CFG"; then
  ok ".codex/config.toml (이미 설정됨)"
else
  warn ".codex/config.toml 이 이미 있지만 network_access = true 가 없습니다. 직접 추가하세요:"
  printf "      [sandbox_workspace_write]\n      network_access = true\n"
fi

# ── 5. 위키 폴더 ─────────────────────────────────────────────
# raw/ 와 wiki/ 는 개인 데이터라 저장소에 올리지 않는다 (.gitignore).
# 그래서 빈 뼈대를 여기서 만든다. 이미 있는 파일은 건드리지 않는다.
say "5/6 위키 폴더"
mkdir -p "$ROOT/raw/assets" "$ROOT/raw/_extracted" \
         "$ROOT/wiki/sources" "$ROOT/wiki/decisions" "$ROOT/wiki/people" \
         "$ROOT/wiki/projects" "$ROOT/wiki/topics"
seed() {  # seed <경로> <내용>  — 파일이 없을 때만 만든다
  if [ -f "$1" ]; then return; fi
  printf "%b" "$2" > "$1"
}
seed "$ROOT/wiki/index.md"  "# Index\n\n## Decisions\n\n## Projects\n\n## People\n\n## Topics\n\n## Sources\n"
seed "$ROOT/wiki/log.md"    "# Log\n"
seed "$ROOT/wiki/용어집.md" "# 용어집\n\n확정된 표기를 기록한다. 틀린 표기가 원본에 나오면 묻지 않고 확정 표기로 바꿔 쓴다.\n\n| 확정 표기 | 틀린 표기·변형 | 뜻 |\n|---|---|---|\n"
if [ -d "$ROOT/wiki/sources" ] && [ -f "$ROOT/wiki/index.md" ]; then
  ok "raw/, wiki/ 준비됨"
else
  fail "위키 폴더 만들기"
fi

# ── 6. 확인 ──────────────────────────────────────────────────
say "6/6 설치 확인"
CMDS="uv ffmpeg pdftotext pdftoppm yt-dlp markitdown hwp5html whisper-ctranslate2 textutil unzip curl"
[ "$ARCH" = "arm64" ] && CMDS="$CMDS mlx_whisper"
for cmd in $CMDS; do
  if command -v "$cmd" >/dev/null 2>&1; then ok "$cmd"; else fail "$cmd 명령을 찾을 수 없음"; fi
done
models_ready || warn "음성 인식 모델 없음 (선택). $MODELS_HINT"

AGENT=""
command -v claude >/dev/null 2>&1 && { ok "claude (Claude Code)"; AGENT=1; }
command -v codex  >/dev/null 2>&1 && { ok "codex (Codex CLI)";   AGENT=1; }
[ -z "$AGENT" ] && warn "claude 또는 codex 가 없습니다. 둘 중 하나를 설치하세요."

finish "설치가 끝났습니다. 이 폴더에서 claude 또는 codex 를 실행하고, 처음 한 번 \"온보딩\"이라고 말하세요."
