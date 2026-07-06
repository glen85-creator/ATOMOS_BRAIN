---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: ATOMOS BRAIN 지식 레이어 — Quartz/llm-wiki 검토 + 4계층 권한 + 콘솔 내 BRAIN 참조 페이지 (2026-06-21)"
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# ADR: ATOMOS BRAIN 지식 레이어 — Quartz/llm-wiki 검토 + 4계층 권한 + 콘솔 내 BRAIN 참조 페이지 (2026-06-21)

## 컨텍스트
[[global/glen/decisions/2026-06-20-atomos-pipeline-redesign|6-20 ADR]] §5에서 ATOMOS BRAIN = GitHub markdown(폴더=스코프) + Supabase pgvector + 우리 MCP `knowledge.search(ctx)` 권한강제로 확정했다. 이번에 "Quartz + Karpathy llm-wiki 패턴을 조합해 BRAIN을 만들자"는 안을 세 1차 소스로 검증(소스검증 워크플로우): Quartz repo/docs, Karpathy gist, Allen(wikidocs) 클리핑 + pytorch.kr 토론(실제 LLM-Wiki 앱). 핵심 발견: **셋 다 접근권한·멀티테넌시가 없다.** Quartz는 정적 SSG(빌드타임 제외만, 비-md 자산은 무조건 공개; "private=빌드 제외≠인증" 공식 명시), llm-wiki는 단일 신뢰경계 패턴, LLM-Wiki 앱은 GPL-3.0(카피레프트). 동시에 "사람이 BRAIN 지식을 보는 화면"이 우리가 만드는 ATOMOS 콘솔(행동)과 같은 것인지 혼동이 있었다.

## 결정
1. **셋은 경쟁재가 아니라 같은 markdown 위 3레이어** — (유지·생성) llm-wiki 패턴 / (에이전트 서빙·권한) 우리 MCP+pgvector / (사람 열람) Quartz 또는 콘솔 페이지. 보완 관계.
2. **권한 = 우리 레이어 전담**(Quartz/llm-wiki는 권한 0). 모델 = `(role × scope)`, frontmatter(`scope`+`read_roles[]`) 단일원천. 강제 지점 = **BRAIN/MCP 런타임**(UI 아님 — "숨김=데이터가 안 옴", 클라 필터 금지).
3. **사람 4계층(단조 포함)**: STORE_OWNER(자기 store+brand점주공개+global점주안전) ⊂ HQ_STAFF(dept+brand+global) ⊂ HQ_EXEC(전 brand/dept/store 읽기) ⊂ ATOMOS_MASTER(전부+system/meta/학습지식+쓰기·큐레이션·lint). 에이전트 역할(ANALYST 등)도 같은 게이트(§4b 세션토큰). `read_roles`를 {ANALYST}→4계층+에이전트로 확장.
4. **사람 열람 표면 = (A) 콘솔 내 "BRAIN 참조" 페이지(권장)** — hbs-dashboard 동적 페이지, MCP/pgvector가 (role,scope)로 서빙, 검색(의미+키워드)·노트뷰(인용·백링크)·스코프탐색·그래프를 React 네이티브 구현. 단일 사이트·단일 로그인·민감지식 정적유출 0. **(B) Quartz 별도 정적 사이트 = 옵션**(비민감/사내공통 한정, 계층별 N빌드+SSO게이트, 민감자산 빌드제외 필수).
5. **유지 루프 = llm-wiki 패턴**(ingest/query-filed-back/lint, compile-not-retrieve) = §5의 "학습지식 v2" 구현 방법. **패턴만 차용, GPL-3.0 앱·LanceDB 미사용** → 우리 스택(pgvector+MCP)으로 구현.
6. 이 결정은 §5를 **대체가 아니라 확장**한다(spec §5a로 기록). 콘솔=행동(DO), BRAIN참조=참조(KNOW)는 별도 *표면*이나 같은 BRAIN을 읽는다 — 별도 *사이트*일 필요는 없다.

## 결과
- (+) "BRAIN 참조 화면"의 위치 혼동 해소: 콘솔의 한 페이지로 두되 지식·권한 백엔드는 BRAIN/MCP 공유.
- (+) Quartz/llm-wiki의 장점(그래프·백링크·즉시검색 / 점증 유지·filed-back compound·lint)을 *추출해 네이티브 구현*하는 명확한 차용 경계.
- (+) 보안: 민감지식은 동적 서빙(정적 HTML로 안 구움) → 유출면 최소. fail-closed 원칙 일관.
- (−) 옵션 A는 그래프/검색을 Quartz처럼 공짜로 못 얻고 직접 구현(라이브러리: react-force-graph류 + pgvector). 빌드량 존재.
- (−) llm-wiki는 ~10만 토큰 이하 우위·동시쓰기 락 미정의·compound 모순 위험 → pgvector 병행 + 병렬세션 락 + lint·사람검증 유지.

## 대안 검토
- **(기각) Quartz를 메인 BRAIN UI로** — 정적·권한0·비-md 무조건공개라 사내 다계층 지식에 부적합. 옵션 B(비민감 한정)로 강등.
- **(기각) LLM-Wiki 앱(Tauri/Rust/LanceDB) 포크** — GPL-3.0 카피레프트(사유 시스템 부적합) + LanceDB가 우리 pgvector와 중복 → 패턴만 차용.
- **(연기) 콘솔 외 별도 사이트(B)를 1차로** — 별도 인증·계층 빌드 운영부담 + 정적유출 위험 → A 우선, B는 그래프 탐색 가치가 확실할 때.

## 참고
- 정본 설계(LIVING): `ATOMOS_BRAIN:docs/superpowers/specs/2026-06-20-pipeline-redesign-design.md` §5a.
- Allen 글은 "공개 퍼블리시(is_public 바이너리)" 지향 — 우리 4계층 게이팅과 정반대 의도라 디폴트 차용 금지. Quartz "Hugo 기반"은 구버전(v4+는 TS/Preact).
- ~~미결: 4계층 frontmatter 규약 · BRAIN 참조 페이지 API/컴포넌트 계약 · 그래프/검색 구현 · v2 ingest/lint~~ → **✅ 4건 확정(2026-06-22, brainstorming→writing-plans):**
  - ① frontmatter = `read_tier`(사람 단조 하한) + `read_roles[]`(에이전트 직교, 레지스트리={ANALYST} 도메인당 증분, **legacy 13-로스터 비차용**); 생략 read_tier→ATOMOS_MASTER+lint경고(fail-closed), 구조적 무효(scope/title/enum)→lint ERROR 차단.
  - ② BRAIN 참조 = 사람 Supabase JWT를 `auth.get_user`로 검증→`app_users.role`→BRAIN tier(v1=super_admin→MASTER만 배선), **서버측 tier-aware RPC 필터(클라필터 금지)**; EP `/api/brain/{search,notes,scopes}` 404/403 통일, 페이지 `/admin/brain`.
  - ③ FTS+태그+스코프 v1 · pgvector 의미검색 예약(동일 RPC 뒤 hybrid) · 링크모델 `wikilink`→`atomos_knowledge_links` · 그래프 react-force-graph(v2).
  - ④ v1 ingest = GitHub Action(knowledge/** push→lint→seed) · lint=frontmatter 검증 · v2 학습루프=seam만(예약 컬럼+학습후보 flag), 본체 Phase 4.
  - 산출물: `ATOMOS_BRAIN/docs/superpowers/specs/2026-06-22-atomos-brain-knowledge-layer-design.md`(커밋 c504a2b) + `plans/2026-06-22-atomos-brain-knowledge-layer-v1.md`(3b052f2, 11 tasks). **사람=신규 `atomos_knowledge_search_v2`, 에이전트 Phase1 경로(007 RPC·mcp_server/tools.py) 무수정.** 구현 선행=Phase1 병합+007 적용.

## 관련

- [[global/glen/decisions/2026-06-20-atomos-pipeline-redesign]]
- [[global/glen/concepts/ATOMOS]]

## 출처(원본)

- ATOMOS_BRAIN:docs/superpowers/specs/2026-06-20-pipeline-redesign-design.md (§5/§5a)
- https://github.com/jackyzha0/quartz
- https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- https://discuss.pytorch.kr/t/llm-wiki-feat-karpathy-llm-wiki/10139
- Clippings/Obsidian + LLM + Git + Quartz 노트가 공개 지식이 되는 자동화 스택.md (Allen, wikidocs)
