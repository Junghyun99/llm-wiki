# 🧠 LLM-Wiki

> LLM이 직접 작성하고 유지보수하는 개인 지식베이스.
> [Andrej Karpathy의 LLM Wiki 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)을 기반으로 제텔카스텐(Zettelkasten) 방법론을 결합한 시스템입니다.

---

## 💡 핵심 컨셉

기존 RAG는 질문할 때마다 원본 문서에서 지식을 재발견합니다. 이 시스템은 다릅니다.

**사람이 소스를 투척하면 → LLM이 원자적 지식으로 분해하여 위키에 축적 → 지식이 복리로 성장**

- **사람의 역할:** 소스 수집, 방향 설정, 질문
- **LLM의 역할:** 분해, 요약, 교차참조, 유지보수, 답변

---

## 📁 디렉터리 구조

```
llm-wiki/
├── CLAUDE.md                    # 시스템 헌법 (LLM 행동 규칙 전체)
│
├── 01_Inbox/                    # 소스 투척 대기열
│   └── (PDF, txt, md 등 드롭)
│
├── 02_Raw_Sources/              # 처리 완료 원본 보관소 (불변·읽기 전용)
│   └── YYYY-MM/
│
├── 03_Wiki/                     # 지식 베이스 (LLM 소유·관리)
│   ├── index.md                 # 전체 노트 카탈로그 (탐색 진입점)
│   ├── log.md                   # 작업 이력 타임라인 (Append-only)
│   ├── @문헌명.md               # 문헌 노트
│   ├── 개념명.md                # 영구 노트
│   └── MOC_주제명.md            # 허브 노트
│
└── .claude/
    ├── skills/                  # LLM 행동 규칙
    │   ├── extract-zettelkasten/
│   │   └── SKILL.md
    │   ├── lint-zettelkasten/
│   │   └── SKILL.md
    │   └── save_query_result.md
    └── commands/                # 실행 매크로
        ├── process_inbox.md
        ├── run_maintenance.md
        ├── fill_stubs.md
        └── ask_wiki.md
```

---

## 🚀 사용법

### 1. 소스 수집
```
01_Inbox/ 폴더에 파일 드롭 (PDF, txt, md, 텍스트 붙여넣기 등)
```

### 2. 지식 분해 (Ingest)
```
/process-inbox
```
LLM이 소스를 읽고 핵심 요약 + 추출 예정 노트 목록을 Preview로 보여줍니다.
승인하면 `03_Wiki/`에 노트가 생성되고 원본은 `02_Raw_Sources/`로 아카이빙됩니다.

### 3. 위키 정비 (Lint)
```
/run-maintenance
```
중복 병합, 고립 노트 구출, 데드링크 복구, MOC 최신화, 충돌 감지를 수행하고 리포트를 출력합니다.

### 4. 스텁 보완 (Fill)
```
/fill-stubs
```
`#todo/fill` 태그가 달린 미작성 노트를 웹 검색으로 채웁니다. 초안을 보여주고 승인 후 저장합니다.

### 5. 지식 쿼리 (Query)
```
/ask [질문내용]
```
위키를 먼저 탐색하고 출처를 명시한 답변을 생성합니다. 가치 있는 답변은 영구 노트로 저장을 제안합니다.

---

## 📝 노트 명명 규칙

| 유형 | 접두사 | 예시 |
|------|--------|------|
| 문헌 노트 | `@` | `@2026_세법개정안_가이드.md` |
| 영구 노트 | 없음 | `DC형_퇴직연금_세금이연효과.md` |
| 허브 노트 | `MOC_` | `MOC_퀀트_트레이딩_시스템.md` |

---

## 🔑 역할 분담

| 영역 | 사람 | LLM |
|------|------|-----|
| `01_Inbox/` | ✍️ 소스 투척 | 📖 읽기 |
| `02_Raw_Sources/` | 📖 읽기 | 📖 읽기만 (수정 금지) |
| `03_Wiki/` | 📖 탐색 | ✍️ 소유·관리 |
| `.claude/` | ✍️ 규칙 설계 | 📖 참조 |

---

## 📚 참고

- 시스템 상세 규칙: [`CLAUDE.md`](./CLAUDE.md)
- 위키 전체 목차: [`03_Wiki/index.md`](./03_Wiki/index.md)
- 작업 이력: [`03_Wiki/log.md`](./03_Wiki/log.md)
- 원본 컨셉: [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
