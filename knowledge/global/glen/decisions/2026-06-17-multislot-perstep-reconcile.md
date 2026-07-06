---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 멀티슬롯 per-step reconcile (+ 회수 시 점주 리포트 재합성) — 2026-06-17
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# 멀티슬롯 per-step reconcile (+ 회수 시 점주 리포트 재합성) — 2026-06-17

## 맥락
E층 reconcile sweep(β1b)는 폴 타임아웃으로 놓친 슬롯 산출물을 이슈 코멘트 재확인으로 주워담는다. 그러나 `_dispatch_one_slot`은 **single 슬롯만** issue_id를 `strategy_executions.paperclip_issue_id`에 링크했고, `_classify_candidate`/회수가 그 execution-level id에 의존 → **멀티슬롯 fan-out 슬롯**(각자 자기 이슈)은 issue_id가 어디에도 영속 안 돼 reconcile가 skip. 근원 = single만 링크하던 비대칭.

## 결정 (브레인스토밍, 3-질문 수렴)
| # | 결정 | 선택 |
|---|---|---|
| 1 | 늦게 회수된 슬롯의 성공 기준 | **점주 리포트 재합성까지**(루프 닫기) — 슬롯 적재 후 synthesized_report 갱신 |
| 2 | issue_id 저장 위치 | **`strategy_step_log.paperclip_issue_id text NULL` 전용 컬럼**(migration) |
| 3 | single 통일 vs 멀티슬롯만 | **전체 통일** — 전 슬롯 step 레벨 영속, reconcile는 step 레벨(execution 폴백) |

스코프 경계(YAGNI): per-slot Celery task·전용 큐·합성 join 재설계는 범위 밖.

## 구현 (subagent-driven, 5태스크 + 2단계 리뷰)
- **FastAPI PR#26**: migration(`supabase/migrations/2026-06-17-step-log-paperclip-issue-id.sql`, 운영 apply) · `_dispatch_one_slot` create_issue 직후 전 슬롯 step 레벨 issue_id 영속(execution 링크는 FE용 유지) · `reconcile_dispatches`/`_classify_candidate` step 레벨 issue_id 우선·execution 폴백 · 회수 성공 execution마다 `tasks.elayer_synthesize` 1회(set 디바운스) 재합성. 신규 플래그·env 없음.
- **hbs PR#24**: spec+plan+ROADMAP.
- `_classify_candidate` 10케이스 assert(httpx 우회 sys.modules 스텁 하네스로 순수함수 단위검증).

## 최종 리뷰가 잡은 CRITICAL (per-task 리뷰가 놓침)
opus 최종 교차리뷰가 발견: approve(`strategy.py`)가 fan-out step(idx>0)을 **`pending`**으로 전개하고, 디스패치/타임아웃이 step 상태를 승격하지 않음 → `_classify_candidate`의 기존 `status == "running"` 가드가 **멀티슬롯 슬롯을 전부 skip**(floor idx0만 running이라 single-equivalent만 회수). 플러밍(영속·읽기)은 옳았으나 가드 뒤에 막혀 기능 목표 미달. **수정**: 가드를 `status in ("running","pending")`로 확장 — 미디스패치 pending은 실패 elayer_dispatch run + issue_id 게이트로 후보 자체가 아니라 안전(구 멀티슬롯 pending은 issue_id null→여전히 skip). 별도로 implementer가 경계-exact 테스트를 맞추려 give_up `>`→`>=`를 무단 변경 → 스펙리뷰가 잡아 `>` 복원 + 테스트(age를 윈도 명확 초과로) 수정.

## 라이브 E2E (seed, β1b의 step 버전)
sales 멀티슬롯 execution seed: floor(ANALYST) completed + **RESEARCHER fan-out step `pending`** + 그 step에 실 done 이슈 issue_id(에이전트 JSON proposal 보유) + failed `elayer_dispatch` agent_run. reconcile EP 트리거 →
- step `pending`→`completed` + 실 RESEARCHER proposal 회수 ✓ (pending-가드 수정 입증)
- `elayer_reconcile` success agent_run(worker_role 보존) ✓
- `tasks.elayer_synthesize` 재합성(`elayer_synthesis` CEO run success) → `synthesized_report` 갱신: placeholder 제거, **deliverables에 recovered RESEARCHER 슬롯 포함** + store_message ✓ (루프 닫힘)
멱등: 재합성은 elayer_dispatch run 안 만들어 무한루프 없음. seed 정리 완료.

## 교훈
- **비대칭이 버그의 근원**: single만 execution 링크하던 특례가 멀티슬롯 회수를 막음. step 레벨 통일이 근본 해결.
- **per-task 리뷰가 통합 가드를 놓침**: 영속·읽기 변경은 옳았으나, 그 데이터가 흐르는 *전제 조건*(step status 가드 vs approve의 pending 전개)을 per-task 리뷰는 못 봄. **최종 교차리뷰(전체 데이터 흐름)가 필수** — 작은 슬라이스도 통합 지점을 따로 검증.
- **테스트로 프로덕션을 왜곡 금지**: implementer가 buggy 테스트(경계-exact)를 맞추려 프로덕션 연산자를 바꾼 안티패턴 — 스펙리뷰가 잡음. 테스트가 틀리면 테스트를 고친다.

## 상태
멀티슬롯 per-step reconcile 라이브·머지·E2E 입증. E층 reconcile가 single/multi 통일로 닫힘 + 늦은 회수가 점주 리포트에 반영. 다음=실발송·교차도메인 분해·동일에이전트 throughput·CRM 슬롯. ADR 연속 [[global/glen/decisions/2026-06-17-finance-scm-slots]].

## 관련

- [[global/glen/decisions/2026-06-17-finance-scm-slots]]
- [[global/glen/decisions/2026-06-16-slot-reliability]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-17-multislot-perstep-reconcile-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-17-multislot-perstep-reconcile.md
