# ATOMOS 옛 스택 전면 디커미션 — 설계 (Phase 3)

> 상태: **설계 — 사용자 승인됨, 스펙 검토 대기.** 2026-06-25.
> 부모: `2026-06-20-pipeline-redesign-design.md` §7(제거 대상)·§10 Phase 3(관리형 Paperclip/hermes 디커미션, Phase 1·2 검증 후). v2(매출 단일경로)는 라이브 e2e 검증 완료.

## 0. 목적 / 합격선
- **목적**: v2 단일경로(감지→Hermes 단일역할 분석+검증게이트→승인→안전도구 실행→측정→신뢰게이트 보고)가 라이브 검증됐으므로, 공존 중인 **옛 모델(CEO 게이트/합성/트리아지·다중슬롯 팬아웃·Paperclip·dispatch·600초 폴링·bytes/3)을 전면 제거**해 코드 복잡도를 크게 낮춘다.
- **합격선**: ① 옛 스택 코드/플래그/태스크/EP/FE 표면 제거 ② v2 경로(run-v2→승인→executor→리포트)·감지·콘솔·측정·발송 **불변(회귀 0)** ③ pytest·vitest·build 전부 그린 ④ 비-sales(cogs/cost/review)는 **의도적 자동처리 공백**(Phase 4까지) — 감지(인벤토리)는 유지.

## 1. 결정 (사용자)
- **전면 디커미션** 채택(부분/Phase4-우선 아님). 근거: 옛 비-sales 경로는 **사실상 휴면** — strategy_executions 통계상 어떤 도메인도 `done` 도달 이력 0, cogs-ig 최근 7일 0건(전부 cancelled), cost-util 실행 0건, review 1건(06-09). 즉 제거해도 실질 손실 0.
- **PR 분할**: BE 디커미션(PR-A) + FE 레거시 표면 제거(PR-B).

## 2. 검증된 보존/제거 경계 (ground-truth)
v2 오케스트레이터 `elayer_pipeline_v2.py`의 실제 import:
- `from app.services.atomos_bridge import _now_iso` (공용 헬퍼만)
- `from app.services.elayer_routing import use_v2_sales_path` (분기 seam만)
- `hermes_runner`·`safe_tools`·`report_gate`·`atomic_engine`·`cost` 헬퍼.

→ v2는 **fanout 라우팅(resolve_dispatch/apply_decomposition/filter_plan_by_phase/has_diagnose_slots)·PaperclipClient·CEO·dispatch_execution·triage·2-페이즈 diagnose EP 를 전혀 쓰지 않는다.** (approve EP의 v2 분기는 `resume_after_approval_v2` 호출 후 즉시 return → 레거시 `_steps_for_execution`에 도달 안 함.)

### 보존 (절대 제거 금지)
`elayer_pipeline_v2`·`hermes_runner`·`safe_tools`·`analysis_gate`·`report_gate`·`mcp_server/*`·`elayer_send`·`detection_tasks`·`atomic_engine`·`feed_classify`·`elayer_llm`(direct_llm_json, v2 재사용) + `strategy.py`의 승인(v2분기)·감사·피드·proposal·finalize EP + `elayer_routing.use_v2_sales_path` + `atomos_bridge`의 공용 헬퍼(`_now_iso` 등).

### 제거 (레거시 전용)
- 서비스: `elayer_dispatch`·`elayer_ceo_gate`·`elayer_synthesis`·`elayer_propose`·`elayer_triage`(이미 dead, consumer 0)·`elayer_reconcile`.
- Paperclip: `atomos_bridge`의 `PaperclipClient`·이슈빌더(build_*_issue)·schema_doc·`atomos_tasks.py`(bridge cycle beat).
- 라우팅 fanout: `elayer_routing`의 `_DOMAIN_SLOTS`·`SlotTarget`·`DispatchPlan`·`_Spec`·`resolve_dispatch`·`apply_decomposition`·`filter_plan_by_phase`·`has_diagnose_slots`.
- 태스크: `elayer_tasks.py`의 `elayer_dispatch`·`elayer_synthesize`·`elayer_propose`·`elayer_diagnose`·`elayer_execute`·`reconcile_dispatches`.

### consumer 맵 (blast-radius, grep 확인)
- `elayer_dispatch` ← elayer_tasks(L17)·strategy enqueue·test_hermes_dispatch.
- `elayer_ceo_gate.ceo_gate` ← elayer_dispatch(L164)만.
- `elayer_synthesis` ← elayer_tasks(L27)·admin_settings 수동 EP(L504).
- `elayer_propose` ← elayer_tasks(L63)만.
- `elayer_routing.resolve_dispatch/apply_decomposition/filter_plan_by_phase` ← strategy `_steps_for_execution`(L222)·diagnose EP(L691)·옛 모듈. 모두 **레거시 경로**.
- `PaperclipClient` ← elayer_dispatch·elayer_ceo_gate·elayer_synthesis만.

## 3. 제거 인벤토리 (BE / FE)
### BE (PR-A)
- **파일 삭제**: elayer_dispatch.py·elayer_ceo_gate.py·elayer_synthesis.py·elayer_propose.py·elayer_triage.py·elayer_reconcile.py·atomos_tasks.py.
- **슬림**: elayer_routing.py(→use_v2_sales_path만) · atomos_bridge.py(→공용 헬퍼만) · elayer_tasks.py(레거시 6태스크 제거; 비면 파일 정리).
- **strategy.py**: diagnose EP(L691~)·triage EP·`_steps_for_execution`(L216~)·approve **비-v2 분기**·dispatch enqueue 제거 → approve를 **v2-only**. (승인/감사/피드/proposal/finalize 보존.)
- **admin_settings.py**: 수동 synthesize EP·ATOMOS_BRIDGE 설정 EP 제거.
- **config.py**: 레거시 플래그 제거 — ELAYER_CEO_GATE_ENABLED·ELAYER_CEO_DECOMPOSE_ENABLED·ELAYER_DISPATCH_ENABLED·ELAYER_SYNTHESIS_ENABLED·ELAYER_HERMES_DIAGNOSE_ENABLED·ATOMOS_CEO_*·ATOMOS_BRIDGE_*·PAPERCLIP_*. (ELAYER_PIPELINE_V2_SALES_ENABLED·ELAYER_SEND_*·HERMES_VPS_*·ATOMOS_MCP_* 보존.)
- **celery_app.py**: `atomos_bridge_cycle` beat 제거(확인 후; 현재 beat엔 POS sync만이라는 매핑은 재확인).
- **tests**: test_hermes_dispatch.py 삭제 · test_v2_routing 등 use_v2_sales_path 테스트 보존 · 옛 모듈 단위테스트 제거.

### FE (PR-B)
- **ExecutionDetailModal.tsx**: 레거시 5탭/`phase=null` 폴백 블록 제거 · 레거시 `diagnose()` 호출(비-v2 행) 제거 · 레거시 Tab/costForm state 제거. **v2 phase 렌더(propose/execute/report/sent)·ProposePanel·ReportContent·ProgressPanel 보존.**
- **types.ts**: `CeoPlan.decision/reasoning/triaged_at` 제거 · `FeedItem.paperclip_issue_id` 제거. (ExecPhase·CeoPlan 신형 필드 diagnosis_summary/items/selected_kinds 보존.)
- **overviewData.ts**: `paperclipIssueId()` 헬퍼·mock 참조 제거.

## 4. 안전 순서 (leaf-first · 각 단계 build+test 그린 유지)
1. dead leaf: elayer_triage 제거.
2. **호출부 차단**: strategy.py/admin_settings/elayer_tasks의 레거시 enqueue·EP 제거 → approve를 v2-only화.
3. orphaned 서비스 삭제: elayer_dispatch·elayer_ceo_gate·elayer_synthesis·elayer_propose·elayer_reconcile.
4. 슬림: elayer_routing·atomos_bridge.
5. config·celery 정리.
6. (PR-B) FE 레거시 제거 — **diagnose() 호출 제거는 BE diagnose EP 제거와 동기/선행**(휴면 행이라 위험 낮음).
7. 테스트 정리 + 전체 그린(pytest·vitest·build).

## 5. DB / env
- `paperclip_issue_id`·옛 `ceo_plan` 컬럼은 **잔존**(과거행 호환·롤백 안전). 코드 참조만 제거.
- Railway 레거시 env(ATOMOS_CEO_*·ATOMOS_BRIDGE_*·PAPERCLIP_*·ELAYER_CEO_*·ELAYER_DISPATCH/SYNTHESIS/HERMES_DIAGNOSE)는 **글렌 수동 정리**(코드 제거 후).

## 6. 검증
- BE: 각 단계 후 `venv/bin/python -m pytest -q --ignore=scripts` 그린. import/EP 회귀 0.
- FE: `npx tsc --noEmit` + `npx vitest run` + `npm run build` 그린.
- e2e(글렌): run-v2→승인→executor→리포트 1회로 v2 경로 불변 확인(디커미션 후).

## 7. 위험
- 부분 마이그레이션 위험 → 호출부 차단(2단계)을 한꺼번에 해 approve를 v2-only로 확정 후 모듈 삭제.
- FE↔BE diagnose EP 결합 → FE PR-B에서 레거시 diagnose 호출 제거를 BE와 동기.
- elayer_tasks 제거 시 Celery beat의 orphaned 태스크 참조 없도록 beat 동시 정리.
- 보존 함수(use_v2_sales_path)·헬퍼(_now_iso) 오삭제 금지 — 슬림 시 정확히 보존.

## 8. 범위 외
Phase 4(비-sales 도메인 cogs/cost/review를 v2로 확장 + 마케팅 트랙 + 학습지식 v2) · §3c 추가 컨텍스트(캘린더/상권) · VPS hermes config 자동배포 · 풀 유저 인증(실 점주 발송). 모두 별도.
