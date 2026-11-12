# abrain

[Karpathy의 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 패턴의 최소 구현.
회의록, 문서, 녹음, 링크를 넣으면 LLM이 결정, 사람, 프로젝트, 주제별로 정리된 위키를 만들고 계속 최신으로 유지한다.

구성은 규칙 문서 하나(`AGENTS.md`)와 설치 스크립트 하나(`INSTALL.sh`)가 전부다. Claude Code와 Codex가 같은 규칙을 읽는다.

## 시작

1. 공유받은 abrain 폴더(압축 파일)를 원하는 위치에 풀고, 터미널에서 그 폴더로 이동한다.
2. `./INSTALL.sh`를 한 번 실행한다. 변환 도구를 설치하고, Codex 샌드박스 설정과 빈 `raw/`, `wiki/` 폴더를 만든다. macOS와 Homebrew가 필요하고, 음성 인식 모델 약 4.6GB를 받는다.
3. 폴더에서 `claude` 또는 `codex`를 실행한다.
4. (선택) Obsidian에서 `wiki/` 폴더를 vault로 열면 링크와 그래프로 탐색할 수 있다.

## 사용법

| 하고 싶은 일 | 하는 말 |
|---|---|
| 파일 넣기 | `raw/`에 파일을 넣고 "ingest" |
| 회의록 넣기 | 내용을 붙여넣고 "정리해줘" |
| 링크 넣기 | "이거 넣어줘 https://..." (웹 문서, YouTube, Google Docs·Slides·Sheets) |
| 물어보기 | "결제 개편 건 지금 어디까지 왔지?", "아직 결정 안 된 사안 뭐 있어?", "내일 김OO 1:1 전에 알아야 할 것" |
| 답을 위키에 남기기 | 답을 받은 뒤 "저장해줘" |
| 틀린 내용 고치기 | "그거 틀렸어, 출시일은 12월 20일이야" |
| 점검 | "lint" (주 1회 정도) |

## 넣을 수 있는 것

| 종류 | 형식 |
|---|---|
| 문서 | docx, pptx, xlsx, pdf(스캔본 포함), hwp, hwpx, doc, rtf, odt, html, eml, txt, md, csv |
| 이미지 | png, jpg, gif, webp, heic, tiff, bmp (화이트보드 사진, 스크린샷) |
| 음성 | mp3, wav, m4a, ogg, flac |
| 영상 | mp4, mkv, mov, webm |
| 온라인 | 웹 URL, YouTube, Google Docs·Slides·Sheets |

알아둘 점:

- **음성 전사에는 화자 구분이 없다.** 누가 말했는지가 중요한 회의는 Zoom, Meet, 클로바노트의 화자 표시 스크립트를 넣는 편이 정확하다.
- **전사 속도**: 1시간 회의 기준 Claude Code는 5~6분, Codex는 13분 안팎이다. Codex 샌드박스는 GPU를 쓸 수 없어 CPU로 전사한다.
- **Google 문서**는 Claude나 Codex에 Google Drive 커넥터가 연결되어 있어야 한다. 없으면 파일로 내려받아 `raw/`에 넣는다.
- **문서보안(DRM)이나 암호가 걸린 파일**은 읽지 못한다. 해제한 파일을 넣는다.
- **Codex를 비대화형으로 쓸 때**는 `codex exec --skip-git-repo-check --sandbox workspace-write "ingest"`처럼 옵션 두 개를 붙인다.

## 원칙

- `raw/`는 사람이 넣고, 에이전트는 읽기만 한다. 변환한 텍스트는 `raw/_extracted/`에 따로 둔다.
- `wiki/`는 에이전트가 쓴다. 직접 고치지 말고 고쳐 달라고 말한다.
- 정리 방식이 마음에 안 들면 `AGENTS.md`를 고친다. 이 파일이 곧 제품이다.
- **내 데이터는 내 컴퓨터에만 있다.** `raw/`와 `wiki/`는 이 폴더 안에만 저장되고, 템플릿 저장소에는 올라가지 않는다.
