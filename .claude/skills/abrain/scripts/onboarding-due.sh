#!/bin/bash
# 온보딩(wiki/프로필.md)을 했는지 확인한다. 읽기만 한다.
#
#   onboarding-due.sh          사람용 한 줄 출력. 온보딩 전이면 종료 코드 1, 아니면 0.
#   onboarding-due.sh --hook   Claude Code SessionStart 훅용. 온보딩 전일 때만 JSON을 출력한다. 항상 0으로 끝난다.
#
# wiki/ 가 없으면(INSTALL.sh 전) 권고하지 않는다.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
MODE="${1:-}"

if [ ! -d "$ROOT/wiki" ] || [ -f "$ROOT/wiki/프로필.md" ]; then
  [ "$MODE" = "--hook" ] || echo "abrain: 온보딩이 필요하지 않습니다."
  exit 0
fi

MSG="abrain: 아직 온보딩 전입니다. /abrain:onboarding 또는 \"온보딩\"으로 기본 정보를 등록하면 자료를 더 정확히 정리합니다."

if [ "$MODE" = "--hook" ]; then
  CTX="abrain 온보딩 전: wiki/프로필.md가 없다. 사용자는 시작 메시지로 알림을 보았다. 사용자가 다른 작업을 요청하면 그 작업을 먼저 하고, 보고 끝에 한 줄로 한 번만 온보딩을 권한다."
  printf '{"systemMessage": "%s", "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "%s"}}\n' \
    "$(printf '%s' "$MSG" | sed 's/"/\\"/g')" "$(printf '%s' "$CTX" | sed 's/"/\\"/g')"
  exit 0
fi

echo "$MSG"
exit 1
