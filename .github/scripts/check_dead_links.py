#!/usr/bin/env python3
"""
CI Check: 03_Wiki 전체 데드 링크 검사

기존 스크립트(.claude/skills/extract-zettelkasten/scripts/check_dead_links.py)와의 차이:
  - 기존: 특정 파일(--files) 대상 / 데드링크 발견 시 스텁 자동 생성 (ingest 후 호출)
  - 이 스크립트: 03_Wiki 전체 대상 / 데드링크 발견 시 CI 실패 (push/PR 마다 실행)

판정 기준:
  - FAIL  : 링크 타깃 파일이 아예 존재하지 않음
  - WARN  : 링크 타깃이 스텁(todo/fill)으로만 존재 → ingest 정상 동작 결과이므로 경고만
  - SKIP  : index.md, log.md (탐색 메타 파일)
"""

import os
import re
import sys

WIKI_DIR = "03_Wiki"
SKIP_FILES = {"index.md", "log.md", ".gitkeep"}
STUB_TAG = "todo/fill"

errors = []
warnings = []


def is_stub(filepath: str) -> bool:
    """파일이 스텁 노트(todo/fill 태그 포함)인지 확인"""
    try:
        with open(filepath, encoding="utf-8") as f:
            # frontmatter 영역(첫 30줄)만 읽어 빠르게 판단
            head = "".join(f.readline() for _ in range(30))
        return STUB_TAG in head
    except OSError:
        return False


def extract_links(filepath: str) -> list[tuple[str, int]]:
    """파일에서 [[링크]] 추출 → (링크명, 줄번호) 리스트 반환"""
    links = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                for raw in re.findall(r"\[\[([^\]]+)\]\]", line):
                    # [[링크|표시명]] → 링크 / [[링크#섹션]] → 링크
                    target = raw.split("|")[0].split("#")[0].strip()
                    if target:
                        links.append((target, lineno))
    except OSError as e:
        warnings.append(f"[WARN] 파일 읽기 실패: {filepath} — {e}")
    return links


def scan_wiki():
    """03_Wiki 전체 파일을 스캔하여 데드링크 검사"""
    if not os.path.isdir(WIKI_DIR):
        print(f"[FAIL] {WIKI_DIR}/ 디렉토리가 존재하지 않습니다.")
        sys.exit(1)

    # 현재 존재하는 모든 .md 파일명 수집 (확장자 제외)
    existing = {
        os.path.splitext(f)[0]
        for f in os.listdir(WIKI_DIR)
        if f.endswith(".md") and f not in SKIP_FILES
    }

    dead_count = 0
    stub_ref_count = 0
    checked_files = 0
    checked_links = 0

    for fname in sorted(os.listdir(WIKI_DIR)):
        if not fname.endswith(".md") or fname in SKIP_FILES:
            continue

        filepath = os.path.join(WIKI_DIR, fname)
        links = extract_links(filepath)
        if not links:
            continue

        checked_files += 1
        checked_links += len(links)

        for target, lineno in links:
            target_path = os.path.join(WIKI_DIR, f"{target}.md")

            if target not in existing:
                # 파일 자체가 없음 → FAIL
                errors.append(
                    f"[FAIL] 데드링크 — [[{target}]]\n"
                    f"       └─ {fname}:{lineno} 에서 참조, 파일 없음"
                )
                dead_count += 1
            elif is_stub(target_path):
                # 스텁으로만 존재 → WARN (ingest 정상 산출물)
                warnings.append(
                    f"[WARN] 스텁 참조 — [[{target}]]\n"
                    f"       └─ {fname}:{lineno} → 스텁 노트(미작성). /fill_stubs 실행 권장"
                )
                stub_ref_count += 1

    return checked_files, checked_links, dead_count, stub_ref_count


def main():
    checked_files, checked_links, dead_count, stub_ref_count = scan_wiki()

    print("=" * 55)
    print("  데드 링크 검사")
    print("=" * 55)
    print(f"  검사 파일 수 : {checked_files}")
    print(f"  검사 링크 수 : {checked_links}")
    print(f"  데드링크     : {dead_count}개  {'← CI 실패' if dead_count else '← 없음 ✅'}")
    print(f"  스텁 참조    : {stub_ref_count}개  {'← 경고' if stub_ref_count else '← 없음'}")
    print("=" * 55)
    print()

    if warnings:
        for w in warnings:
            print(w)
        print()

    if errors:
        for e in errors:
            print(e)
        print()
        print(f"❌ 데드링크 {dead_count}개 발견 — CI 실패")
        sys.exit(1)
    else:
        print("✅ 데드링크 검사 통과")
        sys.exit(0)


if __name__ == "__main__":
    main()
