---
name: abrain-lint
description: abrain 위키를 점검하고 교정한다. 깨진 링크, index 누락, 중복 페이지, 모순, 낡은 서술, 출처 없는 서술, 기한 지난 할 일, 오래된 pending 결정, 미확인 용어·화자, 미처리 원본을 찾아 기계적인 것은 고치고 판단이 필요한 것은 보고한다. 주 1회 실행을 권한다. 사용자가 "lint", "점검해줘", "위키 점검", "정리 상태 확인", "health check"라고 할 때 쓴다.
---

# abrain-lint (Codex)

이 스킬의 본문은 Claude Code와 같이 쓴다. `.claude/skills/abrain/skills/lint/SKILL.md`를 읽고 그대로 실행한다.

- 그 문서의 `$ARGUMENTS`는 사용자가 이 스킬과 함께 준 요청 내용이다.
- `/abrain:onboarding`, `/abrain:ingest`, `/abrain:query`, `/abrain:lint`, `/abrain:morning`은 Codex에서 `$abrain-onboarding`, `$abrain-ingest`, `$abrain-query`, `$abrain-lint`, `$abrain-morning`으로 읽는다.
