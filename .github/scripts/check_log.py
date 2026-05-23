#!/usr/bin/env python3
"""
CI Check: log.md Append-only 위반 및 형식 검사

[검사 A] Append-only 위반 (git diff 기반)
  - 직전 커밋 대비 기존 라인이 삭제·수정됐으면 FAIL
  - git 히스토리가 없는 환경(최초 커밋 등)은 SKIP

[검사 B] 로그 항목 형식 검사 (파싱 기반)
  - 헤더 형식: ## [YYYY-MM-DD] type | description
  - 작업 유형: ingest / fill-stubs / lint / query / maintenance
  - 날짜 순서: 헤더 날짜가 비내림차순(non-decreasing)
  - 빈 항목: 헤더만 있고 내용이 없으면 WARN
"""

import os
import re
import subprocess
import sys
from datetime import date

LOG_FILE   = os.path.join("03_Wiki", "log.md")
DATE_RE    = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADER_RE  = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (\S+) \| (.+)$")
VALID_TYPES = {"ingest", "fill-stubs", "lint", "query", "maintenance"}

errors   = []
warnings = []


def fail(msg: str):
    errors.append(f"[FAIL] {msg}")


def warn(msg: str):
    warnings.append(f"[WARN] {msg}")


# ──────────────────────────────────────────────
# 검사 A: git diff 기반 append-only 위반 탐지
# ──────────────────────────────────────────────
def check_append_only():
    """
    git diff HEAD~1 로 직전 커밋 대비 삭제된 라인을 검사.
    삭제 라인(- 로 시작)이 존재하면 기존 내용이 수정된 것 → FAIL
    """
    # git 사용 가능 여부 확인
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            check=True, capture_output=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        warn("git 환경이 없어 append-only 검사를 건너뜁니다.")
        return

    # 커밋이 1개뿐이면 비교 대상 없음
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or int(result.stdout.strip()) < 2:
        warn("커밋 히스토리가 1개 이하 — append-only 검사를 건너뜁니다.")
        return

    # log.md 가 이번 커밋에서 변경됐는지 확인
    changed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", LOG_FILE],
        capture_output=True, text=True
    )
    if LOG_FILE not in changed.stdout:
        return   # log.md 변경 없음, 검사 불필요

    # 삭제된 라인 추출
    diff = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--", LOG_FILE],
        capture_output=True, text=True
    )

    deleted_lines = []
    for line in diff.stdout.splitlines():
        # diff 헤더(--- a/... / +++ b/...) 제외, 실제 삭제 라인만
        if line.startswith("-") and not line.startswith("---"):
            deleted_lines.append(line[1:].rstrip())

    if deleted_lines:
        preview = "\n         ".join(deleted_lines[:5])
        suffix  = f"\n         ... 외 {len(deleted_lines)-5}줄" if len(deleted_lines) > 5 else ""
        fail(
            f"log.md Append-only 위반 — 기존 {len(deleted_lines)}줄이 삭제·수정됨\n"
            f"         삭제된 내용:\n"
            f"         {preview}{suffix}\n"
            f"         └─ log.md 는 추가만 허용. 기존 항목 수정·삭제 금지"
        )
    else:
        print("  [A] Append-only 위반 없음 ✅")


# ──────────────────────────────────────────────
# 검사 B: 로그 항목 형식 파싱 검사
# ──────────────────────────────────────────────
def check_log_format():
    """log.md 전체를 파싱하여 헤더 형식·날짜 순서·작업 유형 검사"""
    if not os.path.isfile(LOG_FILE):
        fail(f"{LOG_FILE} 파일이 존재하지 않습니다.")
        return

    with open(LOG_FILE, encoding="utf-8") as f:
        lines = f.readlines()

    entries      = []   # (lineno, date_str, work_type, description, has_body)
    current_entry = None
    current_body  = []

    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip()

        m = HEADER_RE.match(line)
        if m:
            # 이전 항목 저장
            if current_entry:
                entries.append((*current_entry, bool(current_body)))
            current_entry = (lineno, m.group(1), m.group(2), m.group(3))
            current_body  = []
        elif current_entry and line.strip() and not line.startswith("#"):
            current_body.append(line)

    # 마지막 항목 저장
    if current_entry:
        entries.append((*current_entry, bool(current_body)))

    if not entries:
        warn("log.md 에 항목이 없습니다.")
        return

    prev_date = None
    for lineno, date_str, work_type, desc, has_body in entries:

        # 날짜 형식
        if not DATE_RE.match(date_str):
            fail(f"log.md:{lineno} — 날짜 형식 오류: '[{date_str}]'  (올바른 형식: YYYY-MM-DD)")

        # 미래 날짜
        try:
            entry_date = date.fromisoformat(date_str)
            if entry_date > date.today():
                warn(f"log.md:{lineno} — 미래 날짜 감지: [{date_str}]")
        except ValueError:
            pass

        # 작업 유형
        if work_type not in VALID_TYPES:
            fail(
                f"log.md:{lineno} — 알 수 없는 작업 유형: '{work_type}'\n"
                f"         └─ 허용 유형: {', '.join(sorted(VALID_TYPES))}"
            )

        # 날짜 순서 (비내림차순)
        if prev_date and date_str < prev_date:
            fail(
                f"log.md:{lineno} — 날짜 역순 감지: [{date_str}] < 이전 항목 [{prev_date}]\n"
                f"         └─ 항목은 시간 순으로만 추가되어야 함"
            )
        prev_date = date_str

        # 빈 항목
        if not has_body:
            warn(f"log.md:{lineno} — 헤더만 있고 내용 없음: '## [{date_str}] {work_type} | {desc}'")

    print(f"  [B] 형식 검사 완료 — 총 {len(entries)}개 항목")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  log.md Append-only 및 형식 검사")
    print("=" * 55)

    check_append_only()
    check_log_format()

    print(f"  오류: {len(errors)}개  {'← CI 실패' if errors else '← 없음 ✅'}")
    print(f"  경고: {len(warnings)}개")
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
        print(f"❌ log.md 검사 {len(errors)}건 실패 — CI 실패")
        sys.exit(1)
    else:
        print("✅ log.md 검사 통과")
        sys.exit(0)


if __name__ == "__main__":
    main()
