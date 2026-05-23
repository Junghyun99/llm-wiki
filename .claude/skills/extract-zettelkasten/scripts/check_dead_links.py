#!/usr/bin/env python3
"""
check_dead_links.py
-------------------
extract-zettelkasten 스킬 실행 후, 방금 생성된 노트들의 [[링크]]를 검사하여
존재하지 않는 링크 대상을 스텁(stub) 파일로 자동 생성한다.

레포 루트에서 실행한다.

사용법:
  python3 .claude/skills/extract-zettelkasten/scripts/check_dead_links.py \
    --files "파일A.md,파일B.md" [--date "2026-05-23"] [--dry-run]

인자:
  --files   방금 생성된 파일명 목록 (쉼표 구분, 03_Wiki/ 기준)
  --date    오늘 날짜 YYYY-MM-DD (생략 시 자동)
  --dry-run 파일 생성 없이 결과만 출력
"""

import argparse
import os
import re
import subprocess
from datetime import date
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────────────────
WIKI_DIR = Path("03_Wiki")

# 스텁 제외 패턴: @문헌노트, MOC_ 허브노트
EXCLUDE_PREFIXES = ("@", "MOC_")

# ── 링크 파싱 ─────────────────────────────────────────────────────────────────

def extract_links(filepath: Path) -> set[str]:
    """마크다운 파일에서 [[링크명]] 수집. 제외 패턴 필터링 포함."""
    content = filepath.read_text(encoding="utf-8")
    raw = re.findall(r"\[\[([^\]]+)\]\]", content)
    links = set()
    for link in raw:
        link = link.split("|")[0].split("#")[0].strip()
        if not link:
            continue
        if any(link.startswith(p) for p in EXCLUDE_PREFIXES):
            continue
        links.add(link)
    return links

# ── 스텁 파일 생성 ────────────────────────────────────────────────────────────

STUB_TEMPLATE = """\
---
aliases: []
tags: [permanent, todo/fill]
date_created: {date}
source: ""
---
# {title}

> ⚠️ 이 노트는 자동 생성된 스텁입니다. `/fill-stubs` 명령으로 내용을 채울 수 있습니다.
"""

def make_stub(title: str, today: str) -> str:
    return STUB_TEMPLATE.format(date=today, title=title)

# ── index.md 업데이트 ─────────────────────────────────────────────────────────

INDEX_ROW = "| [[{name}]] | ⚠️ 스텁(미작성) | {date} | todo/fill |"

def update_index(stubs: list[str], today: str):
    path    = WIKI_DIR / "index.md"
    content = path.read_text(encoding="utf-8")

    rows = "\n".join(INDEX_ROW.format(name=s, date=today) for s in stubs)

    # ## 🧠 영구 노트 섹션 끝(다음 --- 또는 ## 직전)에 삽입
    match = re.search(r"(## 🧠 영구 노트.*?)(\n---|\n## )", content, re.DOTALL)
    if match:
        insert_at = match.end(1)
        content   = content[:insert_at] + "\n" + rows + content[insert_at:]
    else:
        content += "\n" + rows + "\n"

    # 통계 갱신
    n = len(stubs)
    content = re.sub(r"(총 노트 수: )(\d+)",   lambda m: m.group(1) + str(int(m.group(2)) + n), content)
    content = re.sub(r"(영구 노트: )(\d+)",     lambda m: m.group(1) + str(int(m.group(2)) + n), content)
    content = re.sub(r"(마지막 업데이트: )\d{4}-\d{2}-\d{2}", lambda m: m.group(1) + today, content)

    path.write_text(content, encoding="utf-8")

# ── log.md 업데이트 ───────────────────────────────────────────────────────────

def update_log(stubs: list[str]):
    path    = WIKI_DIR / "log.md"
    content = path.read_text(encoding="utf-8")

    stub_lines = "\n".join(f"  - `{s}.md`" for s in stubs)
    addition   = f"- 스텁 생성: {len(stubs)}건\n{stub_lines}"

    # 마지막 ## [...] 블록 끝에 추가
    entries = list(re.finditer(r"^## \[", content, re.MULTILINE))
    if not entries:
        content += "\n" + addition + "\n"
    else:
        last_start  = entries[-1].start()
        next_entry  = re.search(r"^## \[", content[last_start + 1:], re.MULTILINE)
        insert_pos  = last_start + 1 + next_entry.start() if next_entry else len(content)
        block       = content[last_start:insert_pos].rstrip()
        content     = content[:last_start] + block + "\n" + addition + "\n" + content[insert_pos:]

    path.write_text(content, encoding="utf-8")

# ── git commit & push ─────────────────────────────────────────────────────────

def git_commit(stubs: list[str]):
    files = (
        [str(WIKI_DIR / f"{s}.md") for s in stubs]
        + [str(WIKI_DIR / "index.md"), str(WIKI_DIR / "log.md")]
    )
    subprocess.run(["git", "add"] + files, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"stub: 데드링크 {len(stubs)}건 자동 생성 [auto]"],
        check=True
    )
    subprocess.run(["git", "push"], check=True)

# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files",   required=True)
    parser.add_argument("--date",    default=str(date.today()))
    parser.add_argument("--dry-run", action="store_true")
    args  = parser.parse_args()
    today = args.date
    files = [f.strip() for f in args.files.split(",") if f.strip()]

    print(f"🔍 검사 대상: {files}")

    # 1. 링크 수집
    all_links: set[str] = set()
    for fname in files:
        path  = WIKI_DIR / fname
        if not path.exists():
            print(f"  ⚠️  {fname} 없음 (스킵)")
            continue
        links = extract_links(path)
        print(f"  📄 {fname}: {len(links)}개 → {links or '없음'}")
        all_links |= links

    if not all_links:
        print("✅ 검사할 링크 없음.")
        return

    # 2. 파일 존재 확인
    missing: list[str] = []
    for link in sorted(all_links):
        if (WIKI_DIR / f"{link}.md").exists():
            print(f"  ✅ [[{link}]]")
        else:
            print(f"  ❌ [[{link}]] → 스텁 생성 예정")
            missing.append(link)

    if not missing:
        print("✅ 데드링크 없음.")
        return

    if args.dry_run:
        print(f"\n(dry-run) 생성될 스텁: {missing}")
        return

    # 3. 스텁 생성
    created = []
    for link in missing:
        p = WIKI_DIR / f"{link}.md"
        p.write_text(make_stub(link, today), encoding="utf-8")
        print(f"  ✅ 스텁 생성: {link}.md")
        created.append(link)

    # 4. index.md / log.md 업데이트
    update_index(created, today)
    print("  ✅ index.md 갱신")
    update_log(created)
    print("  ✅ log.md 갱신")

    # 5. git commit & push
    git_commit(created)
    print(f"\n🛠️  완료: 스텁 {len(created)}건 커밋")

if __name__ == "__main__":
    main()
