---
name: abrain-morning
description: abrain 모닝 브리핑. 출근해서 한 번 실행하면 연결된 모든 도구(메일, Slack, Jira, Confluence, Google Drive, 캘린더 등)와 위키를 훑어 지난 브리핑 이후 놓친 것, 오늘 챙길 것, 오늘 회의 준비, 내가 한 약속과 기다리는 답, 오늘 날씨를 한 장으로 보고하고 위키에 남긴다. 사용자가 "morning", "모닝", "아침 브리핑", "모닝 브리핑", "오늘 브리핑", "출근했어", "오늘 뭐 챙겨야 해", "어제 놓친 거 있어?", "밤사이 뭐 있었어?"라고 할 때 쓴다.
---

# abrain-morning (Codex)

이 스킬의 본문은 Claude Code와 같이 쓴다. `.claude/skills/abrain/skills/morning/SKILL.md`를 읽고 그대로 실행한다.

- 그 문서의 `$ARGUMENTS`는 사용자가 이 스킬과 함께 준 요청 내용이다.
- 보고서 페이지(6단계)는 `--standalone`으로 만든 `out/모닝 브리핑/YYYY-MM-DD.html`을 `open`으로 띄운다. Artifact 게시는 Claude Code에만 있다.
- 그 문서의 "Claude 커넥터에서의 쿼리"는 예시다. Codex에 연결된 도구(MCP 서버, 앱)에서 같은 것을 찾는다.
- `/abrain:onboarding`, `/abrain:ingest`, `/abrain:query`, `/abrain:lint`, `/abrain:morning`은 Codex에서 `$abrain-onboarding`, `$abrain-ingest`, `$abrain-query`, `$abrain-lint`, `$abrain-morning`으로 읽는다.
