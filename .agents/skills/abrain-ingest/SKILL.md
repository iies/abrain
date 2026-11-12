---
name: abrain-ingest
description: abrain 위키에 무엇이든 넣는다. 회의 내용, 메모, 아이디어, 붙여넣은 텍스트, raw/의 파일, 웹·YouTube·Google 문서 URL을 원본으로 보존하고 source 요약과 결정·사람·프로젝트·주제 페이지로 구축·갱신한다. 사용자가 "ingest", "정리해줘", "이거 넣어줘", "기록해줘", "메모해둬", "위키에 추가", "회의록 정리"라고 하거나, 파일·URL·긴 텍스트를 주며 남겨 달라고 할 때 쓴다.
---

# abrain-ingest (Codex)

이 스킬의 본문은 Claude Code와 같이 쓴다. `.claude/skills/abrain/skills/ingest/SKILL.md`를 읽고 그대로 실행한다.

- 그 문서의 `$ARGUMENTS`는 사용자가 이 스킬과 함께 준 요청 내용이다.
- `/abrain:onboarding`, `/abrain:ingest`, `/abrain:query`, `/abrain:lint`, `/abrain:morning`은 Codex에서 `$abrain-onboarding`, `$abrain-ingest`, `$abrain-query`, `$abrain-lint`, `$abrain-morning`으로 읽는다.
