#!/bin/bash
# 마지막 lint 이후 며칠이 지났는지 확인한다. 읽기만 한다.
#
#   lint-due.sh          사람용 한 줄 출력. 7일 이상이면 종료 코드 1, 아니면 0.
#   lint-due.sh --hook   Claude Code SessionStart 훅용. 7일 이상일 때만 JSON을 출력한다. 항상 0으로 끝난다.
#
# 기준: wiki/log.md 의 마지막 "## [YYYY-MM-DD] lint" 항목.
# lint 기록이 없으면 첫 log 항목 날짜를 기준으로 한다. log 항목이 하나도 없으면(빈 위키) 권고하지 않는다.

set -uo pipefail

DAYS_LIMIT=7
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
LOG="$ROOT/wiki/log.md"
MODE="${1:-}"

entry_date() {  # entry_date <grep 패턴> <head|tail>
  grep -E "$1" "$LOG" 2>/dev/null | "$2" -1 | sed -E 's/^## \[([0-9]{4}-[0-9]{2}-[0-9]{2})\].*/\1/'
}

LAST_LINT="$(entry_date '^## \[[0-9]{4}-[0-9]{2}-[0-9]{2}\] lint' tail)"
if [ -n "$LAST_LINT" ]; then
  BASE="$LAST_LINT"; WHAT="마지막 lint"
else
  BASE="$(entry_date '^## \[[0-9]{4}-[0-9]{2}-[0-9]{2}\]' head)"; WHAT="첫 작업 (lint 기록 없음)"
fi

if [ -z "$BASE" ]; then
  [ "$MODE" = "--hook" ] || echo "위키 작업 기록이 없어 lint가 필요하지 않습니다."
  exit 0
fi

BASE_TS="$(date -j -f %Y-%m-%d "$BASE" +%s 2>/dev/null)" || BASE_TS=""
if [ -z "$BASE_TS" ]; then
  [ "$MODE" = "--hook" ] || echo "log.md 날짜를 읽지 못했습니다: $BASE"
  exit 0
fi
TODAY_TS="$(date -j -f %Y-%m-%d "$(date +%Y-%m-%d)" +%s)"
DAYS=$(( (TODAY_TS - BASE_TS) / 86400 ))

MSG="abrain: ${WHAT} ${BASE}, ${DAYS}일 지났습니다. 주 1회 점검을 권합니다: /abrain:lint 또는 \"lint\""

if [ "$MODE" = "--hook" ]; then
  if [ "$DAYS" -ge "$DAYS_LIMIT" ]; then
    CTX="abrain lint 권고: ${WHAT} ${BASE} (${DAYS}일 전). 사용자는 시작 메시지로 이미 알림을 보았다. 이번 세션에서 ingest나 query 보고를 마칠 때 한 줄로 한 번만 다시 권한다."
    printf '{"systemMessage": "%s", "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "%s"}}\n' \
      "$(printf '%s' "$MSG" | sed 's/"/\\"/g')" "$(printf '%s' "$CTX" | sed 's/"/\\"/g')"
  fi
  exit 0
fi

if [ "$DAYS" -ge "$DAYS_LIMIT" ]; then
  echo "$MSG"; exit 1
fi
echo "abrain: ${WHAT} ${BASE}, ${DAYS}일 전. 점검이 아직 필요하지 않습니다."
exit 0
