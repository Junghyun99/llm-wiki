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
"""

import argparse
import re
from datetime import date
from pathlib import Path

WIKI_DIR         = Path("03_Wiki")
EXCLUDE_PREFIXES = ("@", "MOC_")

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

def extract_links(filepath: Path) -> set[str]:
    content = filepath.read_text(encoding="utf-8")
    links   = set()
    for link in re.findall(r"\[\[([^\]]+)\]\]", content):
        link = link.split("|")[0].split("#")[0].strip()
        if link and not any(link.startswith(p) for p in EXCLUDE_PREFIXES):
            links.add(link)
    return links

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files",   required=True)
    parser.add_argument("--date",    default=str(date.today()))
    parser.add_argument("--dry-run", action="store_true")
    args  = parser.parse_args()
    files = [f.strip() for f in args.files.split(",") if f.strip()]

    # 1. 링크 수집
    all_links: set[str] = set()
    for fname in files:
        path = WIKI_DIR / fname
        if not path.exists():
            print(f"⚠️  {fname} 없음 (스킵)")
            continue
        links = extract_links(path)
        all_links |= links

    # 2. 존재 확인
    missing = [
        link for link in sorted(all_links)
        if not (WIKI_DIR / f"{link}.md").exists()
    ]

    if not missing:
        print("✅ 데드링크 없음.")
        return

    if args.dry_run:
        print(f"(dry-run) 생성될 스텁: {missing}")
        return

    # 3. 스텁 생성
    for link in missing:
        (WIKI_DIR / f"{link}.md").write_text(
            STUB_TEMPLATE.format(date=args.date, title=link),
            encoding="utf-8"
        )
        print(f"stub: {link}.md")

if __name__ == "__main__":
    main()
