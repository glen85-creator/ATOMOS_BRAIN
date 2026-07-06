---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: E층 플로우 재설계 — CEO 트리아지-먼저 (승인 = CEO 플랜) — 2026-06-17
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# E층 플로우 재설계 — CEO 트리아지-먼저 (승인 = CEO 플랜) — 2026-06-17

## 맥락 / 문제
글렌이 콘솔에서 자동감지 매출급락 건을 실사용 테스트하며 3가지 구조적 문제를 발견:
1. **블라인드 승인** — 사람은 감지(raw 신호)만 보고 승인. CEO 판단(게이트·분해 이유)이 내부에 숨겨져 안 보임.
2. **7단계 혼란** — 승인이 full plan(7슬롯)을 step_log로 전개하는데, dispatch는 CEO 동적분해 후 일부 슬롯만 실행 → 선택 안 된 슬롯이 영구 `pending` 고착(답 안 옴).
3. 코헌트한 CEO 산출(합성 리포트)은 맨 끝에야 나옴.

근본 원인: CEO 게이트+분해가 **승인 後·내부**에서 돎. 글렌 멘탈모델 = 감지→CEO가 먼저 분석·제안→사람이 그 플랜을 승인→실행. 즉 게이트+분해를 **승인 前·표면**으로 옮겨야 함.

## 결정 (브레인스토밍)
- **타이밍**: Lazy — proposed 항목 상세를 열 때 1회 트리아지, `ceo_plan` 영속(이후 즉시 cached).
- **속도**: 빠른 직접 CEO콜(`direct_llm_json` deepseek ~4s) — 에이전틱 Paperclip 라운드트립(~3분) 회피. 실패→통계 폴백(즉시).
- **플랜 상호작용**: 승인/반려만(MVP). 슬롯 편집은 후속.
- **NO_GO/HOLD**: advisory — 카드에 표시하되 승인 버튼 살아있음, 오버라이드 시 최소 floor(ANALYST) 실행.
- **하위호환**: `ceo_plan` 없는 execution(미트리아지)은 기존 경로(승인 후 dispatch 내 게이트+분해) 폴백.
- **단일 seam**: `apply_decomposition(plan, selected_kinds)`를 triage·approve·dispatch 3곳이 동일 호출. triage가 `selected_kinds`를 정해 영속하면 두 소비자가 같은 필터를 재적용.

## 구현 (subagent-driven, 5 코드태스크 + 컨트롤러)
- **migration**: `strategy_executions.ceo_plan jsonb`(가산적 nullable, `IF NOT EXISTS`). null=미트리아지.
- **`app/services/elayer_triage.py`** (신규): `triage_execution(execution)` = `resolve_dispatch` → `build_ceo_gate_issue`+`direct_llm_json`(에이전틱 회피) → `_statistical_fallback` → `apply_decomposition`. 최상위 try **fail-open**(절대 raise 안 함, source=error_failopen). 순수 `_plan_from_verdict(plan, verdict, source)`. 무거운 import는 deferred(httpx-free 테스트 + 순환 가드).
- **`app/api/routes/strategy.py`**: triage EP `POST /executions/{id}/triage`(멱등; `source=error_failopen`만 재트리아지; triaged_at 스탬프). `_steps_for_execution`이 `ceo_plan.selected_kinds` 있으면 `apply_decomposition`으로 선택 슬롯만 전개, 없으면 full plan(하위호환). approve 쿼리는 narrowing select 없어 ceo_plan 자동 포함 — 무변경.
- **`app/services/elayer_dispatch.py`**: `dispatch_execution`이 `ceo_plan.selected_kinds`(list) 있으면 **재게이트 스킵**·selected_kinds 필터; `elif ELAYER_CEO_GATE_ENABLED`로 기존 게이트 경로 보존(하위호환). NO_GO 조기리턴은 미트리아지 게이트 경로만(트리아지된 건 사용자가 승인해 도달=advisory).
- **hbs `ApprovalDetail.tsx`**: "🧠 CEO 제안 카드"(결정 배지·이유·담당팀 한글라벨) + lazy triage useQuery(staleTime∞·retry false). NO_GO/HOLD advisory 주의문. `CeoPlan` 타입·`strategyExecApi.triage`.
- 각 코드태스크 2단계 리뷰(스펙→코드품질). 최종 opus **통합리뷰**: seam 멱등(fixed-point: `apply_decomposition(plan, [s.issue_kind for s in apply_decomposition(plan, X).slots]) == apply_decomposition(plan, X)`, 8케이스 입증)·ceo_plan 키 round-trip(writer/FE/소비자 정확 일치)·하위호환·never-raise 전부 PASS.

## 라이브 E2E (성공회대점 z=-3.4 sales)
- **트리아지**: `cached:false`, decision **GO**, `selected_kinds=[sales, sales-research, sales-promo]`(7중 3 선택), `source:direct`(빠른 deepseek 라이브, 통계폴백 아님), **4.0s**.
- **재트리아지**: `cached:true`, 동일 플랜, **0.75s**(no LLM) — 멱등.
- **승인**: 정확히 **3스텝** 전개(7 아님) = selected_kinds.
- **디스패치**: 재게이트 없이 3슬롯 fan-out → 전부 `completed`, **orphaned pending 0**(글렌 "7단계 혼란" 해결 입증) → 합성 리포트 생성(~5분, 파이프라인 종착 닫힘).
- **하위호환**: 미트리아지 execution 승인 → **7스텝 full plan**(게이트 경로).
- 단일-seam 불변식: CEO 카드 3 = 승인 3 = 디스패치 3.

## 교훈
- **실사용이 아키텍처 결함을 드러냄**: 게이트+분해의 위치(승인 後 vs 前)가 UX·정합성을 좌우. 글렌의 "CEO가 먼저 제안하고 그걸 승인하는 게 맞지 않나"가 정확한 진단.
- **단일 필터 seam의 가치**: `apply_decomposition`을 triage·approve·dispatch가 공유 → 세 곳이 같은 슬롯 집합 보장(fixed-point). 만약 각자 다른 로직이었으면 orphaned pending이 재발.
- **빠른 직접 CEO ≠ 에이전틱 CEO**: lazy-on-open UX엔 ~3분 에이전틱 라운드트립 부적합 → direct deepseek(~4s)+통계 폴백. 게이트/합성의 직접폴백 인프라 재사용.
- **never-raise는 끝까지**: 코드리뷰가 `resolve_dispatch`/폴백이 try 밖이던 갭 포착 → 최상위 fail-open 가드(ceo_gate 패턴 미러).

## 상태
E층 플로우 재설계 라이브·머지·E2E 입증. ATOMOS E층의 사용자 접점(승인)이 "블라인드 감지"에서 "CEO 플랜"으로 전환. 다음=throughput·카톡/SNS 채널·실 점주 수신자(풀인증 선결)·교차도메인 분해. 곁버그(별도 슬라이스): ANALYST PAPERCLIP_API_KEY 마스킹→실패 완료 오표기·유효 JSON raw 캡처. ADR 연속 [[global/glen/decisions/2026-06-17-crm-sales-slot]].

## 관련

- [[global/glen/decisions/2026-06-17-crm-sales-slot]]
- [[global/glen/decisions/2026-06-17-elayer-send-email]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-17-elayer-triage-flow-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-17-elayer-triage-flow.md
