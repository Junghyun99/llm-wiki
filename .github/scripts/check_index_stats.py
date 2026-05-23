#!/usr/bin/env python3
"""
CI Check: index.md 통계 섹션 정합성 검사

검증 항목:
  1. 실제 파일 수 vs index.md 테이블 행 수 일치 여부
  2. index.md 테이블 행 수 vs 통계 섹션 숫자 일치 여부
  3. 통계 섹션 내 합산(문헌 + 영구 + MOC == 총 노트 수) 일치 여부
  4. 스텁 노트 수(todo/fill 태그) vs 통계 섹션 스텁 숫자 일치 여부
"""

import os
import re
import sys

WIKI_DIR = "03_Wiki"
INDEX_FILE = os.path.join(WIKI_DIR, "index.md")
EXCLUDE_FILES = {"index.md", "log.md", ".gitkeep"}

errors = []
warnings = []


def fail(msg: str):
    errors.append(f"[FAIL] {msg}")


def warn(msg: str):
    warnings.append(f"[WARN] {msg}")


# ──────────────────────────────────────────────
# 1. 실제 파일 스캔
# ──────────────────────────────────────────────
def scan_wiki_files():
    """03_Wiki/ 디렉토리에서 실제 .md 파일을 분류해 반환"""
    if not os.path.isdir(WIKI_DIR):
        fail(f"03_Wiki/ 디렉토리가 존재하지 않습니다.")
        sys.exit(1)

    lit, perm, moc = [], [], []
    for fname in os.listdir(WIKI_DIR):
        if not fname.endswith(".md") or fname in EXCLUDE_FILES:
            continue
        if fname.startswith("@"):
            lit.append(fname)
        elif fname.startswith("MOC_"):
            moc.append(fname)
        else:
            perm.append(fname)
    return lit, perm, moc


# ──────────────────────────────────────────────
# 2. index.md 파싱
# ──────────────────────────────────────────────
def parse_index():
    """index.md에서 테이블 행 수와 통계 섹션 숫자를 파싱"""
    if not os.path.isfile(INDEX_FILE):
        fail("03_Wiki/index.md 파일이 존재하지 않습니다.")
        sys.exit(1)

    with open(INDEX_FILE, encoding="utf-8") as f:
        content = f.read()

    # --- 테이블 행 카운트 ---
    # 문헌 노트 테이블: `@` 로 시작하는 [[링크]] 행
    table_lit = len(re.findall(r"^\|\s*\[\[@", content, re.MULTILINE))

    # 영구 노트 테이블: `[[` 로 시작하지만 `@`, `MOC_` 가 아닌 행
    table_perm = len(re.findall(r"^\|\s*\[\[(?!@|MOC_)", content, re.MULTILINE))

    # MOC 테이블: `[[MOC_` 로 시작하는 행
    table_moc = len(re.findall(r"^\|\s*\[\[MOC_", content, re.MULTILINE))

    # 스텁: todo/fill 태그가 있는 테이블 행 수
    table_stub = len(re.findall(r"todo/fill", content))

    # --- 통계 섹션 파싱 ---
    # 예: "- 총 노트 수: 24"
    stat_total = _parse_stat(content, r"총 노트 수\s*:\s*(\d+)")
    # 예: "- 문헌 노트: 5 / 영구 노트: 17 (스텁 1 포함) / MOC: 2"
    stat_lit   = _parse_stat(content, r"문헌 노트\s*:\s*(\d+)")
    stat_perm  = _parse_stat(content, r"영구 노트\s*:\s*(\d+)")
    stat_stub  = _parse_stat(content, r"스텁\s*(\d+)\s*포함")
    stat_moc   = _parse_stat(content, r"MOC\s*:\s*(\d+)")

    return {
        "table": {"lit": table_lit, "perm": table_perm, "moc": table_moc, "stub": table_stub},
        "stat":  {"total": stat_total, "lit": stat_lit, "perm": stat_perm,
                  "stub": stat_stub, "moc": stat_moc},
    }


def _parse_stat(content: str, pattern: str) -> int | None:
    m = re.search(pattern, content)
    return int(m.group(1)) if m else None


# ──────────────────────────────────────────────
# 3. 검증
# ──────────────────────────────────────────────
def validate(disk, index):
    disk_lit, disk_perm, disk_moc = disk
    table = index["table"]
    stat  = index["stat"]

    disk_total = len(disk_lit) + len(disk_perm) + len(disk_moc)

    print("=" * 55)
    print("  index.md 통계 정합성 검사")
    print("=" * 55)
    print(f"{'항목':<20} {'디스크':>6} {'테이블':>6} {'통계섹션':>8}")
    print("-" * 55)
    print(f"{'문헌 노트(@)':<20} {len(disk_lit):>6} {table['lit']:>6} {str(stat['lit']):>8}")
    print(f"{'영구 노트':<20} {len(disk_perm):>6} {table['perm']:>6} {str(stat['perm']):>8}")
    print(f"{'MOC':<20} {len(disk_moc):>6} {table['moc']:>6} {str(stat['moc']):>8}")
    print(f"{'합계':<20} {disk_total:>6} {table['lit']+table['perm']+table['moc']:>6} {str(stat['total']):>8}")
    print(f"{'스텁(todo/fill)':<20} {'':>6} {table['stub']:>6} {str(stat['stub']):>8}")
    print("=" * 55)

    # ── 체크 A: 디스크 vs 테이블 ──
    if len(disk_lit) != table["lit"]:
        fail(f"문헌 노트 — 디스크({len(disk_lit)}) ≠ index.md 테이블({table['lit']})")
    if len(disk_perm) != table["perm"]:
        fail(f"영구 노트 — 디스크({len(disk_perm)}) ≠ index.md 테이블({table['perm']})"
             f"\n         └─ LLM이 파일은 생성했지만 테이블에 행을 추가하지 않았을 가능성")
    if len(disk_moc) != table["moc"]:
        fail(f"MOC — 디스크({len(disk_moc)}) ≠ index.md 테이블({table['moc']})")

    # ── 체크 B: 테이블 vs 통계 섹션 ──
    _check_stat("문헌 노트", table["lit"], stat["lit"],
                hint="테이블에 행은 추가됐지만 통계 숫자가 갱신되지 않음")
    _check_stat("영구 노트", table["perm"], stat["perm"],
                hint="영구 노트 생성 후 통계 더하기 누락 (알려진 LLM 버그)")
    _check_stat("MOC", table["moc"], stat["moc"],
                hint="MOC 테이블 행과 통계 섹션 불일치")
    _check_stat("스텁(todo/fill)", table["stub"], stat["stub"],
                hint="스텁 완성 후 통계 숫자 미갱신")

    # ── 체크 C: 통계 섹션 내부 합산 오류 ──
    if None not in (stat["lit"], stat["perm"], stat["moc"], stat["total"]):
        calc_total = stat["lit"] + stat["perm"] + stat["moc"]
        if calc_total != stat["total"]:
            fail(
                f"통계 섹션 합산 오류 — "
                f"문헌({stat['lit']}) + 영구({stat['perm']}) + MOC({stat['moc']}) "
                f"= {calc_total} ≠ 총 노트 수({stat['total']})"
            )
    else:
        warn("통계 섹션에서 일부 숫자를 파싱하지 못했습니다. index.md 형식을 확인하세요.")


def _check_stat(label: str, table_val: int, stat_val: int | None, hint: str):
    if stat_val is None:
        warn(f"{label} — 통계 섹션에서 숫자를 파싱하지 못했습니다.")
        return
    if table_val != stat_val:
        fail(f"{label} — 테이블 행({table_val}) ≠ 통계 섹션({stat_val})\n         └─ {hint}")


# ──────────────────────────────────────────────
# 4. 메인
# ──────────────────────────────────────────────
def main():
    disk = scan_wiki_files()
    index = parse_index()
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
        print("✅ 통계 정합성 검사 통과")
        sys.exit(0)


if __name__ == "__main__":
    main()
