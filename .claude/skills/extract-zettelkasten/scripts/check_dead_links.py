#!/usr/bin/env python3
"""
check_dead_links.py
-------------------
extract-zettelkasten 스킬 실행 후, 방금 생성된 노트들의 [[링크]]를 검사하여
존재하지 않는 링크 대상을 스텁(stub) 파일로 자동 생성한다.

사용법:
  python check_dead_links.py --files "파일A.md,파일B.md" --date "2026-05-23"

인자:
  --files   방금 생성된 파일명 목록 (쉼표 구분, 03_Wiki/ 기준 파일명)
  --date    오늘 날짜 (YYYY-MM-DD, 생략 시 오늘 날짜 자동 사용)
  --dry-run 실제 파일 생성 없이 결과만 출력
"""

import argparse
import base64
import json
import re
import sys
from datetime import date
from urllib import request, error, parse

# ── 설정 ──────────────────────────────────────────────────────────────────────
REPO        = "Junghyun99/llm-wiki"
WIKI_DIR    = "03_Wiki"
TOKEN_FILE  = ".claude/scripts/github_pat.txt"  # 레포 내 PAT 파일 경로 (옵션)

# 스텁 제외 패턴: @문헌노트, MOC_ 허브노트
EXCLUDE_PREFIXES = ("@", "MOC_")

# ── GitHub API 헬퍼 ───────────────────────────────────────────────────────────

class GitHubAPI:
    BASE = "https://api.github.com"

    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo  = repo

    def _headers(self) -> dict:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }

    def _req(self, method: str, path: str, body: dict | None = None):
        encoded = parse.quote(path, safe="/")
        url  = f"{self.BASE}/repos/{self.repo}/contents/{encoded}"
        data = json.dumps(body).encode() if body else None
        req  = request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with request.urlopen(req) as resp:
                return json.loads(resp.read()), resp.status
        except error.HTTPError as e:
            return json.loads(e.read()), e.code

    def get_file(self, path: str) -> tuple[str | None, str | None]:
        """(content, sha) 반환. 없으면 (None, None)"""
        body, status = self._req("GET", path)
        if status != 200:
            return None, None
        content = base64.b64decode(body["content"]).decode("utf-8")
        return content, body["sha"]

    def put_file(self, path: str, content: str, message: str, sha: str | None = None):
        """파일 생성(sha=None) 또는 업데이트(sha 전달)"""
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode(),
        }
        if sha:
            payload["sha"] = sha
        body, status = self._req("PUT", path, payload)
        return status in (200, 201)

    def file_exists(self, path: str) -> bool:
        _, status = self._req("GET", path)
        return status == 200


# ── 링크 파싱 ─────────────────────────────────────────────────────────────────

def extract_links(content: str) -> set[str]:
    """마크다운 본문에서 [[링크명]] 추출 (중첩 없는 단순 패턴)"""
    raw = re.findall(r"\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]", content)
    links = set()
    for link in raw:
        link = link.strip()
        # 별칭(|) 앞부분만, 섹션(#) 앞부분만
        link = link.split("|")[0].split("#")[0].strip()
        if not link:
            continue
        # 제외 패턴
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

INDEX_ROW_TEMPLATE = "| [[{name}]] | ⚠️ 스텁(미작성) | {date} | todo/fill |"

def update_index(content: str, stubs: list[str], today: str) -> str:
    """## 🧠 영구 노트 테이블 마지막 행 뒤에 스텁 행 삽입"""
    rows = "\n".join(INDEX_ROW_TEMPLATE.format(name=s, date=today) for s in stubs)

    # 테이블 마지막 줄 다음에 삽입 (--- 구분선 또는 다음 ## 바로 앞)
    # "## 🧠 영구 노트" 섹션을 찾아 다음 "---" 또는 "## " 직전에 추가
    pattern = r"(## 🧠 영구 노트.*?(?=\n---|\n## |\Z))"
    match   = re.search(pattern, content, re.DOTALL)
    if match:
        section_end = match.end()
        content = content[:section_end] + "\n" + rows + content[section_end:]
    else:
        # 섹션을 못 찾으면 파일 끝에 추가
        content += "\n" + rows + "\n"

    # 📊 통계 업데이트
    stub_count = len(stubs)
    content = _update_stats(content, stub_count, today)
    return content


def _update_stats(content: str, added: int, today: str) -> str:
    """통계 블록의 총 노트 수, 영구 노트 수, 마지막 업데이트일 갱신"""
    def increment(m):
        return str(int(m.group(1)) + added)

    content = re.sub(r"(총 노트 수: )(\d+)",
                     lambda m: m.group(1) + str(int(m.group(2)) + added), content)
    content = re.sub(r"(영구 노트: )(\d+)",
                     lambda m: m.group(1) + str(int(m.group(2)) + added), content)
    content = re.sub(r"(마지막 업데이트: )\d{4}-\d{2}-\d{2}",
                     lambda m: m.group(1) + today, content)
    return content


# ── log.md 업데이트 ───────────────────────────────────────────────────────────

def update_log(content: str, stubs: list[str]) -> str:
    """마지막 ingest 블록에 '스텁 생성: N건' 줄 추가"""
    stub_lines = "\n".join(f"  - `{s}.md`" for s in stubs)
    addition   = f"- 스텁 생성: {len(stubs)}건\n{stub_lines}"

    # 마지막 ## [...] ingest 블록의 끝(다음 ## 또는 EOF) 직전에 삽입
    entries = list(re.finditer(r"^## \[", content, re.MULTILINE))
    if not entries:
        return content + "\n" + addition + "\n"

    last_start = entries[-1].start()
    # 마지막 블록의 끝 위치 탐색
    next_entry = re.search(r"^## \[", content[last_start + 1:], re.MULTILINE)
    if next_entry:
        insert_pos = last_start + 1 + next_entry.start()
    else:
        insert_pos = len(content)

    # 블록 끝 공백 정리 후 추가
    block      = content[last_start:insert_pos].rstrip()
    rest       = content[insert_pos:]
    return content[:last_start] + block + "\n" + addition + "\n" + rest


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Zettelkasten dead-link checker")
    parser.add_argument("--files",   required=True, help="검사할 파일명 목록 (쉼표 구분)")
    parser.add_argument("--token",   required=True, help="GitHub Personal Access Token")
    parser.add_argument("--date",    default=str(date.today()), help="오늘 날짜 YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="파일 수정 없이 결과만 출력")
    args = parser.parse_args()

    api    = GitHubAPI(args.token, REPO)
    today  = args.date
    files  = [f.strip() for f in args.files.split(",") if f.strip()]

    print(f"🔍 검사 대상: {files}")

    # 1. 방금 생성된 파일들의 내용 수집 → 링크 추출
    all_links: set[str] = set()
    for fname in files:
        path    = f"{WIKI_DIR}/{fname}"
        content, _ = api.get_file(path)
        if content is None:
            print(f"  ⚠️  {fname} 를 읽을 수 없음 (스킵)")
            continue
        links = extract_links(content)
        print(f"  📄 {fname}: 링크 {len(links)}개 발견 → {links or '없음'}")
        all_links |= links

    if not all_links:
        print("✅ 검사할 링크 없음. 종료.")
        return

    # 2. 각 링크 대상 파일 존재 여부 확인
    missing: list[str] = []
    for link in sorted(all_links):
        target_path = f"{WIKI_DIR}/{link}.md"
        if api.file_exists(target_path):
            print(f"  ✅ [[{link}]] → 존재")
        else:
            print(f"  ❌ [[{link}]] → 없음 (스텁 생성 예정)")
            missing.append(link)

    if not missing:
        print("✅ 데드링크 없음. 종료.")
        return

    print(f"\n📝 스텁 생성 대상: {missing}")

    if args.dry_run:
        print("(dry-run 모드: 실제 파일 변경 없음)")
        return

    # 3. 스텁 파일 생성
    created = []
    for link in missing:
        path    = f"{WIKI_DIR}/{link}.md"
        content = make_stub(link, today)
        ok      = api.put_file(path, content, f"stub: {link}.md [auto]")
        if ok:
            print(f"  ✅ 스텁 생성: {link}.md")
            created.append(link)
        else:
            print(f"  ❌ 스텁 생성 실패: {link}.md")

    if not created:
        print("생성된 스텁 없음. 종료.")
        return

    # 4. index.md 업데이트
    idx_content, idx_sha = api.get_file(f"{WIKI_DIR}/index.md")
    if idx_content:
        new_idx = update_index(idx_content, created, today)
        ok = api.put_file(f"{WIKI_DIR}/index.md", new_idx,
                          f"index: 스텁 {len(created)}건 추가 [auto]", idx_sha)
        print(f"  {'✅' if ok else '❌'} index.md 업데이트")

    # 5. log.md 업데이트
    log_content, log_sha = api.get_file(f"{WIKI_DIR}/log.md")
    if log_content:
        new_log = update_log(log_content, created)
        ok = api.put_file(f"{WIKI_DIR}/log.md", new_log,
                          f"log: 스텁 {len(created)}건 기록 [auto]", log_sha)
        print(f"  {'✅' if ok else '❌'} log.md 업데이트")

    # 6. 결과 요약
    print(f"\n🛠️  데드링크 복구 완료")
    print(f"   - 스텁 생성: {len(created)}건")
    for s in created:
        print(f"     • {s}.md")


if __name__ == "__main__":
    main()
