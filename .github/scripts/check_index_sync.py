#!/usr/bin/env python3
"""
CI Check: index.md 동기화 검사

check_index_stats.py 와의 차이:
  - stats : 카테고리별 '개수'가 맞는지 검사  (숫자 비교)
  - sync  : '어떤 파일'이 등록됐는지 검사     (파일명 비교)

  개수는 같아도 다른 파일이 등록될 수 있음.
  예) 파일 A 삭제 + 파일 B 신규 생성 → 개수 동일 → stats 통과 → sync 실패

검증 항목:
  1. 디스크에 있지만 index.md 테이블에 없는 파일  → FAIL (LLM이 파일만 만들고 index 미등록)
  2. index.md 테이블에 있지만 디스크에 없는 파일  → FAIL (파일 삭제 후 index 미정리)
  3. 파일 유형과 테이블 섹션 불일치              → FAIL (예: @ 파일이 영구 노트 섹션에 등록)
"""

import os
import re
import sys

WIKI_DIR = "03_Wiki"
INDEX_FILE = os.path.join(WIKI_DIR, "index.md")
SKIP_FILES = {"index.md", "log.md", ".gitkeep"}

errors = []
warnings = []


def fail(msg: str):
    errors.append(f"[FAIL] {msg}")


def warn(msg: str):
    warnings.append(f"[WARN] {msg}")


# ──────────────────────────────────────────────
# 1. 실제 파일 스캔
# ──────────────────────────────────────────────
def scan_disk() -> dict[str, str]:
    """
    03_Wiki/ 실제 파일 스캔
    반환: {파일명(확장자 제외): 유형}  유형 = "lit" | "perm" | "moc"
    """
    if not os.path.isdir(WIKI_DIR):
        print(f"[FAIL] {WIKI_DIR}/ 디렉토리가 존재하지 않습니다.")
        sys.exit(1)

    result = {}
    for fname in os.listdir(WIKI_DIR):
        if not fname.endswith(".md") or fname in SKIP_FILES:
            continue
        stem = os.path.splitext(fname)[0]
        if fname.startswith("@"):
            result[stem] = "lit"
        elif fname.startswith("MOC_"):
            result[stem] = "moc"
        else:
            result[stem] = "perm"
    return result


# ──────────────────────────────────────────────
# 2. index.md 테이블 파싱
# ──────────────────────────────────────────────
def parse_index_tables() -> dict[str, str]:
    """
    index.md 테이블에서 등록된 파일명을 파싱
    반환: {파일명(확장자 제외): 섹션 유형}  유형 = "lit" | "perm" | "moc"
    """
    if not os.path.isfile(INDEX_FILE):
        print(f"[FAIL] {INDEX_FILE} 파일이 존재하지 않습니다.")
        sys.exit(1)

    with open(INDEX_FILE, encoding="utf-8") as f:
        content = f.read()

    # 섹션별로 분리
    # 마크다운 h2(##) 헤더로 분리
    sections = re.split(r"^## .+$", content, flags=re.MULTILINE)
    headers  = re.findall(r"^## .+$", content, flags=re.MULTILINE)

    # 헤더 키워드로 섹션 유형 판별
    def section_type(header: str) -> str | None:
        h = header.lower()
        if "문헌" in h or "literature" in h:
            return "lit"
        if "허브" in h or "moc" in h:
            return "moc"
        if "영구" in h or "permanent" in h:
            return "perm"
        return None

    registered: dict[str, str] = {}
    for header, body in zip(headers, sections[1:]):
        stype = section_type(header)
        if stype is None:
            continue
        # 테이블 행에서 [[파일명]] 추출
        for m in re.finditer(r"^\|\s*\[\[([^\]|#]+)", body, re.MULTILINE):
            fname = m.group(1).strip()
            registered[fname] = stype

    return registered


# ──────────────────────────────────────────────
# 3. 검증
# ──────────────────────────────────────────────
def validate(disk: dict[str, str], index: dict[str, str]):
    disk_set  = set(disk)
    index_set = set(index)

    only_disk  = disk_set - index_set   # 디스크에만 있음
    only_index = index_set - disk_set   # index에만 있음
    both       = disk_set & index_set   # 양쪽 모두 있음

    # ── 체크 A: 디스크에만 있는 파일 (index 미등록) ──
    for fname in sorted(only_disk):
        fail(
            f"index.md 미등록 — '{fname}.md'\n"
            f"       └─ 디스크에 존재하지만 index.md 테이블에 없음"
            f" (LLM이 파일만 생성하고 index 갱신 누락)"
        )

    # ── 체크 B: index에만 있는 파일 (디스크 없음) ──
    for fname in sorted(only_index):
        fail(
            f"파일 없음 — '{fname}.md'\n"
            f"       └─ index.md 테이블에 등록됐지만 디스크에 파일이 없음"
            f" (파일 삭제 후 index 미정리, 또는 파일명 오타)"
        )

    # ── 체크 C: 유형 불일치 (파일명은 맞지만 잘못된 섹션에 등록) ──
    type_label = {"lit": "문헌 노트(@)", "perm": "영구 노트", "moc": "MOC"}
    for fname in sorted(both):
        disk_type  = disk[fname]
        index_type = index[fname]
        if disk_type != index_type:
            fail(
                f"섹션 불일치 — '{fname}.md'\n"
                f"       └─ 파일 유형: {type_label[disk_type]}"
                f"  /  index.md 등록 섹션: {type_label[index_type]}"
            )

    # ── 요약 출력 ──
    print("=" * 55)
    print("  index.md 동기화 검사")
    print("=" * 55)
    print(f"  디스크 파일 수  : {len(disk_set)}")
    print(f"  index 등록 수   : {len(index_set)}")
    print(f"  index 미등록    : {len(only_disk)}개  {'← FAIL' if only_disk else '← 없음 ✅'}")
    print(f"  디스크 없음     : {len(only_index)}개  {'← FAIL' if only_index else '← 없음 ✅'}")
    print(f"  섹션 불일치     : {sum(1 for f in both if disk[f] != index[f])}개"
          f"  {'← FAIL' if any(disk[f] != index[f] for f in both) else '← 없음 ✅'}")
    print("=" * 55)


# ──────────────────────────────────────────────
# 4. 메인
# ──────────────────────────────────────────────
def main():
    disk  = scan_disk()
    index = parse_index_tables()
    validate(disk, index)

    print()
    if warnings:
        for w in warnings:
            print(w)
    if errors:
        for e in errors:
            print(e)
        print()
        print(f"❌ {len(errors)}개 오류 발견 — CI 실패")
        sys.exit(1)
    else:
        print("✅ index.md 동기화 검사 통과")
        sys.exit(0)


if __name__ == "__main__":
    main()
