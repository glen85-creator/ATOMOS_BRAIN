# ATOMOS BRAIN 지식 레이어 — 상세 설계 (4 미결 확정)

> 상태: **설계 확정** — 사용자 리뷰 → writing-plans 대기. 2026-06-22.
> 부모 설계: `2026-06-20-pipeline-redesign-design.md` §5 / §5a (지식 wiki 레이어).
> ADR: glen_work `wiki/decisions/2026-06-21-atomos-brain-knowledge-layer.md`.
> 본 문서 = §5a가 남긴 4 미결의 확정 설계.

## 0. 범위 / 전제

이 문서는 §5a 말미의 미결 4건을 확정한다:
- **①** 4계층 frontmatter 규약
- **②** "BRAIN 참조" 콘솔 페이지 컴포넌트 + API 계약
- **③** 그래프·검색 구현 선택
- **④** 학습지식 v2 ingest/lint 파이프라인

### 0.1 불변 전제 (확정 결정 — 재논의 아님)
- **권한 = 우리 레이어 전담.** `(role × scope)` frontmatter 단일원천, **BRAIN/MCP 런타임에서 강제**. UI 아님 — **"숨김 = 데이터가 안 온다"**(클라이언트 필터 금지, fail-closed).
- **사람 4계층(단조 포함)**: `STORE_OWNER ⊂ HQ_STAFF ⊂ HQ_EXEC ⊂ ATOMOS_MASTER`.
- **사람 열람 표면 = 콘솔(hbs-dashboard) 내 "BRAIN 참조" 동적 페이지(옵션 A).** Quartz(B)는 비채택(비민감 한정 옵션으로 보류).
- **유지 = llm-wiki 패턴**(ingest/query-filed-back/lint, compile-not-retrieve) — **패턴만 차용, GPL-3.0 앱·LanceDB 미사용**, 우리 스택(pgvector + MCP)으로 구현.

### 0.2 기존 자산 (Phase 1 — `feat/atomos-phase1-hermes-mcp`, 건드리지 않음)
- 테이블 `atomos_knowledge(scope, read_roles[], title, body, source_path, ts tsvector, created_at)`.
- RPC `atomos_knowledge_search(p_query, p_scopes, p_role, p_limit)` — **Postgres FTS**, scope + role 필터.
- MCP 서버(`app/mcp_server/`) — **HMAC 스코프 세션토큰**(execution_id·store_id·brand_id·dept·role·exp) = **에이전트 경로**. Bearer 정적토큰 + `X-Atomos-Session`.
- 감사 `atomos_mcp_call_log`.
- 시드 2파일: `knowledge/global/grounding-rules.md`, `knowledge/dept/sales/anomaly-playbook.md` (둘 다 `read_roles:[ANALYST]`).
- pgvector는 Phase 1에서 **미통합 — 동일 RPC 인터페이스 뒤로 Phase 2 교체** 명시.

> **구현 시점**: 본 설계의 구현은 **Phase 1 병합 후 새 브랜치 + 새 마이그레이션(008+)**. Phase 1 브랜치/마이그레이션 007/D-COGS 미커밋 파일은 **수정 금지**.

### 0.3 리포 분담
- **지식 SSOT** = `ATOMOS_BRAIN/knowledge/` (markdown, 폴더 = 스코프).
- **백엔드**(MCP·pgvector·ingest·RPC·인증) = `FastAPI` (`~/FastAPI`).
- **콘솔**(BRAIN 참조 페이지) = `hbs-dashboard` (`~/hbs-dashboard`).

### 0.4 역할 어휘 — legacy 로스터 비차용 (중요)
신규 지식 레이어의 **에이전트 역할 어휘는 legacy 13-슬롯 로스터(CEO/CTO/RESEARCHER/CRM_TEAM/ARCHIVES/BRAND_DIVISION/CONTENTS_STUDIO/VISION_AI 등)에서 오지 않는다.** 그 로스터는 재설계가 **명시적으로 제거하는** 다중-에이전트 팬아웃·CEO 합성 아키텍처의 잔재다(§1 "팬아웃·CEO 합성 제거", §7 제거 대상). 재설계 모델은 **단일 역할 / 도메인**(§1, §8): 1차 = D-SALES → **ANALYST** 하나. HERMES는 역할이 아니라 *런타임*(세션토큰의 `role`은 `ANALYST`). 신규 역할은 **새 도메인이 실제로 활성화될 때 1개씩** 추가한다.

---

## 1. ① 4계층 frontmatter 규약 (확정)

### 1.1 핵심 모델 — 사람=단조 tier, 에이전트=직교 집합
읽기 권한은 **두 가지 모양**을 한 스키마에 담는다:
- **사람**: 4계층은 **단조 포함**(상위는 하위를 항상 읽음) → 파일당 **단일 하한 `read_tier`** 한 개로 표현.
- **에이전트**: 역할은 **직교(평면 집합)** → **`read_roles[]`** 명시 grant로 표현.

이 분리로 `read_tier: STORE_OWNER` 한 줄이 "STORE_OWNER 이상 전 계층"을 인코딩하고, 에이전트는 별개 집합으로 직교 부여된다.

### 1.2 스키마

```yaml
---
# ─── REQUIRED ───
title: 매출 급락 대응 플레이북
scope: store:ST-123        # 네임스페이스(어디 소속). global | brand:{br_id} | dept:{dept} | store:{st_id}
read_tier: HQ_STAFF        # 사람 최소 계층(단조 ↑). 생략 시 → ATOMOS_MASTER (fail-closed) + lint 경고

# ─── OPTIONAL ───
read_roles: [ANALYST]      # 에이전트 직교 grant. 검증 레지스트리={ANALYST}(현재). 생략 → 에이전트 0
tags: [매출, 급락, D-SALES]  # 그래프/필터용 (③)

# ─── v2 LEARNING (Phase 4까지 inert — 저장만, v1 랭킹 미사용) ───
source: "ANALYST_RETRO:exec-uuid"           # 출처/귀속
verified: true                              # 검증 사이클 통과 여부
confidence: 0.82                            # 학습지식 신뢰도
supersedes: knowledge/dept/sales/old.md     # compound/모순 처리(대체 대상)
---
```

### 1.3 enum

```
Tier (단조 오름차순, rank):
  STORE_OWNER(0) < HQ_STAFF(1) < HQ_EXEC(2) < ATOMOS_MASTER(3)

Agent role registry (현재):
  { ANALYST }
  └ 도메인 활성화 시 1개씩 증가(COGS·비용·리뷰는 Phase 4, 역할명 그때 확정). lint가 미등록 역할 경고.

Scope 구문:
  global | brand:{br_id} | dept:{dept} | store:{st_id}
```

### 1.4 권한 해석 (런타임 = 단일 강제점)
요청은 `(reader_kind, tier|role, allowed_scopes[])`를 싣고 RPC에서 필터한다:
- **사람**: `note.scope ∈ allowed_scopes` **AND** `rank(reader.tier) ≥ rank(note.read_tier)`
- **에이전트**: `note.scope ∈ allowed_scopes` **AND** `agent_role ∈ note.read_roles`
- **ATOMOS_MASTER**: 위 + `system/meta` 스코프 + v2 학습지식 + 쓰기·큐레이션·lint 권한

> `read_tier`가 "global**점주안전**(read_tier=STORE_OWNER) vs global**임원전용**(read_tier=HQ_EXEC)"을 가르는 **진짜 변별자**다 — scope(=네임스페이스)만으로는 동일 `global` 내 계층을 구분 못 한다.

### 1.5 기본값 / fail-closed
- `read_tier` 생략 → **`ATOMOS_MASTER`**(master만 열람, 누출 0). **lint가 시끄럽게 경고**해 저자가 고침. 파일은 색인됨(드롭 안 함).
- `read_roles` 생략 → 에이전트 **0**(명시 grant만).
- **구조적 무효**(scope 구문 위반 / title 누락 / tier enum 외 값)는 기본값이 아니라 **lint ERROR → ingest 차단**(④ 참조). 즉 "생략=안전한 기본값", "깨짐=거부".

### 1.6 저장 / 마이그레이션 (새 마이그레이션 008, 007 미수정)
```sql
-- 008_atomos_brain_knowledge_layer.sql
alter table atomos_knowledge
  add column if not exists read_tier text not null default 'ATOMOS_MASTER';

-- 시드 2파일 백필: 둘 다 에이전트 분석규율 → read_tier='ATOMOS_MASTER' (사람 노출 0),
--                  기존 read_roles:[ANALYST] 유지(에이전트 경로 정상).

-- v2 예약 컬럼(inert)
alter table atomos_knowledge
  add column if not exists source text,
  add column if not exists verified boolean,
  add column if not exists confidence numeric,
  add column if not exists supersedes text,
  add column if not exists tags text[] not null default '{}';

-- tier rank 헬퍼
create or replace function atomos_tier_rank(t text) returns int language sql immutable as $$
  select case t
    when 'STORE_OWNER' then 0 when 'HQ_STAFF' then 1
    when 'HQ_EXEC' then 2 when 'ATOMOS_MASTER' then 3 else 99 end;
$$;
```

### 1.7 tier-aware 검색 RPC (사람·에이전트 단일 함수)
```sql
create or replace function atomos_knowledge_search(
  p_query       text,
  p_scopes      text[],
  p_reader_kind text,            -- 'human' | 'agent'
  p_role        text default null,   -- agent: role ∈ read_roles
  p_tier        text default null,   -- human: rank(tier) >= rank(read_tier)
  p_limit       int  default 20
) returns table(source_path text, scope text, read_tier text, title text,
                snippet text, tags text[], rank real)
language sql stable as $$
  select k.source_path, k.scope, k.read_tier, k.title,
         left(k.body, 280) as snippet, k.tags,
         ts_rank(k.ts, plainto_tsquery('simple', coalesce(p_query,''))) as rank
  from atomos_knowledge k
  where k.scope = any(p_scopes)
    and (
      (p_reader_kind = 'agent' and p_role = any(k.read_roles))
      or
      (p_reader_kind = 'human' and atomos_tier_rank(p_tier) >= atomos_tier_rank(k.read_tier))
    )
    and (coalesce(p_query,'') = '' or k.ts @@ plainto_tsquery('simple', p_query))
  order by rank desc, k.created_at desc
  limit greatest(p_limit, 1);
$$;
```
- **에이전트 호출부**(Phase 1 `app/mcp_server/tools.py`)는 `p_reader_kind='agent'` 1줄 추가 — **Phase 1 병합 후** 적용.
- pgvector 전환 시(③) **이 시그니처를 유지**하고 내부 랭킹만 hybrid로 교체.

---

## 2. ② BRAIN 참조 페이지 — 컴포넌트 + API 계약 (확정)

### 2.1 인증 경계 — 검증 Supabase JWT → tier (최소 시작)
설계 제약: 필터는 **항상 서버측**. 현재 사람 독자 = 글렌(=`ATOMOS_MASTER`) 1명, 실 점주는 "풀 유저인증 선결"(deferred-security) 뒤. 따라서 **강제 seam은 정확히 깔되, 매핑은 master 한 줄만 배선**한다.

```python
# FastAPI: app/api/routes/brain.py (신규)
async def require_brain_reader(authorization: str = Header(...)) -> BrainReader:
    # 1) Supabase JWT 검증 (HS256, SUPABASE_JWT_SECRET) → claims.sub (실패→401)
    # 2) sub로 role + 스코프(br_id_scope, st_id_scope[]) 해석 (JWT app_metadata 또는 profiles 조회)
    # 3) console role → BRAIN tier 매핑
    # 4) allowed_scopes(tier, profile) 산출
    # 5) BrainReader(tier, allowed_scopes) 반환 — fail-closed
```

**console role → BRAIN tier 매핑** (현재 활성 = `super_admin`만; 나머지는 스펙 정의·실 점주 온보딩 때 점등·확정):
```
super_admin    → ATOMOS_MASTER   ← 지금 배선 (글렌)
brand_admin    → HQ_STAFF  (scope = 자기 br_id)        [provisional]
brand_manager  → HQ_STAFF  (scope = 자기 br_id)        [provisional]
sv             → HQ_STAFF  또는 STORE_OWNER(다점)       [provisional, 온보딩 때 확정]
store_manager  → STORE_OWNER (scope = 자기 st_id_scope[]) [provisional]
staff          → STORE_OWNER (scope = 자기 store)        [provisional]
viewer         → STORE_OWNER (read-only)                 [provisional]
```

**allowed_scopes(tier, profile)** — tier가 breadth를 지배(read_tier 단조 체크는 그 위에 항상 적용):
```
ATOMOS_MASTER → 전 scope (필터 없음) + system/meta + 학습지식
HQ_EXEC       → 전 brand/dept/store + global (system/meta 제외)
HQ_STAFF      → global ∪ {dept:*} ∪ {brand:b | b ∈ user.brands} ∪ {그 brand 하위 store}
STORE_OWNER   → global ∪ {brand:b | b ∈ user.brands} ∪ {store:s | s ∈ user.stores}
```
> 지금은 `super_admin→ATOMOS_MASTER`(무제한)만 유효하므로 하위 tier 해석은 **provisional(스펙 전용)**. 실 점주 온보딩(풀 유저인증) 시 점등.

### 2.2 API 계약 (구현-무관 — FTS든 pgvector든 동일)
모든 EP는 `require_brain_reader` 의존성을 통과 → tier-aware RPC로 서버측 필터. **403/404 통일**(권한 밖 노트의 존재 여부 누출 금지).

```
GET /api/brain/search?q=<text>&scope=<opt>&limit=20
    → { results: [{ source_path, title, scope, read_tier, tags, snippet, rank }] }
      · q 비움 + scope 지정 = 브라우즈
      · 서버가 reader.tier/allowed_scopes로 필터

GET /api/brain/notes/{source_path}        (source_path는 URL-encode 또는 ?path= 쿼리)
    → { source_path, title, scope, read_tier, read_roles, tags, body_md,
        backlinks: [...], outlinks: [...] }
      · backlinks/outlinks = [] (③ 링크추출 전까지 빈 배열)
      · 권한 밖 → 404 (403과 응답 동일)

GET /api/brain/scopes
    → { scopes: [{ scope, count }] }
      · reader가 볼 수 있는 스코프 + 가시 노트 수만

GET /api/brain/graph?scope=<opt>          ← v2 (③ 링크추출 뒤)
    → { nodes: [{ source_path, title, scope }], edges: [{ from, to }] }
```
- **노트 주소 = `source_path`**(예 `dept/sales/anomaly-playbook`) — wikilink 타깃 + 멱등 upsert 키와 동일.
- env 추가: `SUPABASE_JWT_SECRET`.

### 2.3 콘솔 컴포넌트 (기존 패턴 그대로)
- **라우트** `/admin/brain` → `ProtectedRoute` + `permissions.ts` 엔트리(접근 게이트는 콘솔측, **데이터 필터는 백엔드**).
- **페이지** `src/pages/Admin/BrainReference.tsx`: 헤더(h1+부제) + 탭바(`🔍 검색` / `🗂 스코프` / `🕸 그래프`(v2)) + **2-pane**(좌 = 검색결과·스코프목록 / 우 = 노트 detail).
- **노트 detail**: `react-markdown`로 본문 렌더. `[[wikilink]]`는 커스텀 컴포넌트로 노트 간 내부 링크(클릭 → 해당 source_path 로드). 백링크 패널은 v2.
- **API** `src/api/client.ts`에 `brainApi` 오브젝트(search/getNote/listScopes/getGraph) + `src/api/types.ts` 응답 타입.
- **상태** TanStack Query(`['brain','search',q,scope]`, `['brain','note',source_path]`, `['brain','scopes']`), staleTime 5분.
- **스타일** 기존 UI 프리미티브(`Card`/`Button`/`Pill`/`SectionHeader`) + CSS 변수. shadcn 미도입 유지.
- **신규 의존성**: `react-markdown`(v1). `react-force-graph`(v2, 그래프 슬라이스 때).

### 2.4 v1 범위 (확정)
- **v1**: 키워드 검색(FTS) + 노트뷰(본문 마크다운) + 스코프 탐색.
- **v2**(③ 인프라 뒤): 백링크/아웃링크 + 의미검색 + 그래프 뷰.

---

## 3. ③ 그래프·검색 구현 (확정)

### 3.1 검색 — FTS+태그+스코프 우선, pgvector 예약
- **v1 = Postgres FTS**(현 RPC) + **태그 필터** + **스코프 네비**. 작은 큐레이션 위키(현 2노트·향후 수십)에는 키워드+태그+스코프가 대개 충분.
- **pgvector 의미검색 = 예약**: "키워드로 놓치기 시작할 때" 추가. **동일 `atomos_knowledge_search` 시그니처 뒤로 hybrid(FTS 후보 → 임베딩 코사인 재랭킹) 교체.** 그때만 임베딩 키·벡터컬럼·재색인 도입.
- 임베딩 제공자/모델은 **전환 시점에 확정**(현재 미결로 둠 — 코퍼스가 정당화할 때). 후보: OpenAI `text-embedding-3-small`(1536d) 등. 비결정으로 둔다.

### 3.2 링크 데이터 모델 (백링크·그래프·lint 공용)
ingest 때 본문의 `[[wikilink]]`(대상 = `source_path` 또는 `title`)를 파싱 → 링크 테이블:
```sql
create table if not exists atomos_knowledge_links (
  from_path text not null,
  to_ref    text not null,           -- [[…]] 원문 토큰
  to_path   text,                    -- 해소된 source_path (미해소 시 null)
  resolved  boolean not null default false,
  primary key (from_path, to_ref)
);
```
- **백링크** = `to_path = :path` 역조회. **아웃링크** = `from_path = :path`. **그래프** = 노드(노트) + 엣지(resolved 링크). **missing-link** = `resolved=false`(④ lint). **orphan** = inlink·outlink 모두 0(④ lint).
- 링크 조회도 **reader allowed_scopes로 필터**(권한 밖 노트는 그래프/백링크에서도 보이지 않음 — "숨김=데이터 안 옴" 일관).

### 3.3 그래프 렌더 (v2)
- **`react-force-graph`(2d, canvas)** 채택 — 이 용도 전용·경량, 클릭→노트 네비 용이. 작은~중간 코퍼스 적합.
- 비채택: cytoscape(오버킬), 커스텀 d3(손이 많이 감).
- 그래프 데이터 범위: v2 초기 = reader 가시 전체 그래프(소규모라 충분), 이후 필요 시 "현재 노트 N-hop 이웃"으로 축소.

---

## 4. ④ ingest / lint 파이프라인 (확정)

세 갈래를 분리한다: **(1) v1 ingest = 지금 필요**, **(2) lint = 일부 v1 필요**, **(3) v2 학습루프 = seam만**.

### 4.1 v1 ingest — git → CI 색인 (지금 구현)
- **GitHub Action**: `ATOMOS_BRAIN`에서 `knowledge/**` push(또는 PR)에 트리거.
- **단계**: checkout → **lint(ERROR면 실패)** → `scripts/seed_atomos_knowledge.py` 실행(프론트매터 파싱 → `atomos_knowledge` upsert by `source_path`, 멱등) → **삭제 reconcile**(리포에서 사라진 source_path 행 제거) → `[[wikilink]]` 파싱 → `atomos_knowledge_links` 재구축.
- **시크릿**: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (GH Actions secrets).
- 결과: 지식 편집 = git push만으로 BRAIN 페이지·MCP 검색에 반영.

### 4.2 lint 규칙 (CI + CLI 스크립트)
```
ERROR (ingest 차단):
  · scope 누락 / 구문 위반(global|brand:|dept:|store: 아님)
  · title 누락
  · read_tier 값이 enum 밖

WARN (색인은 진행, CI 로그에 표면화):
  · read_tier 누락 → ATOMOS_MASTER 기본(누구도 못 봄 위험 경고)
  · read_roles에 레지스트리({ANALYST}) 밖 역할
  · missing-link ([[X]] 미해소)
  · orphan (inlink·outlink 모두 0)

INFO:
  · v2 메타(source/verified/confidence/supersedes) 형식 점검
```
- lint는 **CI에서 PR/push마다** + **로컬 CLI**(`python scripts/lint_knowledge.py`)로 동일 코드 경로.

### 4.3 v2 학습루프 — seam만 (본체 Phase 4)
지금 **차단되지 않게 seam만** 깐다:
- **예약 메타**(1.2/1.6): `source`·`verified`·`confidence`·`supersedes` 컬럼 — 저장만, v1 검색 랭킹 미사용.
- **append-only 감사**: `knowledge/index.md` + `knowledge/log.md`(append-only) 규약 도입(사람=큐레이션/방향, ATOMOS=bookkeeping).
- **학습후보 flag 훅**: 분석 사이클이 §3a 검증 게이트 통과 **AND** 운영자 승인(§3e L4 라벨) 시 → `atomos_learning_candidates`(또는 `strategy_executions` 플래그)에 후보 레코드 적재. **자동 file-back 아님** — Phase 4용 캡처만.
- **Phase 4로 연기**(별도 스펙): entity/concept 정규화 + 모순 플래그, query-filed-back compound, 모순/stale 해소, 동시쓰기 락. **실 데이터(검증된 사이클)가 쌓인 뒤** 설계.

---

## 5. 구현 phasing (이 레이어)

> 전제: **Phase 1(MCP + atomos_knowledge) 병합 후** 시작. 새 브랜치·새 마이그레이션(008).

- **Slice 1 — 스키마 + ingest + lint** (FastAPI + ATOMOS_BRAIN): 마이그레이션 008(read_tier·예약컬럼·tier_rank·tier-aware RPC), lint 스크립트, GitHub Action ingest, 시드 백필. → 신선 색인 + 검증 작동. (①, ④-v1)
- **Slice 2 — BRAIN API** (FastAPI): `require_brain_reader`(JWT 검증→tier), `/api/brain/{search,notes,scopes}`, 403/404 통일. (②-백엔드)
- **Slice 3 — BRAIN 참조 페이지 v1** (hbs-dashboard): `/admin/brain`, `BrainReference.tsx`(검색·노트뷰·스코프탐색), `brainApi`, react-markdown. (②-프론트)
- **Slice 4 — v2** (후속): `[[wikilink]]` 링크추출 + 백링크 + pgvector hybrid + 그래프(react-force-graph) + 학습 seam 활성화.

의존: Slice 1 → 2 → 3 (순차). Slice 4는 그 뒤.

---

## 6. 미해결 / 후속
- 임베딩 제공자/모델 — pgvector 전환 시점에 확정(③.1).
- 하위 tier(STORE_OWNER~HQ_EXEC) 매핑·scope 해석 점등 — 실 점주 온보딩(풀 유저인증)과 함께(②.1).
- v2 학습루프 본체 — Phase 4 별도 스펙(④.3).
- `system/meta` 스코프 구체 구획(ATOMOS_MASTER 전용 메타지식) — Slice 1에서 스코프 문자열 예약만.

---

## 7. 검증 체크리스트 (확정 추적)
- [x] ① read_tier(단조) + read_roles(직교, 레지스트리={ANALYST}, legacy 비차용) + 생략→MASTER+lint경고
- [x] ② 검증 JWT→tier(super_admin→MASTER 배선) + API 계약(search/notes/scopes/graph, 403·404 통일) + 컴포넌트(2-pane, react-markdown) + v1 범위
- [x] ③ FTS+태그+스코프 v1 / pgvector 예약(동일 RPC) / 링크테이블 / react-force-graph(v2)
- [x] ④ v1 ingest(GH Action)+lint 지금 / v2 학습루프 seam만(예약메타·log·후보flag), 본체 Phase 4
- [x] phasing 4 slice (Phase 1 병합 후, 008 신규 마이그레이션)
- [ ] 사용자 리뷰 → writing-plans
