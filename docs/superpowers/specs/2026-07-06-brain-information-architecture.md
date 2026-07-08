# ATOMOS BRAIN 정보 아키텍처 (재구성) 설계

**작성일**: 2026-07-06
**상태**: 설계 승인됨 (글렌 브레인스토밍 확정) → 구현
**관련**: `2026-07-06-glen-wiki-brain-seed-design.md`(GLEN_WORK 시드), 메모리 project_brain_knowledge_layer

## 1. 배경·문제

GLEN_WORK 1계층 86문서를 시드했으나 — 폴더구조가 **GLEN_WORK 미러**(`global/glen/entities-*·concepts·decisions`)일 뿐 ATOMOS 고유 구조가 아니다. 글렌 지적:
- 스코프 칩(global/dept:sales)이 트리와 중복 → 기능적 의미 약함.
- 폴더구조가 GLEN_WORK 그대로.
- 브랜드/매장 리포트가 어디 쌓이는지 불명확.

## 2. BRAIN 정보 아키텍처 (청사진)

BRAIN = ATOMOS 운영 지식 중추. scope 체계로 조직한다:
```
ATOMOS BRAIN  (scope = ATOMOS 고유 구조)
├ global/            회사 전반 공용
│   ├ (playbooks·규칙·개념)   grounding-rules 등 ATOMOS 운영 공용 지식
│   └ glen/          글렌 위키 참조지식 86 (출처 격리 · 재시드 깔끔)
├ dept/{도메인}/      부서 도메인 지식 (sales·cost·cogs…)  — 도메인 플레이북 (anomaly-playbook 등)
└ brand/{브랜드}/     브랜드 전략·지식·플레이북 (브랜드 직하)
    └ {매장}/
        └ {YYYY-MM}/         프로젝트 결과보고서·(향후)월 리포트   ← 파일(큐레이션 승격·년월 직하)
            └ {YYYY-MM-DD}/  그날 매일 저널                       ← store_journal DB(트리가 표시·파일 아님)
```

**핵심 원칙:**
- **통합 뷰 + 큐레이션 승격**: 위키 트리는 **통합 뷰**다 — (a)매일 저널(`store_journal` DB, 자동)을 월일자에 *읽어서 표시*(파일 승격 아님·DB-first 유지: 볼륨·구조·기계검색 그대로) + (b)"지속 가치 있는 것"(프로젝트 결과·큰 인사이트·매장/브랜드 지식)만 파일로 큐레이션 승격(년월/브랜드 직하). 저널=흐르는 기록(DB)·큐레이션 지식=안정(파일). 상세 `2026-07-07-brain-unified-tree-design.md`.
- **출처 격리**: GLEN_WORK(참조지식)는 `global/glen`에 격리 — ATOMOS 운영지식(파이프라인이 채우는 dept/brand/store)과 안 섞이고, GLEN_WORK 업데이트 시 재시드 깔끔.
- **저장 = 파일(SSOT) + DB(색인)** (glen-wiki-seed 설계 §2 그대로).

## 3. 이번에 구현하는 것 (지금 가능)

### 3.1 스코프 칩 제거 (FE)
`hbs BrainReference.tsx`의 스코프 필터 칩(global/dept:sales) 제거 — 트리가 scope 계층을 대표하므로 중복. 검색은 텍스트(q)만. scope 필터 로직 정리.

### 3.2 빈 scope 안내 (FE)
트리에 아직 비어있는 scope(`brand:`·`store:` 등)를 회색 안내로 표시:
> "🔒 아직 비어있음 — brand:{브랜드}, store:{매장}. 매장·브랜드 지식과 프로젝트 결과 보고서가 여기 쌓일 예정(S3 MRI·S4 프로젝트)."
청사진을 사용자가 이해하도록. 실데이터 없이 안내 텍스트.

### 3.3 아키텍처 spec (본 문서)
scope 체계·승격 규칙 박제 — S3/S4가 참조.

## 4. 이번에 안 하는 것 (후속)

- **glen 하위 단순화**(`entities-people/projects/org/tech` → `entities`): source_path 변경 → 재시드·링크 재변환·DB reconcile 리스크. 현행 유지, 필요 시 후속(별도 재시드 작업).
- **실제 매장/브랜드 콘텐츠 채우기**: S3(MRI)·S4(프로젝트)가 큐레이션 승격으로 채움. 파이프라인 없이는 인위적이라 미룸.
- **global 공용 지식 재편**(grounding-rules 등을 playbooks/로): 콘텐츠 늘면.
- **pgvector 의미검색**: 예약(동일 RPC 뒤 hybrid).

## 5. 승격 규칙 (S3/S4 참조용 — 이번 미구현, 계약만)

- **store: 승격 대상**: 매장 프로필(고정 정보)·프로젝트 종료 효과보고서·반복 재사용될 큰 인사이트. 매일 저널은 제외(테이블에만).
- **brand: 승격 대상**: 브랜드 전략·브랜드 공통 플레이북·브랜드 단위 인사이트.
- **승격 주체**: S4 프로젝트 종료 시 결과보고서를 knowledge 문서로 생성(파일→DB seed 동일 경로). read_tier·read_roles는 대상에 맞게.
  - **경로(트리 표시)**: `knowledge/brand/{br_id}/{st_id}/{YYYY-MM}/project-{id}.md` — 프로젝트 결과는 **년월 직하**(일자 폴더는 매일 저널 전용·저널은 store_journal DB에서 트리가 직접 표시). *(구현: `brain_promote.build_knowledge_md`, spec `2026-07-07-brain-tree-hierarchy-design.md`·`2026-07-07-brain-unified-tree-design.md`.)*
  - **scope 필드(접근 제어)**: `store:{st_id}`(또는 brand 단위면 `brand:{br_id}`) — 경로와 별개 관심사. 트리는 경로 기준, 접근은 scope 기준.
  - **표시**: 트리 세그먼트는 한글 라벨(전사 공용·부서·브랜드·매장 등)·ID→이름·월/일자 한글·문서는 한글 제목(FE `brainLabel.ts`).
- **저널→BRAIN 직접 승격 금지**: 저널은 원자료. 승격은 "사람/CEO가 가치 판단한 산물"만.

## 6. 검증

1. `/admin/brain`(ATOMOS BRAIN) — 칩 사라지고 트리만 · 빈 scope 안내 표시.
2. 트리에서 `global > glen`·`dept > sales` 정상 탐색.
3. 청사진(scope 체계)이 사용자에게 안내로 가시화.
