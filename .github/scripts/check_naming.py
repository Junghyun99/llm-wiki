#!/usr/bin/env python3
"""
CI Check: 03_Wiki 파일명 명명 규칙 검사

CLAUDE.md / SKILL.md 기준 규칙:
  문헌 노트  : @원문_제목.md       (@로 시작, 내용 필수)
  영구 노트  : 개념_이름.md        (접두사 없음)
  MOC 노트   : MOC_주제명.md       (MOC_로 시작, 내용 필수)
  공통       : 하위 폴더 금지 / 공백 금지 / 유효 문자만 허용

검사 항목:
  R1. 하위 폴더 금지
  R2. 파일명에 공백 포함 금지
  R3. 유효 문자 외 특수문자 금지  (허용: 한글·영문·숫자·_·-)
  R4. @ 는 첫 글자에만 허용      (중간 위치 금지)
  R5. @ 뒤 내용 필수             (@.md 금지)
  R6. MOC_ 뒤 내용 필수          (MOC_.md 금지)
  R7. 이중 접두사 금지            (@MOC_… / MOC_@… 등)
  R8. 영구 노트 오접두사 금지     (Note_ / Lit_ / Stub_ / Temp_ 등)
"""

import os
import re
import sys

WIKI_DIR   = "03_Wiki"
SKIP_FILES = {"index.md", "log.md", ".gitkeep"}

# R8: 영구 노트에서 허용하지 않는 알려진 오접두사 (소문자 비교)
BANNED_PREFIXES = [
    "note_", "lit_", "stub_", "temp_", "tmp_", "draft_",
    "wip_", "archive_", "old_", "ref_",
]

errors   = []
warnings = []


def fail(fname: str, rule: str, detail: str):
    errors.append(f"[FAIL] {fname}\n       └─ [{rule}] {detail}")


def warn(fname: str, rule: str, detail: str):
    warnings.append(f"[WARN] {fname}\n       └─ [{rule}] {detail}")


# ──────────────────────────────────────────────
# 개별 규칙 검사 함수
# ──────────────────────────────────────────────
def check_valid_chars(stem: str, fname: str):
    """R3: 허용 문자(한글·영문·숫자·_·-·@) 외 특수문자 금지"""
    invalid = re.findall(r"[^\uAC00-\uD7A3a-zA-Z0-9_\-@]", stem)
    if invalid:
        unique = sorted(set(invalid))
        fail(fname, "R3", f"허용되지 않는 문자 포함: {unique}  "
                          f"(허용: 한글·영문·숫자·_·-)")


def check_at_position(stem: str, fname: str):
    """R4: @ 는 첫 글자에만 허용"""
    if "@" in stem[1:]:
        fail(fname, "R4", f"@ 가 첫 글자 외 위치에 있음: '{stem}'")


def check_at_content(stem: str, fname: str):
    """R5: @ 로 시작하면 뒤에 내용이 반드시 있어야 함"""
    if stem.startswith("@") and len(stem) == 1:
        fail(fname, "R5", "@ 뒤에 파일명 내용이 없음 ('@.md' 불가)")


def check_moc_content(stem: str, fname: str):
    """R6: MOC_ 로 시작하면 _ 뒤에 내용이 반드시 있어야 함"""
    if stem.upper().startswith("MOC_") and len(stem) <= 4:
        fail(fname, "R6", "MOC_ 뒤에 주제명이 없음 ('MOC_.md' 불가)")


def check_double_prefix(stem: str, fname: str):
    """R7: 이중 접두사 금지"""
    patterns = [
        (r"^@MOC_",  "@MOC_… 형식"),
        (r"^MOC_@",  "MOC_@… 형식"),
        (r"^@@",     "@@ 중복 @ 형식"),
    ]
    for pattern, desc in patterns:
        if re.match(pattern, stem, re.IGNORECASE):
            fail(fname, "R7", f"이중 접두사 금지: {desc}")
            return


def check_banned_prefix(stem: str, fname: str):
    """R8: 영구 노트 오접두사 금지 (@ / MOC_ 가 아닌 파일에만 적용)"""
    if stem.startswith("@") or stem.upper().startswith("MOC_"):
        return
    lower = stem.lower()
    for bp in BANNED_PREFIXES:
        if lower.startswith(bp):
            fail(fname, "R8", f"영구 노트 오접두사 감지: '{stem[:len(bp)]}…'  "
                              f"(CLAUDE.md: 영구 노트는 접두사 없음)")
            return


def check_file(fname: str):
    """단일 파일에 대해 모든 규칙 적용"""
    stem = os.path.splitext(fname)[0]   # 확장자 제거

    # R2: 공백
    if " " in fname:
        fail(fname, "R2", "파일명에 공백 포함  (공백 대신 _ 사용)")

    check_valid_chars(stem, fname)
    check_at_position(stem, fname)
    check_at_content(stem, fname)
    check_moc_content(stem, fname)
    check_double_prefix(stem, fname)
    check_banned_prefix(stem, fname)


# ──────────────────────────────────────────────
# 디렉토리 스캔
# ──────────────────────────────────────────────
def scan():
    if not os.path.isdir(WIKI_DIR):
        print(f"[FAIL] {WIKI_DIR}/ 디렉토리가 존재하지 않습니다.")
        sys.exit(1)

    checked = 0

    for entry in sorted(os.scandir(WIKI_DIR), key=lambda e: e.name):
        # R1: 하위 폴더 금지
        if entry.is_dir():
            if entry.name == ".git":
                continue
            fail(entry.name + "/", "R1",
                 f"03_Wiki/ 내 하위 폴더 금지  (CLAUDE.md: 절대적 수평 구조)")
            continue

        if entry.name in SKIP_FILES or not entry.name.endswith(".md"):
            continue

        check_file(entry.name)
        checked += 1

    return checked


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main():
    checked = scan()

    # 유형별 집계
    rule_counts: dict[str, int] = {}
    for e in errors:
        m = re.search(r"\[(R\d+)\]", e)
        if m:
            rule_counts[m.group(1)] = rule_counts.get(m.group(1), 0) + 1

    print("=" * 55)
    print("  파일명 명명 규칙 검사")
    print("=" * 55)
    print(f"  검사 파일 수  : {checked}")
    print(f"  위반 파일 수  : {len(errors)}개  {'← CI 실패' if errors else '← 없음 ✅'}")
    if rule_counts:
        for rule, cnt in sorted(rule_counts.items()):
            print(f"    {rule}: {cnt}건")
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
        print(f"❌ 명명 규칙 위반 {len(errors)}건 — CI 실패")
        sys.exit(1)
    else:
        print("✅ 파일명 명명 규칙 검사 통과")
        sys.exit(0)


if __name__ == "__main__":
    main()
