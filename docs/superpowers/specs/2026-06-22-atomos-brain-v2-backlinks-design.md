# ATOMOS BRAIN 지식 레이어 v2 — 백링크 (Slice 4) 상세 설계

> 상태: **설계 확정** — writing-plans 대기. 2026-06-22.
> 부모: `2026-06-22-atomos-brain-knowledge-layer-design.md` (v1) + `…-v1.md` plan. v1 spec이 "Slice 4(v2)"로 예고한 것 중 **링크추출 + 백링크만** 떼어낸 것.
> 그래프·pgvector 의미검색·학습루프 본체는 **이 스펙 범위 밖**(각자 트리거 충족 시 별도 스펙).

## 0. 범위 / 전제

### 0.1 범위 (확정)
**링크추출 + 백링크/아웃링크.** "위키를 진짜 위키로" 만드는 구조 레이어 — 노트 간 상호참조를 표면화.
- ingest가 본문 `[[wikilink]]`를 파싱 → `source_path`로 해소 → `atomos_knowledge_links` 채움.
- note EP가 **권한필터** 백링크/아웃링크를 회수.
- 프론트가 백링크/아웃링크 패널 + 본문 클릭 네비.
- lint가 missing-link / orphan 점검(이제 링크그래프 존재).

### 0.2 범위 밖 (YAGNI — 각자 트리거)
- **그래프(react-force-graph)**: 노드가 충분히 많아야 가치 → 코퍼스 성장 후 별도.
- **pgvector 의미검색**: 코퍼스가 키워드로 놓치기 시작할 때(v1 결정 유지). 임베딩 제공자 선택은 실데이터 후.
- **학습루프 본체**(자동 file-back·정규화·모순해소): 검증된 사이클 데이터 축적 후 별도 스펙.

### 0.3 전제 / 기존 자산
- **v1 적용 선행**: 007(Phase 1)+008 적용 + ingest 라이브. (이 슬라이스의 구현은 v1 적용 후 — 설계는 지금.)
- `atomos_knowledge_links(from_path, to_ref, to_path, resolved)` + `to_path` 인덱스 = **이미 008에 생성됨**(비어있음). 이 슬라이스는 **그 테이블을 채우고 읽는다.**
- `atomos_tier_rank(text)` = 008. 권한 모델·`atomos_knowledge_search_v2` 등 = v1.
- 프론트 `parseWikilinks(md)` = 이미 존재(`src/pages/Admin/brainWikilink.ts`).
- note EP `brain_note`는 `backlinks:[]/outlinks:[]` 자리만 비워둠.
- 리포: 콘솔=hbs-dashboard, 백엔드=FastAPI, 지식 SSOT=ATOMOS_BRAIN/knowledge/. Phase1 경로(007 RPC·mcp_server) 무수정 원칙 유지.

## 1. 링크 데이터 모델 (확정)

`atomos_knowledge_links` (008, 그대로 사용):
```
from_path text   -- 링크를 가진 노트의 source_path
to_ref    text   -- [[...]] 원문 토큰 (해소 전)
to_path   text   -- 해소된 source_path (미해소 시 null)
resolved  boolean
primary key (from_path, to_ref)
```

### 1.1 해소 규칙 = source_path 기준 (확정)
- `[[target]]` / `[[target|label]]`에서 `target`을 **source_path로 해소**.
- 정규화: `target` 그대로, 그다음 `target + ".md"`를 코퍼스의 알려진 source_path 집합과 대조 → 첫 매치가 `to_path`, `resolved=true`. 둘 다 실패 → `to_path=null`, `resolved=false`(→ lint missing-link).
- `source_path`는 정본 식별자(예 `dept/sales/anomaly-playbook.md`)이며 note EP·프론트 네비 키와 동일. 작성 예: `[[dept/sales/anomaly-playbook]]`(`.md` 생략 허용).
- `label`은 표시용(저장 안 함 — v2 백링크 단계에선 to_ref/to_path만 필요; label은 본문 렌더 시 즉석 사용).

## 2. 4a — ingest 링크추출 + lint (ATOMOS_BRAIN, 순수 Python)

### 2.1 링크추출 (seed 확장)
`scripts/seed_atomos_knowledge.py`에 순수 함수 추가:
```python
import re
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

def extract_links(body: str) -> list[tuple[str, str]]:
    """본문 → [(to_ref, label)] 리스트(순수)."""
    return [(m.group(1).strip(), (m.group(2) or m.group(1)).strip())
            for m in _WIKILINK_RE.finditer(body)]

def resolve_target(to_ref: str, known_paths: set) -> str | None:
    for cand in (to_ref, to_ref + ".md"):
        if cand in known_paths:
            return cand
    return None
```
`main()` 흐름에 링크 적재 추가(노트 upsert 후):
- `known = {r["source_path"] for r in rows}`.
- 각 노트: `for to_ref, _label in extract_links(body)` → `to_path = resolve_target(to_ref, known)` → 링크행 `{from_path, to_ref, to_path, resolved: to_path is not None}`.
- **per-from_path 재구축 + reconcile**(전체 delete 회피, 기존 seed 패턴과 일치):
  - 각 현재 노트: `DELETE atomos_knowledge_links?from_path=eq.<sp>` → 현재 노트 링크 INSERT.
  - reconcile: `GET …links?select=from_path` → `keep`(현재 source_path 집합)에 없는 from_path 행 DELETE(삭제된 노트의 링크 청소).
  - `source_path`/`to_ref`는 URL-encode(`urllib.parse.quote(..., safe="")`).

### 2.2 lint 크로스파일 패스 (lint_knowledge.py)
지금까지 per-file 검증에 **크로스파일 패스** 추가(`main()`에서 전 파일 파싱 후):
- 전 노트 `source_path` 집합 + 각 노트의 `extract_links` 결과 수집.
- **missing-link** (WARN): `[[X]]`의 X가 source_path 집합에 (X / X+.md 둘 다) 없음 → `WARN: <file>: 미해소 링크 [[X]]`.
- **orphan** (WARN): 어떤 노트가 inbound(다른 노트가 가리킴) 0 **AND** outbound(해소된 링크) 0 → `WARN: <file>: orphan (인·아웃 링크 0)`.
- 이 두 검사는 ERROR 아님(WARN) — ingest 차단 안 함(v1 lint 기조: 구조 무효만 ERROR).
- extract_links/resolve 로직은 seed와 공유(중복 회피 위해 한쪽 import 또는 작은 공용 모듈 `scripts/links.py`로 추출 — 구현계획에서 결정).

## 3. 4b — 백링크 RPC + note EP (FastAPI)

### 3.1 migration 009 (008 미수정; 008의 테이블·tier_rank 사용)
```sql
-- 009_atomos_brain_backlinks.sql
-- 전제: 008 적용(atomos_knowledge_links 테이블 + atomos_tier_rank).
create or replace function atomos_knowledge_backlinks_v2(
  p_source_path text, p_scopes text[], p_tier text
) returns table(source_path text, title text)
language sql stable as $$
  select k.source_path, k.title
  from atomos_knowledge_links l
  join atomos_knowledge k on k.source_path = l.from_path
  where l.to_path = p_source_path and l.resolved
    and (p_scopes is null or k.scope = any(p_scopes))
    and atomos_tier_rank(p_tier) >= atomos_tier_rank(k.read_tier)
  order by k.title;
$$;
revoke all on function atomos_knowledge_backlinks_v2(text, text[], text) from anon;
grant execute on function atomos_knowledge_backlinks_v2(text, text[], text) to service_role;

create or replace function atomos_knowledge_outlinks_v2(
  p_source_path text, p_scopes text[], p_tier text
) returns table(source_path text, title text)
language sql stable as $$
  select k.source_path, k.title
  from atomos_knowledge_links l
  join atomos_knowledge k on k.source_path = l.to_path
  where l.from_path = p_source_path and l.resolved
    and (p_scopes is null or k.scope = any(p_scopes))
    and atomos_tier_rank(p_tier) >= atomos_tier_rank(k.read_tier)
  order by k.title;
$$;
revoke all on function atomos_knowledge_outlinks_v2(text, text[], text) from anon;
grant execute on function atomos_knowledge_outlinks_v2(text, text[], text) to service_role;
```
- **권한 일관**: 백링크/아웃링크 모두 reader의 (scope,tier)로 필터 — 못 보는 노트는 백링크에도, 아웃링크에도 안 나옴("숨김=데이터 안 옴"). 미해소(resolved=false) 링크는 아웃링크에 안 나옴(끊긴 링크는 lint가 표면화, UI 노출 안 함).

### 3.2 note EP 변경 (brain.py)
`brain_note`가 두 RPC를 호출해 `backlinks`/`outlinks`를 채움(현 `[]`):
```python
bl = await client.rpc("atomos_knowledge_backlinks_v2", {
    "p_source_path": path, "p_scopes": reader.scopes, "p_tier": reader.tier}).execute()
ol = await client.rpc("atomos_knowledge_outlinks_v2", {
    "p_source_path": path, "p_scopes": reader.scopes, "p_tier": reader.tier}).execute()
# ... return 에서 "backlinks": bl.data or [], "outlinks": ol.data or []
```
각 항목 = `{source_path, title}`. (노트 본문 회수 후, 노트가 권한 통과한 경우에만 백링크 회수 — 404면 RPC 호출 안 함.)

## 4. 4c — 프론트 패널 + 클릭 네비 (hbs-dashboard)

### 4.1 타입 정정
`BrainNoteDetail.backlinks` / `.outlinks`: `string[]` → **`{ source_path: string; title: string }[]`**(4b 응답과 일치). 신규 타입 `BrainLinkRef { source_path: string; title: string }`.

### 4.2 note detail UI
- 우측 노트 패널 하단에 **백링크 / 아웃링크 섹션**: 각 항목 title 버튼 → `setSelected(item.source_path)`(해당 노트 로드). 비어있으면 섹션 숨김.
- **본문 클릭 네비**: `body_md`를 react-markdown에 넘기기 전 `[[target|label]]` → 마크다운 링크 `[label](brain:<target>)`로 전처리(전처리 함수는 `brainWikilink.ts`에 추가, vitest). react-markdown `components.a` 커스텀: href가 `brain:`로 시작하면 `<button>`로 렌더, 클릭 시 `setSelected(normalize(target))`(`normalize` = `.md` 없으면 붙임). 그 외 href는 평범한 외부 링크.

## 5. 권한 / 엣지 (확정)
- 백링크·아웃링크는 **서버측 RPC가 (scope,tier) 필터** — 클라 필터 0.
- 못 보는 노트로의/로부터의 링크는 양방향 모두 숨김.
- 미해소 링크: UI 비노출(아웃링크 제외), lint WARN로만 표면화.
- 본문 클릭 링크가 권한 밖/없는 노트를 가리키면 note EP가 404 → 기존 "열람 권한 없거나 노트 없음" 상태 재사용.

## 6. 테스트
- **4a**: `extract_links`(여러 패턴·라벨·없음), `resolve_target`(.md 폴백·미해소), lint missing-link/orphan(크로스파일 픽스처) — pytest, **지금 가능**(순수). seed 링크적재는 parse 단위까지 단위테스트.
- **4b**: `brain_note`가 백링크/아웃링크 RPC를 호출하고 응답을 채우는지(RPC 모킹, 기존 `_StubRPC` 패턴) + 404면 RPC 미호출. RPC SQL 자체는 v1처럼 Python 레이어 모킹(라이브 DB 검증은 E2E).
- **4c**: 본문 전처리 함수 vitest + `npm run build`. 패널은 build 검증.

## 7. Phasing / 의존
- **4a → 4b → 4c** 순차(4b note EP·4c 타입이 응답형태 공유). v1과 동일 3-repo/3-워크트리(새 브랜치).
- **구현 게이트 = v1 적용 후**(007+008 적용·ingest 라이브). 4a 순수 Python 테스트는 지금도 그린 가능.
- 새 마이그레이션 **009**(008 미수정). seed/lint 확장(Slice 1 산출물 확장). note EP/타입 확장(Slice 2/3 산출물 확장).

## 8. 자기검토 체크리스트
- [x] 범위 = 링크추출+백링크만(그래프·의미검색·학습 명시적 제외)
- [x] 해소 = source_path(.md 폴백), 미해소→lint
- [x] 링크테이블 = 008 기존, 009는 RPC만
- [x] 백링크/아웃링크 권한필터(서버측, 양방향 숨김)
- [x] note EP 응답 `{source_path,title}[]` ↔ FE 타입 정정 일치
- [x] lint missing-link/orphan 크로스파일(WARN)
- [x] 본문 클릭 네비(brain: href 전처리)
- [ ] 사용자 리뷰 → writing-plans
