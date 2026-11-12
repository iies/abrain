#!/usr/bin/env python3
"""모닝 브리핑 데이터(JSON)를 읽기 좋은 보고서 HTML로 만든다.

    python3 morning-report.py DATA.json OUT.html               # Claude 아티팩트용 (본문 조각)
    python3 morning-report.py DATA.json OUT.html --standalone  # 브라우저에서 바로 여는 완전한 HTML (Codex)

디자인은 이 파일에 고정되어 있다. 에이전트는 JSON만 쓴다. 모든 글자는 여기서 이스케이프하고,
링크는 http(s)만 건다. 메일·메시지에서 온 글이 그대로 HTML이 되지 않게 하기 위해서다.

DATA.json (없는 키는 그 절을 "없음"으로 그린다):

{
  "date": "2026-11-12", "weekday": "목",
  "window": "2026-11-11 00:00 ~ 14:35",
  "summary": "한두 문장 요약",
  "weather": weather.sh --json 의 출력 그대로 | {"error": "가져오지 못함 — 이유"},
  "focus":   [{"tag": "답할 것|약속|확인|정리|기한", "title": "", "detail": "", "source": "Slack #채널", "url": ""}],
  "schedule": [{"time": "10:00–11:00", "title": "", "people": "", "prep": "", "url": ""}],
  "schedule_note": "겹침·미응답 초대·내일 일정 수 등 한 줄",
  "reply":   [{"source": "", "from": "", "when": "11-11 19:03", "quote": "", "ask": "", "url": ""}],
  "fyi":     [{"source": "", "text": "", "url": ""}],
  "promised": [{"text": "", "meta": "", "url": ""}],
  "waiting":  [{"text": "", "meta": "", "url": ""}],
  "carried":  [{"text": "", "meta": "3일째", "url": ""}],
  "resolved": [{"text": "", "meta": "", "url": ""}],
  "wiki":    [{"label": "기한이 지난 할 일", "count": 2,
               "text": "무엇이 어떤 상태이고 왜 봐야 하는지 한두 문장",
               "items": [{"text": "항목 하나를 풀어 쓴 문장", "page": "위키 페이지 이름", "url": "원문 링크"}],
               "page": "", "pages": [], "url": "", "links": [{"label": "", "url": ""}],
               "action": "사용자가 하면 되는 일 한 문장"}],
  "wiki_ok": "문제가 없는 점검 항목을 한 줄로 (예: 오늘·7일 내 기한 0건, pending 결정 0건)",
  "status":  [{"source": "Slack", "state": "완료|연결 없음|실패|잘림", "read": "49", "shown": "12", "note": ""}],
  "suggestions": [{"kind": "넣기|답하기|설정", "title": "사용자에게 묻는 것 한 문장",
                   "why": "하면 무엇이 좋아지는지",
                   "items": [{"text": "물을 것이 여럿일 때 하나씩", "url": ""}],
                   "say": "새 대화에 이것만 붙여넣어도 통하는 말. 답이 필요한 자리는 ___ 로 비워 둔다",
                   "say_note": "빈칸을 어떻게 채우는지", "how": "말로 할 수 없는 일(커넥터 연결 등)의 방법",
                   "links": [{"label": "", "url": ""}]}],
  "written": "위키에 쓴 것 한 줄 (보기만이면 '쓰지 않음 (보기만)')"
}
"""
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

WIKI = Path(__file__).resolve().parents[4] / "wiki"

TAG_CLASS = {"답할 것": "reply", "약속": "promise", "기한": "due", "확인": "check", "정리": "tidy"}
STATE_CLASS = {"완료": "ok", "연결 없음": "off", "실패": "bad", "잘림": "warn"}


def e(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def link(url, label="원문"):
    url = str(url or "").strip()
    if not re.match(r"^https?://", url):
        return ""
    return f'<a class="src" href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(label)}</a>'


def empty(text="없음"):
    return f'<p class="none">{e(text)}</p>'


def weather_block(w):
    if not w:
        return ""
    if w.get("error"):
        return f'<aside class="wx"><p class="wx-label">날씨</p><p class="none">{e(w["error"])}</p></aside>'
    hours = [h for h in w.get("hours") or [] if isinstance(h.get("temp"), (int, float))]
    bars = ""
    if hours:
        lo, hi = min(h["temp"] for h in hours), max(h["temp"] for h in hours)
        span = (hi - lo) or 1
        for h in hours:  # 막대 높이는 표시한 시간대의 기온 범위(최저 8px ~ 최고 48px)에 비례한다
            px = 8 + round((h["temp"] - lo) / span * 40)
            rain = f'<span class="wx-pop">{e(h.get("pop"))}%</span>' if (h.get("pop") or 0) >= 30 else ""
            bars += (f'<li title="{e(h.get("sky"))}"><span class="wx-t">{e(h["temp"])}°</span>'
                     f'<span class="wx-bar" style="height:{px}px"></span>'
                     f'<span class="wx-h">{e(h.get("hour"))}시</span>{rain}</li>')
        bars = f'<ol class="wx-hours" aria-label="시간대별 기온">{bars}</ol>'
    facts = [f'{e(w.get("low"))} / {e(w.get("high"))}°C', f'강수 {e(w.get("rain"))}']
    if w.get("dust"):
        facts.append(e(w["dust"]))
    tomorrow = f'<p class="wx-tom">내일 {e(w["tomorrow"])}</p>' if w.get("tomorrow") else ""
    return f'''<aside class="wx">
<p class="wx-label">날씨 · {e(w.get("place"))} <span>{e(w.get("asof"))} 기준</span></p>
<div class="wx-row"><p class="wx-now"><strong>{e(w.get("now"))}</strong> {e(w.get("sky"))}</p>
<p class="wx-facts">{" · ".join(facts)}</p></div>
{bars}
<div class="wx-row"><p class="wx-tip">{e(w.get("tip"))}</p>
{tomorrow}</div>
</aside>'''


def focus_block(items, date):
    if not items:
        return empty("오늘 꼭 챙길 것은 없습니다.")
    rows = ""
    for n, it in enumerate(items, 1):
        tag = it.get("tag") or ""
        pill = f'<span class="pill {TAG_CLASS.get(tag, "check")}">{e(tag)}</span>' if tag else ""
        src = " · ".join(x for x in (e(it.get("source")) if it.get("source") else "", link(it.get("url"))) if x)
        detail = f'<p class="detail">{e(it["detail"])}</p>' if it.get("detail") else ""
        rows += f'''<li>
<input type="checkbox" id="focus-{e(date)}-{n}" aria-label="{n}번 끝냄">
<div class="focus-body"><p class="focus-title"><span class="num">{n}</span>{pill}<label for="focus-{e(date)}-{n}">{e(it.get("title"))}</label></p>
{detail}<p class="meta">{src}</p></div>
</li>'''
    return f'<ol class="focus">{rows}</ol>'


def schedule_block(items, note):
    body = ""
    for it in items or []:
        people = f'<p class="meta">{e(it["people"])}</p>' if it.get("people") else ""
        prep = f'<p class="detail"><span class="k">준비</span>{e(it["prep"])}</p>' if it.get("prep") else ""
        body += (f'<li><span class="time">{e(it.get("time"))}</span><div><p class="row-title">{e(it.get("title"))} '
                 f'{link(it.get("url"), "일정")}</p>{people}{prep}</div></li>')
    body = f'<ul class="sched">{body}</ul>' if body else empty("오늘 일정이 없습니다.")
    return body + (f'<p class="note">{e(note)}</p>' if note else "")


def reply_block(items):
    if not items:
        return empty("답을 기다리는 것이 없습니다.")
    out = ""
    for it in items:
        head = " · ".join(e(x) for x in (it.get("source"), it.get("from"), it.get("when")) if x)
        quote = f'<blockquote>{e(it["quote"])}</blockquote>' if it.get("quote") else ""
        ask = f'<p class="detail"><span class="k">할 일</span>{e(it["ask"])}</p>' if it.get("ask") else ""
        out += f'<li><p class="meta">{head} {link(it.get("url"))}</p>{quote}{ask}</li>'
    return f'<ul class="cards">{out}</ul>'


def simple_list(items, cls="plain", none="없음"):
    if not items:
        return empty(none)
    out = ""
    for it in items:
        lead = f'<span class="k">{e(it["source"])}</span>' if it.get("source") else ""
        meta = f' <span class="meta-inline">{e(it["meta"])}</span>' if it.get("meta") else ""
        out += f'<li>{lead}{e(it.get("text"))}{meta} {link(it.get("url"))}</li>'
    return f'<ul class="{cls}">{out}</ul>'


def loops_block(d):
    groups = [("내가 한 약속", "promised"), ("내가 기다리는 답", "waiting"), ("이월", "carried"), ("해결", "resolved")]
    out = ""
    for title, key in groups:
        if d.get(key):
            out += f'<h3>{title} <span class="count">{len(d[key])}</span></h3>{simple_list(d[key])}'
    return out or empty("약속도, 기다리는 답도 없습니다.")


def page_ref(name):
    """위키 페이지 이름 → 이름 표시 + Obsidian에서 여는 링크. 파일이 없으면 이름만."""
    name = str(name or "").strip()
    if not name:
        return ""
    hit = next(iter(sorted(WIKI.rglob(name + ".md"))), None) if WIKI.is_dir() else None
    if not hit:
        return f'<span class="page">{e(name)}</span>'
    rel = hit.relative_to(WIKI.parent).as_posix()
    href = "obsidian://open?path=" + quote(str(hit))
    return (f'<span class="page" title="{e(rel)}">{e(name)}</span> '
            f'<a class="src" href="{e(href)}">Obsidian에서 열기</a>')


def refs(it):
    """항목에 붙는 근거: 위키 페이지(page, pages)와 원문 링크(url, links)."""
    out = [page_ref(n) for n in ([it.get("page")] if it.get("page") else []) + list(it.get("pages") or [])]
    if it.get("url"):
        out.append(link(it["url"]))
    out += [link(l.get("url"), l.get("label") or "원문") for l in it.get("links") or []]
    out = [x for x in out if x]
    return f'<p class="refs">{" · ".join(out)}</p>' if out else ""


def wiki_block(items, ok_note):
    if not items and not ok_note:
        return empty()
    out = ""
    for it in items or []:
        num = f'<span class="wiki-n">{e(it["count"])}</span>' if it.get("count") is not None else ""
        subs = "".join(f'<li>{e(sub.get("text"))}{refs(sub)}</li>' for sub in it.get("items") or [])
        subs = f'<ul class="sub">{subs}</ul>' if subs else ""
        action = f'<p class="todo"><span class="k">할 일</span>{e(it["action"])}</p>' if it.get("action") else ""
        out += (f'<li><p class="row-title">{num}{e(it.get("label"))}</p>'
                f'<p class="detail">{e(it.get("text"))}</p>{subs}{refs(it)}{action}</li>')
    out = f'<ul class="wiki">{out}</ul>' if out else ""
    return out + (f'<p class="note">{e(ok_note)}</p>' if ok_note else "")


def status_block(items):
    if not items:
        return empty()
    rows = ""
    for it in items:
        state = it.get("state") or ""
        note = f'<span class="meta-inline">{e(it["note"])}</span>' if it.get("note") else ""
        rows += (f'<tr><th scope="row">{e(it.get("source"))}</th>'
                 f'<td><span class="state {STATE_CLASS.get(state, "warn")}">{e(state)}</span> {note}</td>'
                 f'<td class="n">{e(it.get("read", "-"))}</td><td class="n">{e(it.get("shown", "-"))}</td></tr>')
    return (f'<div class="scroll"><table><thead><tr><th scope="col">소스</th><th scope="col">상태</th>'
            f'<th scope="col" class="n">읽음</th><th scope="col" class="n">올림</th></tr></thead><tbody>{rows}</tbody></table></div>')


def suggestions_block(items):
    if not items:
        return empty("제안할 것이 없습니다.")
    out = ""
    for n, it in enumerate(items, 1):
        why = f'<p class="detail">{e(it["why"])}</p>' if it.get("why") else ""
        say = ""
        if it.get("say"):
            hint = f'<span class="meta-inline">{e(it["say_note"])}</span>' if it.get("say_note") else ""
            say = (f'<p class="say"><span class="k">이렇게 말하면 됩니다</span>'
                   f'<code id="say-{n}">{e(it["say"])}</code>'
                   f'<button type="button" class="copy" data-copy="say-{n}">복사</button>{hint}</p>')
        how = f'<p class="todo"><span class="k">방법</span>{e(it["how"])}</p>' if it.get("how") else ""
        subs = "".join(f'<li>{e(sub.get("text"))}{refs(sub)}</li>' for sub in it.get("items") or [])
        subs = f'<ul class="sub">{subs}</ul>' if subs else ""
        out += (f'<li><p class="row-title"><span class="pill tidy">{e(it.get("kind"))}</span>{e(it.get("title"))}</p>'
                f'{why}{subs}{refs(it)}{say}{how}</li>')
    return f'<ul class="sugg">{out}</ul>'


STYLE = """
/* 레이아웃: 처음부터 끝까지 한 단 720px. 위에서 아래로 읽는 순서가 곧 우선순위다. 옆으로 나란히 놓는 절은 없다. */
:root {
  --bg: #eef1f4; --surface: #ffffff; --ink: #18222d; --muted: #5d6b79; --line: #d5dbe2;
  --accent: #c2570c; --accent-soft: #fbe9d9;
  --reply: #b3261e; --reply-soft: #fbe3e1; --promise: #1f5fa8; --promise-soft: #e0ebf8;
  --ok: #1d7044; --ok-soft: #dff1e6; --warn: #8a5a00; --warn-soft: #f8ecd0; --off: #5d6b79; --off-soft: #e4e8ec;
  --sans: "IBM Plex Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12171d; --surface: #1b222b; --ink: #e6ebf0; --muted: #9aa7b4; --line: #303a46;
  --accent: #f0a05a; --accent-soft: #3a2a1c;
  --reply: #ff8f86; --reply-soft: #3d1f1d; --promise: #8dbaf0; --promise-soft: #1c2c40;
  --ok: #7dcea0; --ok-soft: #1a3226; --warn: #e5bd62; --warn-soft: #382d14; --off: #9aa7b4; --off-soft: #262e38;
  color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12171d; --surface: #1b222b; --ink: #e6ebf0; --muted: #9aa7b4; --line: #303a46;
  --accent: #f0a05a; --accent-soft: #3a2a1c;
  --reply: #ff8f86; --reply-soft: #3d1f1d; --promise: #8dbaf0; --promise-soft: #1c2c40;
  --ok: #7dcea0; --ok-soft: #1a3226; --warn: #e5bd62; --warn-soft: #382d14; --off: #9aa7b4; --off-soft: #262e38;
  color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 15px; line-height: 1.6;
  padding-block: 28px 56px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.page { max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px; }
.page p, .page h1, .page h2, .page h3, .page ul, .page ol, .page blockquote { margin: 0; }
.page ul, .page ol { padding: 0; list-style: none; }
a.src { color: var(--promise); font-size: 12.5px; text-decoration: underline; text-underline-offset: 2px; white-space: nowrap; }
a.src:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.top { display: flex; flex-direction: column; gap: 20px; }
.head { min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.eyebrow { font-family: var(--mono); font-size: 12px; letter-spacing: .08em; color: var(--muted); }
h1 { font-size: clamp(30px, 6vw, 44px); line-height: 1.1; font-weight: 700; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
h1 span { color: var(--accent); }
.summary { font-size: 16px; text-wrap: pretty; }

.wx { min-width: 0; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; }
.wx-row { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 4px 20px; }
.wx-label { font-size: 12px; color: var(--muted); letter-spacing: .04em; }
.wx-label span { font-family: var(--mono); letter-spacing: 0; }
.wx-now strong { font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums; margin-right: 6px; }
.wx-facts, .wx-tom { font-size: 13px; color: var(--muted); }
.wx-tip { font-size: 13.5px; }
.wx-hours { display: flex; gap: 10px; align-items: flex-end; height: 92px; margin-block: 8px 4px; }
.wx-hours li { flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 2px; font-family: var(--mono); font-size: 11px; color: var(--muted); position: relative; }
.wx-bar { width: 100%; background: var(--accent-soft); border-top: 2px solid var(--accent); min-height: 4px; flex: 0 0 auto; }
.wx-t { color: var(--ink); }
.wx-pop { position: absolute; top: 0; right: 0; color: var(--promise); }

section { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
h2 { font-size: 15px; font-weight: 700; letter-spacing: .02em; color: var(--ink); margin-top: 8px; display: flex; align-items: baseline; gap: 8px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }
h3 { font-size: 13px; font-weight: 600; margin-top: 6px; }
.count { font-family: var(--mono); font-weight: 400; color: var(--muted); letter-spacing: 0; }
.none { color: var(--muted); font-size: 14px; }
.meta, .meta-inline, .note { font-size: 12.5px; color: var(--muted); }
.detail { font-size: 14px; color: var(--ink); }
.k { display: inline-block; font-size: 11.5px; font-weight: 600; color: var(--muted); margin-right: 8px; letter-spacing: .03em; }
.row-title { font-weight: 600; }

.focus { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; }
.focus li { display: flex; gap: 12px; padding: 14px 16px; align-items: flex-start; }
.focus li + li { border-top: 1px solid var(--line); }
.focus input { margin: 5px 0 0; width: 17px; height: 17px; accent-color: var(--accent); flex: none; }
.focus-body { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.focus-title { font-size: 16px; font-weight: 600; line-height: 1.45; text-wrap: pretty; }
.num { font-family: var(--mono); font-weight: 400; color: var(--muted); margin-right: 8px; }
.focus li:has(input:checked) .focus-title label, .focus li:has(input:checked) .detail { color: var(--muted); text-decoration: line-through; }
.pill { display: inline-block; font-size: 11.5px; font-weight: 600; padding: 1px 8px; border-radius: 99px; margin-right: 8px; vertical-align: 2px; white-space: nowrap; }
.pill.reply { background: var(--reply-soft); color: var(--reply); }
.pill.promise { background: var(--promise-soft); color: var(--promise); }
.pill.due { background: var(--accent-soft); color: var(--accent); }
.pill.check { background: var(--warn-soft); color: var(--warn); }
.pill.tidy { background: var(--off-soft); color: var(--off); }

.sched li { display: flex; gap: 14px; padding-block: 8px; }
.sched li + li { border-top: 1px solid var(--line); }
.time { font-family: var(--mono); font-size: 13px; color: var(--accent); flex: 0 0 96px; font-variant-numeric: tabular-nums; padding-top: 2px; }
.sched div { min-width: 0; }

.cards { display: flex; flex-direction: column; gap: 12px; }
.cards li { border-left: 3px solid var(--reply); padding: 2px 0 2px 14px; display: flex; flex-direction: column; gap: 6px; }
blockquote { font-size: 14px; color: var(--ink); white-space: pre-line; overflow-wrap: anywhere; }
.plain { display: flex; flex-direction: column; gap: 8px; }
.plain li { font-size: 14.5px; overflow-wrap: anywhere; }

.wiki, .sugg { display: flex; flex-direction: column; }
.wiki > li, .sugg > li { display: flex; flex-direction: column; gap: 6px; padding-block: 14px; min-width: 0; }
.wiki > li + li, .sugg > li + li { border-top: 1px solid var(--line); }
.wiki > li:first-child, .sugg > li:first-child { padding-top: 2px; }
.wiki-n { font-family: var(--mono); font-weight: 600; color: var(--accent); margin-right: 8px; font-variant-numeric: tabular-nums; }
.sub { display: flex; flex-direction: column; gap: 6px; padding-left: 14px; border-left: 2px solid var(--line); margin-block: 2px; }
.sub li { font-size: 14px; overflow-wrap: anywhere; }
.refs { font-size: 12.5px; color: var(--muted); overflow-wrap: anywhere; line-height: 2; }
span.page { font-size: 12.5px; background: var(--off-soft); color: var(--ink); padding: 1px 7px; border-radius: 4px; }
.todo { font-size: 14px; }
.say { font-size: 14px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; }
.say .k { margin-right: 0; }
.say code { font-family: var(--mono); font-size: 13px; background: var(--accent-soft); color: var(--ink); padding: 3px 9px; border-radius: 4px; overflow-wrap: anywhere; user-select: all; min-width: 0; }
.copy { font: inherit; font-size: 12px; color: var(--muted); background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 2px 9px; cursor: pointer; }
.copy:hover { color: var(--ink); border-color: var(--muted); }
.copy:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
th, td { text-align: left; padding: 7px 10px 7px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
thead th { font-size: 11.5px; color: var(--muted); font-weight: 600; letter-spacing: .04em; }
tbody th { font-weight: 600; white-space: nowrap; }
.n { text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
.state { font-size: 11.5px; font-weight: 600; padding: 1px 8px; border-radius: 99px; white-space: nowrap; }
.state.ok { background: var(--ok-soft); color: var(--ok); }
.state.off { background: var(--off-soft); color: var(--off); }
.state.bad { background: var(--reply-soft); color: var(--reply); }
.state.warn { background: var(--warn-soft); color: var(--warn); }
footer { font-size: 12.5px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 12px; }
"""

SCRIPT = """
(function () {
  var boxes = document.querySelectorAll('.focus input[type=checkbox]');
  boxes.forEach(function (box) {
    try { if (localStorage.getItem(box.id) === '1') box.checked = true; } catch (err) {}
    box.addEventListener('change', function () {
      try { box.checked ? localStorage.setItem(box.id, '1') : localStorage.removeItem(box.id); } catch (err) {}
    });
  });
  document.querySelectorAll('.copy').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var el = document.getElementById(btn.dataset.copy);
      var done = function () { btn.textContent = '복사됨'; setTimeout(function () { btn.textContent = '복사'; }, 1500); };
      var select = function () { var r = document.createRange(); r.selectNodeContents(el); var sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); btn.textContent = '선택됨'; };
      try { navigator.clipboard.writeText(el.textContent).then(done, select); } catch (err) { select(); }
    });
  });
})();
"""


def render(d):
    date = d.get("date", "")
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date)
    big = f'{int(m.group(2))}월 {int(m.group(3))}일' if m else e(date)
    weekday = f' <span>{e(d["weekday"])}요일</span>' if d.get("weekday") else ""
    reply, fyi = d.get("reply") or [], d.get("fyi") or []
    written = f'위키: {e(d["written"])} · ' if d.get("written") else ""
    return f'''<title>모닝 브리핑</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@400;600;700&display=swap">
<style>{STYLE}</style>
<main class="page">
<div class="top">
<header class="head">
<p class="eyebrow">모닝 브리핑 · {e(date)}</p>
<h1>{big}{weekday}</h1>
<p class="summary">{e(d.get("summary"))}</p>
<p class="meta">구간 {e(d.get("window"))}</p>
</header>
{weather_block(d.get("weather"))}
</div>
<section><h2>오늘 챙길 것 <span class="count">{len(d.get("focus") or [])}</span></h2>{focus_block(d.get("focus"), date)}</section>
<section><h2>오늘 일정 <span class="count">{len(d.get("schedule") or [])}</span></h2>{schedule_block(d.get("schedule"), d.get("schedule_note"))}</section>
<section><h2>놓친 것 · 답할 것 <span class="count">{len(reply)}</span></h2>{reply_block(reply)}</section>
<section><h2>약속과 대기</h2>{loops_block(d)}</section>
<section><h2>놓친 것 · 알아둘 것 <span class="count">{len(fyi)}</span></h2>{simple_list(fyi, none="알아둘 변화가 없습니다.")}</section>
<section><h2>위키 점검</h2>{wiki_block(d.get("wiki"), d.get("wiki_ok"))}</section>
<section><h2>제안</h2>{suggestions_block(d.get("suggestions"))}</section>
<section><h2>수집 상태</h2>{status_block(d.get("status"))}</section>
<footer>{written}밖의 도구는 읽기만 했습니다. 체크 표시는 이 브라우저에만 남습니다.</footer>
</main>
<script>{SCRIPT}</script>
'''


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit("사용법: morning-report.py DATA.json OUT.html [--standalone]")
    try:
        data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        sys.exit(f"보고서 실패: 데이터를 읽지 못했습니다 ({err})")
    page = render(data)
    if "--standalone" in sys.argv:
        page = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                '<style>body{margin:0}img{max-width:100%}</style>\n</head>\n<body>\n' + page + '</body>\n</html>\n')
    out = Path(args[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"보고서: {out} ({len(page.encode('utf-8')) // 1024 + 1}KB)")


if __name__ == "__main__":
    main()
