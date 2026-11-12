#!/usr/bin/env python3
"""abrain 위키 기계 점검. 읽기만 하고 아무것도 고치지 않는다.

    python3 lint-scan.py            # 저장소 루트를 자동으로 찾는다
    python3 lint-scan.py --root DIR

판단이 필요 없는 항목(깨진 링크, index 누락, 기한 지난 할 일 등)을 찾아
항목별로 출력한다. 판단이 필요한 항목(모순, 출처 대조)은 에이전트가 한다.
표준 라이브러리만 쓴다.
"""
import argparse
import datetime as dt
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SPECIAL = {"index", "log", "용어집", "프로필"}
REQUIRED = {
    "source": ["raw", "date"],
    "decision": ["status", "date", "owner"],
    "person": ["aliases"],
    "project": [],
    "topic": [],
}
LINK_RE = re.compile(r"!?\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")
DUE_RE = re.compile(r"기한\s*(\d{4}-\d{2}-\d{2})")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm, text[end + 4:]


def strip_code(body):
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", body)


def to_date(s):
    try:
        return dt.date.fromisoformat(s[:10])
    except (TypeError, ValueError):
        return None


def section(title, items, limit=40):
    print(f"\n## {title} — {len(items)}건")
    for it in items[:limit]:
        print(f"- {it}")
    if len(items) > limit:
        print(f"- … 외 {len(items) - limit}건")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    args = ap.parse_args()
    root = Path(args.root)
    wiki, raw = root / "wiki", root / "raw"
    if not wiki.is_dir():
        sys.exit(f"wiki/ 폴더가 없습니다: {wiki}")
    today = dt.date.today()

    pages = {}  # stem -> dict
    dup_names = defaultdict(list)
    for p in sorted(wiki.rglob("*.md")):
        if any(part.startswith(".") for part in p.relative_to(wiki).parts):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        fm, body = parse_frontmatter(text)
        rel = p.relative_to(root).as_posix()
        dup_names[p.stem].append(rel)
        pages[p.stem] = {"path": rel, "fm": fm, "body": strip_code(body), "text": text}

    # 링크
    inbound = Counter()
    broken = defaultdict(set)  # target -> {source pages}
    for stem, pg in pages.items():
        for t in LINK_RE.findall(pg["text"]):
            t = t.strip()
            if Path(t).suffix and Path(t).suffix != ".md":
                continue  # 이미지 등 첨부
            t = t[:-3] if t.endswith(".md") else t
            if t in pages:
                if stem not in ("index", "log") and t != stem:
                    inbound[t] += 1
            else:
                broken[t].add(stem)

    index_links = set()
    if "index" in pages:
        index_links = {t.strip() for t in LINK_RE.findall(pages["index"]["text"])}

    content = {s: pg for s, pg in pages.items() if s not in SPECIAL}

    fm_problems, overdue, pending_old, unconfirmed, speakers, stale = [], [], [], [], [], []
    for stem, pg in content.items():
        fm = pg["fm"]
        if fm is None:
            fm_problems.append(f"{pg['path']}: frontmatter 없음")
            continue
        typ = fm.get("type")
        if typ not in REQUIRED:
            fm_problems.append(f"{pg['path']}: type 없음 또는 알 수 없음 ({typ!r})")
            continue
        missing = [k for k in ["updated"] + REQUIRED[typ] if not fm.get(k)]
        if missing:
            fm_problems.append(f"{pg['path']}: {', '.join(missing)} 없음")
        if fm.get("updated") and not to_date(fm["updated"]):
            fm_problems.append(f"{pg['path']}: updated 날짜 형식 오류 ({fm['updated']})")
        if typ == "decision" and fm.get("status") == "pending":
            d = to_date(fm.get("date", ""))
            if d and (today - d).days > 30:
                pending_old.append(f"[[{stem}]] — pending {(today - d).days}일째")
        for line in pg["body"].splitlines():
            if re.match(r"^\s*- \[ \]", line):
                m = DUE_RE.search(line)
                if m and to_date(m.group(1)) and to_date(m.group(1)) < today:
                    overdue.append(f"[[{stem}]]: {line.strip()}")
        if "(표기 미확인)" in pg["body"]:
            unconfirmed.append(f"[[{stem}]] — {pg['body'].count('(표기 미확인)')}곳")
        lab = set(re.findall(r"참여자[A-Z]\s*\(미확정\)", pg["body"]))
        if typ == "source":
            lab |= {f"{m} (표: 미확정)" for m in re.findall(r"\|\s*(참여자[A-Z])\s*\|\s*미확정", pg["body"])}
        if lab:
            speakers.append(f"[[{stem}]] — {', '.join(sorted(lab))}")

    # 낡은 페이지 후보: 이 페이지를 링크하는 source가 페이지의 updated보다 새롭다
    for stem, pg in content.items():
        fm = pg["fm"] or {}
        if fm.get("type") in (None, "source"):
            continue
        upd = to_date(fm.get("updated", ""))
        if not upd:
            continue
        newer = []
        for s2, pg2 in content.items():
            fm2 = pg2["fm"] or {}
            if fm2.get("type") != "source":
                continue
            d2 = to_date(fm2.get("updated", "")) or to_date(fm2.get("date", ""))
            if d2 and d2 > upd and re.search(r"\[\[" + re.escape(stem) + r"(\]\]|\||#)", pg2["text"]):
                newer.append(s2)
        if newer:
            stale.append(f"[[{stem}]] (updated {upd}) ← 더 새 소스: " + ", ".join(f"[[{n}]]" for n in sorted(newer)[:3]))

    # 용어집의 틀린 표기가 남은 곳
    wrong_terms = []
    glossary = pages.get("용어집")
    if glossary:
        for line in glossary["text"].splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or cells[0] in ("확정 표기", "") or set(cells[0]) <= set("-: "):
                continue
            right = cells[0]
            for v in re.split(r"[,、/]", cells[1]):
                v = v.strip()
                if not v or v == right or v in right:
                    continue
                hits = [f"[[{s}]]" for s, pg in content.items() if v in pg["body"]]
                if hits:
                    wrong_terms.append(f"'{v}' → '{right}': " + ", ".join(hits[:5]))

    # 미처리 원본
    unprocessed = []
    if raw.is_dir():
        referenced = set()
        for pg in content.values():
            r = (pg["fm"] or {}).get("raw")
            if r:
                referenced.add(r.removeprefix("raw/"))
        for p in sorted(raw.rglob("*")):
            rel = p.relative_to(raw)
            if not p.is_file() or rel.parts[0] in ("_extracted", "assets") or p.name.startswith("."):
                continue
            if rel.as_posix() not in referenced:
                unprocessed.append(f"raw/{rel.as_posix()}")

    print(f"# abrain lint-scan {today} — 페이지 {len(content)}개")
    section("깨진 링크 (대상 · 링크한 페이지)",
            [f"[[{t}]] ← " + ", ".join(f"[[{s}]]" for s in sorted(srcs)[:4]) + (" (3곳 이상: 페이지 후보)" if len(srcs) >= 3 else "")
             for t, srcs in sorted(broken.items(), key=lambda kv: -len(kv[1]))])
    section("파일명 중복", [f"{n}: {', '.join(ps)}" for n, ps in dup_names.items() if len(ps) > 1])
    section("index 누락", [f"[[{s}]] ({pg['path']})" for s, pg in content.items() if s not in index_links])
    section("들어오는 링크 없음 (index·log 제외)", [f"[[{s}]]" for s in content if inbound[s] == 0])
    section("frontmatter 문제", fm_problems)
    section("기한 지난 열린 항목", overdue)
    section("30일 넘은 pending 결정", pending_old)
    section("낡은 서술 후보 (더 새 소스가 링크함)", stale)
    section("(표기 미확인) 남은 페이지", unconfirmed)
    section("용어집의 틀린 표기가 남은 곳", wrong_terms)
    section("미확정 참여자", speakers)
    section("미처리 원본", unprocessed)


if __name__ == "__main__":
    main()
