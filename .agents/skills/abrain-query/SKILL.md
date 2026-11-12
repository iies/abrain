---
name: abrain-query
description: abrain 위키를 뒤져 질문에 답한다. 결론부터 말하고 근거 페이지를 [[링크]]로 인용하며, 페이지끼리 어긋나면 양쪽과 최신 쪽을 밝힌다. 사람·프로젝트·결정·회의 내용에 대한 모든 질문에 쓴다. 예를 들면 "결제 개편 어디까지 왔지?", "아직 결정 안 된 거 뭐 있어?", "김OO 1:1 전에 알아야 할 것", "지난달 회의에서 X 얘기 나왔어?", "누가 Y 담당이야?", "찾아줘", "검색".
---

# abrain-query (Codex)

이 스킬의 본문은 Claude Code와 같이 쓴다. `.claude/skills/abrain/skills/query/SKILL.md`를 읽고 그대로 실행한다.

- 그 문서의 `$ARGUMENTS`는 사용자가 이 스킬과 함께 준 요청 내용이다.
- `/abrain:ingest`, `/abrain:query`, `/abrain:lint`는 Codex에서 `$abrain-ingest`, `$abrain-query`, `$abrain-lint`로 읽는다.
