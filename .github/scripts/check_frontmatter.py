#!/usr/bin/env python3
"""
CI Check: 프론트매터(Frontmatter) 필수 필드 검사

SKILL.md 기준 유형별 필수 필드:
  문헌 노트 (@)  : aliases / tags(source/* 포함) / date_processed / author
  영구 노트      : aliases / tags(permanent 포함) / date_created   / source
  MOC 노트       : aliases / tags(MOC 포함)       / date_created
  스텁 (todo/fill이 tags에 포함된 영구 노트): 영구 노트 규칙 동일, source 빈값 허용

공통 검사:
  - 프론트매터 블록(--- ... ---) 자체가 존재하는지
  - 날짜 필드가 YYYY-MM-DD 형식인지
  - tags 필드가 리스트 형식인지
  - aliases 필드가 리스트 형식인지

스텁 본문 무결성 검사 (체크 7 흡수):
  - todo/fill 태그 있음 + 실질 내용 존재 → WARN (fill_stubs 후 태그 제거 누락)
  - todo/fill 태그 없음 + 본문 비어있음  → FAIL  (빈 영구 노트)
"""

import os
import re
import sys

WIKI_DIR   = "03_Wiki"
SKIP_FILES = {"index.md", "log.md", ".gitkeep"}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STUB_WARNING_RE = re.compile(r"^>\s*⚠️")   # 스텁 자동생성 경고문

errors   = []
warnings = []


def fail(fname: str, detail: str):
    errors.append(f"[FAIL] {fname}\n       └─ {detail}")


def warn(fname: str, detail: str):
    warnings.append(f"[WARN] {fname}\n       └─ {detail}")


# ──────────────────────────────────────────────
# 프론트매터 파싱
# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# 본문 파싱
# ──────────────────────────────────────────────
def parse_body(filepath: str) -> list[str]:
    """프론트매터 이후 본문 라인을 반환"""
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    if not lines or lines[0].strip() != "---":
        return lines   # 프론트매터 없으면 전체가 본문

    in_fm = True
    body  = []
    for line in lines[1:]:
        if in_fm and line.strip() == "---":
            in_fm = False
            continue
        if not in_fm:
            body.append(line.rstrip())
    return body


def meaningful_lines(body: list[str]) -> list[str]:
    """
    본문에서 실질 내용 라인만 추출.
    제외 대상: 빈 줄 / # 헤딩 / 스텁 경고문(> ⚠️...)
    """
    result = []
    for line in body:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if STUB_WARNING_RE.match(stripped):
            continue
        result.append(stripped)
    return result


def parse_frontmatter(filepath: str) -> dict | None:
    """
    파일에서 YAML 프론트매터를 파싱해 dict 반환.
    프론트매터가 없으면 None 반환.
    복잡한 YAML은 직접 파싱 (PyYAML 미설치 환경 대응).
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        warnings.append(f"[WARN] {os.path.basename(filepath)} — 파일 읽기 실패: {e}")
        return None

    if not lines or lines[0].strip() != "---":
        return None   # 프론트매터 없음

    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)

    if not fm_lines:
        return None

    return _parse_yaml_simple(fm_lines)


def _parse_yaml_simple(lines: list[str]) -> dict:
    """
    단순 key: value / key: [list] YAML 파서.
    중첩 구조 불필요 — 프론트매터 수준만 처리.
    """
    result = {}
    current_key = None
    in_list = False

    for raw in lines:
        line = raw.rstrip()

        # 리스트 항목
        if in_list and line.startswith("  - "):
            result[current_key].append(line[4:].strip())
            continue

        # 인라인 리스트: key: [a, b, c]
        m = re.match(r'^(\w+):\s*\[([^\]]*)\]\s*$', line)
        if m:
            key = m.group(1)
            items = [x.strip().strip('"\'') for x in m.group(2).split(",") if x.strip()]
            result[key] = items
            in_list = False
            current_key = key
            continue

        # key: value
        m = re.match(r'^(\w+):\s*(.*)', line)
        if m:
            key   = m.group(1)
            value = m.group(2).strip().strip('"\'')
            in_list = False
            current_key = key
            if value == "":
                result[key] = ""   # 빈 값
            elif value == "[]":
                result[key] = []
            else:
                result[key] = value
            continue

        # 멀티라인 리스트 시작 (값 없이 다음 줄이 - 로 시작)
        if line.endswith(":"):
            key = line[:-1].strip()
            result[key] = []
            current_key = key
            in_list = True
            continue

    return result


# ──────────────────────────────────────────────
# 유형 판별
# ──────────────────────────────────────────────
def note_type(fname: str) -> str:
    if fname.startswith("@"):
        return "lit"
    if fname.upper().startswith("MOC_"):
        return "moc"
    return "perm"


def is_stub(fm: dict) -> bool:
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        return "todo/fill" in tags
    return "todo/fill" in str(tags)


# ──────────────────────────────────────────────
# 공통 검사
# ──────────────────────────────────────────────
def check_required_field(fname: str, fm: dict, field: str, label: str):
    """필드 존재 여부"""
    if field not in fm:
        fail(fname, f"필수 필드 누락: '{field}'  ({label})")
        return False
    return True


def check_date_format(fname: str, fm: dict, field: str):
    """날짜 필드 YYYY-MM-DD 형식 검사"""
    val = fm.get(field)
    if val and isinstance(val, str) and not DATE_RE.match(val):
        fail(fname, f"날짜 형식 오류: '{field}: {val}'  (올바른 형식: YYYY-MM-DD)")


def check_list_field(fname: str, fm: dict, field: str):
    """리스트 형식 검사"""
    val = fm.get(field)
    if val is not None and not isinstance(val, list):
        fail(fname, f"'{field}' 는 리스트 형식이어야 함  (현재값: {repr(val)})")


def check_tag_contains(fname: str, fm: dict, required_tag: str, hint: str):
    """tags 리스트에 특정 태그 포함 여부"""
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        tags_lower = [t.lower() for t in tags]
        if required_tag.lower() not in tags_lower:
            fail(fname, f"tags 에 '{required_tag}' 태그 누락  ({hint})")
    else:
        fail(fname, f"tags 필드가 리스트가 아님 — '{required_tag}' 태그 확인 불가")


def check_source_tag(fname: str, fm: dict):
    """문헌 노트 tags 에 source/* 태그 포함 여부"""
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        has_source = any(str(t).lower().startswith("source/") for t in tags)
        if not has_source:
            warn(fname, "tags 에 'source/*' 태그 없음  (예: source/pdf, source/article)")
    else:
        fail(fname, "tags 필드가 리스트가 아님")


def check_stub_integrity(fname: str, fm: dict, body: list[str]):
    """
    스텁 본문 무결성 검사 (체크 7)

    케이스 1: todo/fill 태그 있음 + 실질 내용 > 5줄
      → fill_stubs 실행 후 Step4(태그 제거)를 누락한 것으로 판단 → WARN

    케이스 2: todo/fill 태그 없음 + 실질 내용 == 0줄
      → 내용이 없는 영구 노트 (스텁도 아님) → FAIL
    """
    stub    = is_stub(fm)
    content = meaningful_lines(body)

    if stub and len(content) > 5:
        warn(
            fname,
            f"todo/fill 태그가 있지만 실질 내용 {len(content)}줄 존재\n"
            f"       └─ fill_stubs 실행 후 태그 제거(Step 4) 누락 가능성\n"
            f"       └─ 확인 후 tags 에서 'todo/fill' 제거 필요"
        )

    if not stub and len(content) == 0:
        fail(
            fname,
            "본문 내용 없음 (빈 영구 노트)\n"
            f"       └─ todo/fill 태그도 없어 스텁으로 인식되지 않음\n"
            f"       └─ 내용을 채우거나 tags 에 'todo/fill' 추가 필요"
        )


# ──────────────────────────────────────────────
# 유형별 검사
# ──────────────────────────────────────────────
def check_lit(fname: str, fm: dict):
    """문헌 노트 (@) 필수 필드 검사"""
    check_list_field(fname, fm, "aliases")
    check_list_field(fname, fm, "tags")
    check_required_field(fname, fm, "aliases",        "문헌 노트 필수")
    check_required_field(fname, fm, "tags",           "문헌 노트 필수")
    check_required_field(fname, fm, "date_processed", "문헌 노트 필수")
    check_required_field(fname, fm, "author",         "문헌 노트 필수")
    check_date_format(fname, fm, "date_processed")
    check_source_tag(fname, fm)


def check_perm(fname: str, fm: dict, body: list[str]):
    """영구 노트 필수 필드 검사 (스텁 포함)"""
    stub = is_stub(fm)

    check_list_field(fname, fm, "aliases")
    check_list_field(fname, fm, "tags")
    check_required_field(fname, fm, "aliases",      "영구 노트 필수")
    check_required_field(fname, fm, "tags",         "영구 노트 필수")
    check_required_field(fname, fm, "date_created", "영구 노트 필수")
    check_required_field(fname, fm, "source",       "영구 노트 필수")
    check_date_format(fname, fm, "date_created")
    check_tag_contains(fname, fm, "permanent",
                       "영구 노트는 tags 에 permanent 포함 필수")

    # source 필드: 스텁은 빈 값 허용, 일반 영구 노트는 권장
    source = fm.get("source", "")
    if not stub and (source == "" or source is None):
        warn(fname, "source 필드가 비어있음  (출처 문헌 노트 링크 권장: \"[[@파일명]]\")")

    # 스텁 본문 무결성 검사
    check_stub_integrity(fname, fm, body)


def check_moc(fname: str, fm: dict):
    """MOC 노트 필수 필드 검사"""
    check_list_field(fname, fm, "aliases")
    check_list_field(fname, fm, "tags")
    check_required_field(fname, fm, "aliases",      "MOC 노트 필수")
    check_required_field(fname, fm, "tags",         "MOC 노트 필수")
    check_required_field(fname, fm, "date_created", "MOC 노트 필수")
    check_date_format(fname, fm, "date_created")
    check_tag_contains(fname, fm, "MOC",
                       "MOC 노트는 tags 에 MOC 포함 필수")


# ──────────────────────────────────────────────
# 파일 단위 진입점
# ──────────────────────────────────────────────
def check_file(fname: str):
    filepath = os.path.join(WIKI_DIR, fname)
    fm   = parse_frontmatter(filepath)
    body = parse_body(filepath)

    # 프론트매터 블록 자체 없음
    if fm is None:
        fail(fname, "프론트매터(--- ... ---) 블록이 없음")
        return

    ntype = note_type(fname)
    if ntype == "lit":
        check_lit(fname, fm)
    elif ntype == "moc":
        check_moc(fname, fm)
    else:
        check_perm(fname, fm, body)


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main():
    if not os.path.isdir(WIKI_DIR):
        print(f"[FAIL] {WIKI_DIR}/ 디렉토리가 존재하지 않습니다.")
        sys.exit(1)

    checked = 0
    for fname in sorted(os.listdir(WIKI_DIR)):
        if not fname.endswith(".md") or fname in SKIP_FILES:
            continue
        check_file(fname)
        checked += 1

    print("=" * 55)
    print("  프론트매터 필수 필드 검사")
    print("=" * 55)
    print(f"  검사 파일 수  : {checked}")
    print(f"  오류          : {len(errors)}개  {'← CI 실패' if errors else '← 없음 ✅'}")
    print(f"  경고          : {len(warnings)}개")
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
        print(f"❌ 프론트매터 오류 {len(errors)}건 — CI 실패")
        sys.exit(1)
    else:
        print("✅ 프론트매터 필수 필드 검사 통과")
        sys.exit(0)


if __name__ == "__main__":
    main()
