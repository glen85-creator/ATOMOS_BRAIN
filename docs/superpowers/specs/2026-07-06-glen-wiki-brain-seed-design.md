# ATOMOS BRAIN — GLEN_WORK 1계층 시드 + 리네임 + 위키 계층 보기 설계

**작성일**: 2026-07-06
**상태**: 설계 승인됨 (글렌 브레인스토밍 확정) → 구현
**관련**: 메모리 project_brain_knowledge_layer(BRAIN 인프라), reference_atomos_brain, project_store_service_journal(저널=순수DB와 대비)

## 1. 목적

ATOMOS BRAIN 지식층이 실 콘텐츠 2개(스텁)뿐이라 "껍데기". 글렌의 LLM 위키 **GLEN_WORK**의 1계층 지식(온톨로지+결정)을 시드해 **Hermes가 참조하는 풍성한 지식 창고**로 만든다. 3조각:
- ③-1 리네임: 콘솔 "BRAIN 참조" → **"ATOMOS BRAIN"**
- ③-2 GLEN_WORK 1계층 시드 (핵심)
- ③-3 위키 계층 보기 (스코프/폴더 트리)

## 2. ★핵심 구조 — 지식층은 "파일(SSOT) + DB(색인)" 2단 (저널과 다름)

**"DB로만 변환"이 아니다.** git `.md` 파일이 원본(SSOT)으로 남고, DB는 검색·서빙 색인이다:
```
GLEN_WORK .md (D:\ Obsidian, 폴더구조)
  → [변환 스크립트]
  → ATOMOS_BRAIN/knowledge/global/glen/*.md (git, 폴더구조 유지)  ← 원본(SSOT)
  → [GitHub Action knowledge-index.yml: lint → seed]
  → Supabase atomos_knowledge (+ atomos_knowledge_links)          ← 검색·서빙 색인
  → 검색·MCP(knowledge_search)·/admin/brain 이 DB 조회
```
- **파일** = 편집·버전관리·계층(SSOT). **DB** = FTS·scope 필터·rank·limit로 관련 문서만 빠르게 서빙.
- **성능**: 파일 전체 읽기/grep 대신 DB 검색 → 그대로거나 더 나음(토큰·속도 유리).
- **저널(store_journal)과 차이**: 저널=매일 자동생성·기계용 → 순수 DB(파일 무의미). 지식층=사람 큐레이션·git 편집 → **파일 SSOT + DB 색인 둘 다**.

## 3. BRAIN 현황 (조사 확인)

- `knowledge/` 폴더: `global/`·`dept/sales/` (2 문서). frontmatter `scope`(필수·정규식 `^(global|brand:*|dept:*|store:*)$`)·`read_tier`(STORE_OWNER<HQ_STAFF<HQ_EXEC<ATOMOS_MASTER, 기본 ATOMOS_MASTER)·`read_roles`(레지스트리 {ANALYST})·`tags`·`title`(필수).
- `scripts/`: `lint_knowledge.py`(ERROR 차단·WARN 허용)·`seed_atomos_knowledge.py`(source_path upsert·reconcile·링크테이블)·`links.py`.
- GitHub Action `knowledge-index.yml`: push(knowledge/**) → lint → main이면 seed.
- `/admin/brain`(hbs `BrainReference.tsx`): 검색·스코프필터·위키링크 네비·노트뷰. **폴더 트리 없음**. nav 라벨 `permissions.ts:161` = "BRAIN 참조".
- brainApi: `/api/brain/{search,notes,scopes}`.
- GLEN_WORK 1계층: `wiki/entities/`(people 9·projects 9·organizations 17·technologies 14) + `wiki/concepts/`(12) + `wiki/decisions/`(37) = **98개**. frontmatter(type/created/updated/aliases/tags/sources/related), 위키링크 `[[wiki/...]]`.

## 4. ③-2 GLEN_WORK 시드 — 변환 매핑

### 4.1 대상·출력
- **입력**: `/mnt/d/WORK/GLEN/GLEN_WORK/wiki/{entities/**,concepts,decisions}/*.md` (98개). (WSL이 /mnt/d로 D: 마운트)
- **출력**: `~/ATOMOS_BRAIN/knowledge/global/glen/{category}/{slug}.md`
  - category: `entities-people`·`entities-projects`·`entities-organizations`·`entities-technologies`·`concepts`·`decisions` (평탄화, 폴더 1뎁스).
  - source_path = `global/glen/{category}/{slug}` (knowledge/ 제외한 경로, seed 키).

### 4.2 frontmatter 변환
| BRAIN 필드 | 값 |
|---|---|
| `scope` | `global` (전부) |
| `read_tier` | `ATOMOS_MASTER` (전부) |
| `read_roles` | `[ANALYST]` (Hermes 참조) |
| `title` | GLEN_WORK 본문 첫 H1 → 없으면 `aliases[0]` → 없으면 파일명(확장자·날짜프리픽스 제거) |
| `tags` | GLEN_WORK `tags` + `glen-wiki` + `type/{gw_type}` (중복 제거) |
| `body` | GLEN_WORK 본문(§4.3 위키링크 변환 적용) |

### 4.3 위키링크·참조 처리
- 본문 `[[wiki/concepts/ATOMOS]]` → 시드 대상(98) 안이면 `[[global/glen/concepts/ATOMOS]]`(source_path), 밖(summaries/raw/미시드)이면 **링크 대괄호 제거해 텍스트로 강등**(lint missing-link WARN 회피).
- GLEN_WORK `sources:`(raw 링크·미시드) → 본문 하단 "출처(원본)" 텍스트 목록으로 강등(링크 아님).
- GLEN_WORK `related:`(wiki 링크) → 시드 대상이면 body 말미 "관련" 위키링크로, 밖이면 생략.
- 슬러그: 한글 파일명은 안전 슬러그(공백·특수문자 → `-`), title에 원래 한글 보존.

### 4.4 변환 스크립트
- 신규 `~/ATOMOS_BRAIN/scripts/seed_glen_wiki.py`.
- 역할: /mnt/d GLEN_WORK 98개 읽기 → 변환 → `knowledge/global/glen/**` 생성(덮어씀=멱등) → 요약 출력(생성 수·미해소 링크 수). **DB는 직접 안 건드림** — 파일만 생성, seed는 기존 Action이 push 시 수행.
- 안전: 입력 GLEN_WORK는 read-only(D:\ 원본 무수정). knowledge/global/glen/ 만 쓰기(기존 global/·dept/ 무영향).
- 재실행: knowledge/global/glen/ 전체 재생성(stale 파일 제거 후 재작성) → Action seed가 reconcile.

### 4.5 ingest·검증
- `python scripts/lint_knowledge.py` → ERROR 0(WARN 허용).
- push → Action `knowledge-index.yml` → seed → `atomos_knowledge`에 98 row(scope=global·read_roles=[ANALYST]).
- (Action 시크릿 SUPABASE_URL/SERVICE_KEY 기설정 확인.)

## 5. ③-1 리네임

- `hbs src/auth/permissions.ts:161` nav 라벨 `'BRAIN 참조'` → `'ATOMOS BRAIN'`.
- `hbs src/pages/Admin/BrainReference.tsx` 페이지 제목(H1/헤더) → "ATOMOS BRAIN".
- (FE only, 기능 무변경.)

## 6. ③-3 위키 계층 보기

- `/admin/brain`에 **스코프/폴더 트리** 추가: `source_path`를 `/`로 파싱해 계층 트리(예 `global > glen > concepts > ATOMOS`). 지금 스코프 목록만 있음.
- 구현: brainApi.search 결과의 `source_path`를 FE에서 트리로 그룹핑(신규 EP 불필요) — 스코프 탭에 트리 뷰 추가. 클릭 시 해당 노트 열기.
- 범위: 읽기 전용 트리 탐색(편집 없음). 대량(98+)이라 접기/펼치기.

## 7. 검증 (성공 기준)

1. `seed_glen_wiki.py` 실행 → `knowledge/global/glen/**` 98개 생성 + lint ERROR 0.
2. push → Action seed → `atomos_knowledge` scope=global·glen-wiki tag 문서 98 row.
3. `/admin/brain`(리네임 "ATOMOS BRAIN") 검색에서 GLEN_WORK 지식(예 "ATOMOS"·"Hermes") 회수 + 트리에 `global > glen > {entities/concepts/decisions}` 표시.
4. **Hermes `knowledge_search`가 GLEN_WORK 지식 실제 회수**(e2e: scope global·role ANALYST, call_log 확인) — 글렌 목적("Hermes가 LLM 위키 참조").
5. 재실행 멱등(스크립트 재실행 → 파일 동일·seed reconcile).

## 8. 범위 경계

**포함**: 변환 스크립트(seed_glen_wiki.py) · 98 시드(entities+concepts+decisions) · 리네임(2곳) · 위키 계층 트리 UI · 검증(시드→페이지→Hermes e2e).
**제외(후속)**: summaries 85·raw 시드(원본 정합 필요) · 자동 동기화 파이프라인(GLEN_WORK 변경→자동, D↔WSL·Obsidian) · 하위 tier 개방(풀 인증 온보딩) · pgvector 의미검색(예약, 동일 RPC 뒤 hybrid) · REST 질문 API 외부 AI 개방(tier 인증 선결).

## 9. 안전·불변식

- GLEN_WORK 원본(D:\) **read-only** — 읽기만, 무수정.
- knowledge/global/glen/ 만 쓰기 — 기존 global/·dept/ 지식 무영향.
- read_tier=ATOMOS_MASTER(사람은 super_admin=글렌만, 온보딩 때 하위 개방) · read_roles=[ANALYST](Hermes 참조).
- 파일=SSOT, DB=색인(seed는 Action이 파일에서 재생성 — DB 직접 쓰기 없음).
