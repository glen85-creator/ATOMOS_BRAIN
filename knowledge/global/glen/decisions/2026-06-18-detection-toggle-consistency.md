---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 감지 토글 일관성 — 홈 피드 도메인 필터"
tags: [domain/atomos, domain/frontend, status/done, priority/medium, glen-wiki, type/decision]
---
# ADR: 감지 토글 일관성 — 홈 피드 도메인 필터

## 맥락 — 글렌의 발견

감지 기준 탭에서 도메인을 체크 해제(`enable_*=false`)해도, **이미 감지·등록된 제안이 ATOMOS 콘솔의 홈·감지 양쪽에 그대로 남아** 헷갈린다. "하나의 주제씩 검증" 전략상 끈 감지는 화면에서도 일관되게 사라져야 테스트가 명확해진다. (디테일 리스트 작업 hbs#46/#47 — 공식·등급에 라이브 임계값 치환·수치→등급 사다리 — 직후 이어진 후속.)

## Phase 1 조사 (systematic-debugging)

- **🔍 감지 탭(`DetectionPanel`)**: 모든 카드·상세가 `EN`(enable_*)로 게이팅(`visible = DOMAIN_META.filter(m => EN[m.id])`). 저장 시 `["detection-settings"]` 무효화 → 재계산 → 카드 숨김. **로직 정상**, 잔존은 스테일(새로고침 전).
- **🏠 홈(`OperatorHome`)**: `GET /api/strategy/feed` 4그룹을 `enable_*` **전혀 안 보고** 렌더(client측 매장 필터만). → **과거 등록건 잔존 = 진짜 원인.**
- `FeedItem.trigger_context.domain` 보유(자동감지 `detection_tasks.py`: sales/cogs-ig/cost-util/cost-contract/review; 수동 propose: store/propagation 등) → **FE에서 도메인→enable_* 매핑 필터 가능, BE 0.**

## 결정 (brainstorming, 글렌 승인)

- "정리" = **숨김(필터), 되돌림 가능** (삭제·상태변경 아님). FE 전용.
- 감지 탭은 정상 → 무변경.

## 구현 (hbs#48, FE only)

- `detectionCatalog.ts`: `enableKeyForDomain(raw)`(접두어 매핑; `propagation`→enable_opportunity 포함)·`isDomainEnabled(raw, settings)`(key 없음||settings 없음→true=fail-open). + vitest.
- `OperatorHome.tsx`: `settingsQ=['detection-settings']` 로드 → 4그룹 `byDomain(byStore(...))` 합성 → `hiddenByDomain` 카운트 → 🔕 숨김 안내 스트립(`/admin/atomos` 링크). 되돌림=저장 시 쿼리 무효화→자동 재등장.

## 5차원 적대 리뷰 (워크플로 — ultracode)

스펙·필터정확성·도메인매핑완전성·되돌림/캐시·통합회귀 5차원 병렬 리뷰 → 각 지적 적대 검증. **11건 중 8건 반증, 확정 3건 반영:**
1. **유령 매장 칩**(minor) — `storeLabels`가 unfiltered에서 도출돼, 전부 숨겨진 매장 칩을 누르면 빈 화면. → `visibleItems`(도메인 필터 통과분)에서 도출 + 선택 고아 시 `activeStore` 전체 폴백.
2. **기회 토글 dead**(minor) — 수동 '우수사례 전파' 제안은 domain=`propagation`인데 매핑 없어 기회 토글로 안 숨겨짐(fail-open). → `propagation`→enable_opportunity 매핑 추가 + 테스트.
3. **로드 깜빡임**(nit) — feed가 settings보다 먼저 resolve되면 fail-open로 잠깐 노출 후 사라짐. → 로딩 게이트에 `settingsQ.isLoading` 포함(retry:false라 에러 시 즉시 통과).

## 교훈

- "끄면 사라진다"는 한 토글이 여러 surface(감지 탭·홈)에 일관 적용돼야 — surface별로 게이팅 유무가 갈리면 혼란. 근본은 홈 피드 EP가 enable_* 무인지였음.
- 작은 FE 슬라이스라도 다차원 적대 리뷰가 유령 칩·dead 토글 같은 **상호작용 결함**(단위 테스트로 안 잡히는)을 포착. fail-open은 안전하지만 "안 숨겨짐"을 조용히 유발 → 매핑 완전성 점검 필수.
- 글렌 오정지 후 워크플로 `resumeFromRunId`로 캐시 재개(완료 에이전트 즉시 반환).

다음: 데이터 근거성 점검(AI 본사 답변이 트리거 수치 인용하는지) · 항목별 세부 제외 · P4 원가업로드 행.

## 관련

- [[global/glen/decisions/2026-06-18-detection-criteria-tab]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/superpowers/specs/2026-06-18-detection-toggle-consistency-design.md
