#!/usr/bin/env python3
"""abrain 모닝 브리핑 준비. 읽기만 하고 아무것도 고치지 않는다.

    python3 morning-scan.py                # 저장소 루트를 자동으로 찾는다
    python3 morning-scan.py --days 3       # 수집 구간을 3일 전부터로 고정
    python3 morning-scan.py --root DIR

브리핑에서 판단이 필요 없는 부분을 계산해 출력한다.

- 오늘 날짜와 수집 구간 (지난 브리핑 이후. 없으면 직전 근무일부터. 최대 7일)
- 구간의 시작을 각 도구가 받는 형식으로 (Slack unix, 캘린더 ISO, Drive UTC, JQL·CQL 날짜)
- 프로필의 "모닝 브리핑 설정"
- 위키의 기한 지난·오늘·7일 내 열린 항목, pending 결정, 미확정 참여자, 미처리 원본
- 구간 안의 log 항목, 지난 브리핑의 "오늘 챙길 것"

표준 라이브러리만 쓴다.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

MAX_DAYS = 7
SOON_DAYS = 7
WEEKDAYS = "월화수목금토일"
SPECIAL = {"index", "log", "용어집", "프로필"}
DUE_RE = re.compile(r"기한\s*(\d{4}-\d{2}-\d{2})")
LOG_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]\s*([^|]+?)\s*\|\s*(.*)$")
BRIEF_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) 모닝 브리핑$")
CARRY_HEADING = "## 오늘 챙길 것"
SETTINGS_HEADING = "## 모닝 브리핑 설정"


def frontmatter(text):
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm, text[end + 4:]


def to_date(s):
    try:
        return dt.date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def heading_block(text, heading):
    """heading 줄 다음부터 같은 수준 이상의 다음 제목 전까지."""
    level = len(heading) - len(heading.lstrip("#"))
    out, on = [], False
    for line in text.splitlines():
        if line.strip() == heading:
            on = True
            continue
        if on and re.match(r"^#{1,%d} " % level, line):
            break
        if on:
            out.append(line)
    return "\n".join(out).strip()


def prev_workday(d):
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def section(title, items, limit=30):
    print(f"\n## {title} — {len(items)}건")
    for it in items[:limit]:
        print(f"- {it}")
    if len(items) > limit:
        print(f"- … 외 {len(items) - limit}건")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    ap.add_argument("--days", type=int, default=0, help="수집 구간을 N일 전부터로 고정 (1~7)")
    args = ap.parse_args()
    root = Path(args.root)
    wiki, raw = root / "wiki", root / "raw"
    if not wiki.is_dir():
        sys.exit(f"wiki/ 폴더가 없습니다: {wiki} — ./INSTALL.sh 를 먼저 실행하세요.")

    now = dt.datetime.now().astimezone()
    today = now.date()

    pages = {}
    for p in sorted(wiki.rglob("*.md")):
        if any(part.startswith(".") for part in p.relative_to(wiki).parts):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        fm, body = frontmatter(text)
        pages[p.stem] = {"path": p.relative_to(root).as_posix(), "fm": fm, "body": body, "text": text}

    # log
    log_entries = []
    if "log" in pages:
        for line in pages["log"]["text"].splitlines():
            m = LOG_RE.match(line)
            if m and to_date(m.group(1)):
                log_entries.append((to_date(m.group(1)), m.group(2).strip(), m.group(3).strip()))
    morning_dates = sorted({d for d, kind, _ in log_entries if kind == "morning"})

    # 브리핑 페이지
    briefs = sorted((BRIEF_NAME_RE.match(s).group(1), s) for s in pages if BRIEF_NAME_RE.match(s))
    brief_today = next((s for d, s in briefs if d == today.isoformat()), None)
    brief_prev = next((s for d, s in reversed(briefs) if d < today.isoformat()), None)

    # 수집 구간
    last_before_today = max((d for d in morning_dates if d < today), default=None)
    if args.days:
        since = today - dt.timedelta(days=max(1, min(args.days, MAX_DAYS)))
        reason = f"인자로 지정 ({(today - since).days}일)"
    elif last_before_today:
        since, reason = last_before_today, f"지난 브리핑 {last_before_today}"
    else:
        since, reason = prev_workday(today), "브리핑 기록 없음 → 직전 근무일"
    floor = today - dt.timedelta(days=MAX_DAYS)
    truncated = since < floor
    if truncated:
        reason += f" → 최대 {MAX_DAYS}일로 줄임 (원래 {since})"
        since = floor
    since_dt = dt.datetime.combine(since, dt.time.min).astimezone()
    tomorrow = today + dt.timedelta(days=1)

    print(f"# abrain morning-scan {today} ({WEEKDAYS[today.weekday()]}) {now:%H:%M} {now.tzname()}")
    print("\n## 구간")
    print(f"- 오늘: {today} ({WEEKDAYS[today.weekday()]}요일)")
    print(f"- 수집 구간: {since} ({WEEKDAYS[since.weekday()]}) 00:00 ~ 지금 — {reason}")
    if (today - since).days >= 3 and not args.days:
        print(f"- 구간이 {(today - since).days}일입니다. 주말·휴가 뒤의 브리핑으로 쓴다.")
    print(f"- 오늘 브리핑 페이지: {('[[' + brief_today + ']] 있음 → 새로 만들지 말고 다시 쓴다') if brief_today else '없음 → 새로 만든다'}")
    print(f"- 지난 브리핑 페이지: {('[[' + brief_prev + ']]') if brief_prev else '없음'}")
    print("\n## 도구별 구간 값")
    print(f"- Slack `after` (unix, 구간 시작): {int(since_dt.timestamp())}")
    print(f"- 캘린더 오늘: startTime {today}T00:00:00 / endTime {tomorrow}T00:00:00")
    print(f"- 캘린더 구간(지난 회의): startTime {since}T00:00:00 / endTime {today}T00:00:00")
    print(f"- Drive modifiedTime (UTC): {since_dt.astimezone(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}")
    print(f"- JQL·CQL 날짜: \"{since}\"")
    print(f"- 메일 after: {since:%Y/%m/%d}")

    # 프로필
    print("\n## 프로필")
    prof = pages.get("프로필")
    if not prof:
        print("- wiki/프로필.md 없음 → 지역은 서울로 가정하고, 사용자는 각 도구의 로그인 계정으로 본다. 보고 끝에 온보딩을 권한다.")
    else:
        settings = heading_block(prof["text"], SETTINGS_HEADING)
        if settings and settings != "없음":
            print(f"- 설정 ({SETTINGS_HEADING}):")
            for line in settings.splitlines():
                if line.strip():
                    print(f"  {line}")
        else:
            print(f"- 프로필에 \"{SETTINGS_HEADING}\"이 없거나 비어 있음 → 지역은 서울로 가정한다.")

    content = {s: pg for s, pg in pages.items() if s not in SPECIAL}

    overdue, due_today, due_soon, undated = [], [], [], {}
    pending, speakers, unconfirmed = [], [], []
    for stem, pg in content.items():
        fm = pg["fm"]
        if BRIEF_NAME_RE.match(stem):
            continue  # 브리핑 페이지는 다른 페이지의 내용을 옮겨 적은 것이다
        body = re.sub(r"```.*?```", "", pg["body"], flags=re.S)
        for line in body.splitlines():
            if not re.match(r"^\s*- \[ \]", line):
                continue
            item = f"[[{stem}]]: {line.strip()}"
            m = DUE_RE.search(line)
            due = to_date(m.group(1)) if m else None
            if not due:
                undated[stem] = undated.get(stem, 0) + 1
            elif due < today:
                overdue.append((due, f"{item} ← {(today - due).days}일 지남"))
            elif due == today:
                due_today.append((due, item))
            elif (due - today).days <= SOON_DAYS:
                due_soon.append((due, f"{item} ← {(due - today).days}일 남음"))
        if fm.get("type") == "decision" and fm.get("status") == "pending":
            d = to_date(fm.get("date"))
            age = f"{(today - d).days}일째" if d else "날짜 없음"
            pending.append(f"[[{stem}]] — pending {age}, owner {fm.get('owner', '없음')}")
        labs = set(re.findall(r"참여자[A-Z]\s*\(미확정\)", body))
        if fm.get("type") == "source":
            labs |= {f"{m} (표: 미확정)" for m in re.findall(r"\|\s*(참여자[A-Z])\s*\|\s*미확정", body)}
        if labs:
            speakers.append(f"[[{stem}]] — {', '.join(sorted(labs))}")
        if "(표기 미확인)" in body:
            unconfirmed.append(f"[[{stem}]]")

    section("기한 지난 열린 항목", [t for _, t in sorted(overdue)])
    section("오늘 기한인 열린 항목", [t for _, t in sorted(due_today)])
    section(f"{SOON_DAYS}일 안에 기한이 오는 열린 항목", [t for _, t in sorted(due_soon)])
    section("기한 없는 열린 항목 (페이지별 개수)", [f"[[{s}]] — {n}개" for s, n in sorted(undated.items(), key=lambda kv: -kv[1])])
    section("pending 결정", pending)
    section("미확정 참여자", speakers)
    section("(표기 미확인) 남은 페이지", unconfirmed)

    unprocessed = []
    if raw.is_dir():
        source_text = "\n".join(pg["text"] for pg in content.values() if pg["fm"].get("type") == "source")
        for p in sorted(raw.rglob("*")):
            rel = p.relative_to(raw)
            if not p.is_file() or rel.parts[0] in ("_extracted", "assets") or p.name.startswith("."):
                continue
            if f"raw/{rel.as_posix()}" not in source_text:  # raw: 필드나 본문에 경로가 적혀 있으면 처리된 것
                unprocessed.append(f"raw/{rel.as_posix()}")
    section("미처리 원본 (ingest 안 됨)", unprocessed)

    section(f"구간 안의 위키 작업 ({since} 이후 log)",
            [f"{d} {kind} | {title}" for d, kind, title in log_entries if d >= since])

    print("\n## 지난 브리핑의 \"오늘 챙길 것\"")
    if brief_prev:
        carry = heading_block(pages[brief_prev]["text"], CARRY_HEADING)
        print(f"출처: [[{brief_prev}]] — 항목마다 해결됐는지 확인하고, 남은 것은 이월한다.")
        print(carry or "(비어 있음)")
    else:
        print("없음")


if __name__ == "__main__":
    main()
