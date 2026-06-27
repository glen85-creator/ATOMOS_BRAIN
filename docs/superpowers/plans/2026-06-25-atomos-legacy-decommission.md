# ATOMOS 옛 스택 전면 디커미션 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v2 단일경로가 라이브 검증됐으므로 공존 중인 옛 모델(CEO 게이트/합성/트리아지·다중슬롯 팬아웃·Paperclip·dispatch·600초 폴링)을 전면 제거하되, v2·감지·콘솔·측정·발송은 회귀 0으로 보존한다.

**Architecture:** 디커미션(코드 삭제) — 기능 추가 아님. 따라서 각 태스크 = "제거/수정 → 회귀 게이트(기존 테스트·빌드 그린) → 커밋". leaf-first 순서로 호출부를 먼저 끊어 orphan을 만든 뒤 모듈 삭제. 보존 경계는 ground-truth 검증됨(spec §2). BE(PR-A)·FE(PR-B) 분리.

**Tech Stack:** FastAPI(Python, pytest) · React/TS(hbs-dashboard, vitest/tsc/vite). 정본 = WSL `~/wt/pv2-fastapi`(BE)·hbs 워크트리(FE). 편집은 UNC 직접.

**보존 절대 금지목록(spec §2):** `elayer_pipeline_v2`·`hermes_runner`·`safe_tools`·`analysis_gate`·`report_gate`·`mcp_server/*`·`elayer_send`·`detection_tasks`·`atomic_engine`·`feed_classify`·`elayer_llm` + strategy.py 승인(v2분기)·감사·피드·proposal·finalize + `elayer_routing.use_v2_sales_path` + `atomos_bridge._now_iso`(및 생존코드가 쓰는 헬퍼).

**BE 회귀 게이트(매 태스크):** `cd ~/wt/pv2-fastapi && venv/bin/python -m pytest -q --ignore=scripts` → 그린(현재 270 passed 기준; 삭제된 테스트만큼 감소는 정상).
**FE 회귀 게이트:** `cd <hbs-worktree> && npx tsc --noEmit && npx vitest run && npm run build` → 그린.

---

## Part A — BE 디커미션 (PR-A)

**브랜치 준비(태스크 전 1회):**
- [ ] `cd ~/wt/pv2-fastapi && git fetch origin -q && git checkout -b feat/phase3-decommission-be origin/main`
- [ ] 베이스라인 게이트: `venv/bin/python -m pytest -q --ignore=scripts` → "N passed" 기록(기준선).

### Task A1: dead leaf 제거 (elayer_triage)
**Files:** Delete `app/services/elayer_triage.py` · Delete `tests/test_elayer_triage*.py`(있으면)

- [ ] **Step 1: consumer 0 재확인** — `grep -rn "elayer_triage\|triage_execution" app tests` → strategy.py·태스크에서 호출 없음 확인(spec: consumer 0). 만약 strategy.py에 triage EP가 있으면 Task A2에서 함께 처리하므로 여기선 import만 확인.
- [ ] **Step 2: 파일 삭제** — `git rm app/services/elayer_triage.py` (+ 해당 테스트 있으면 `git rm`).
- [ ] **Step 3: 게이트** — `venv/bin/python -m pytest -q --ignore=scripts` → 그린(ImportError 0).
- [ ] **Step 4: 커밋** — `git commit -m "chore(decom): remove dead elayer_triage (consumer 0)"`

### Task A2: strategy.py 레거시 경로 제거 (approve를 v2-only로)
**Files:** Modify `app/api/routes/strategy.py`
**주의:** 가장 정교한 태스크. 아래 심볼/블록을 **전체** 제거하되 v2·승인·감사·피드·proposal·finalize는 보존. 줄번호는 편집 중 이동하므로 **심볼명으로 찾아** 블록 단위 제거.

- [ ] **Step 1: 제거 대상 식별(읽기)** — strategy.py에서 다음을 찾는다: (a) `def _steps_for_execution(` (≈L216, `elayer_routing` import 포함 함수 전체), (b) diagnose EP(≈L691, `has_diagnose_slots`/`resolve_dispatch`/`filter_plan_by_phase` 사용하는 `@router.post(".../diagnose")` 핸들러 전체), (c) triage EP(`@router.post(".../triage")` 핸들러 전체, 있으면), (d) `approve_execution`의 **비-v2 분기** — v2 분기(`if settings.ELAYER_PIPELINE_V2_SALES_ENABLED and body.selected_actions is not None:` … `return …` ≈L904-927)는 보존하고, 그 `return` **이후**의 레거시 본문(관문① ceo_plan 병합·`_steps_for_execution(execution)`·`tasks.elayer_*` enqueue ≈L929-끝) 제거.
- [ ] **Step 2: 제거 실행** — (a)(b)(c) 함수/핸들러 전체 삭제. (d) approve_execution을 v2 분기 + 공통 가드(검증/감사)만 남기고 레거시 본문 삭제. `from app.services.elayer_routing import resolve_dispatch, apply_decomposition, filter_plan_by_phase, has_diagnose_slots` 임포트 라인 삭제(파일 내 다른 곳 미사용 확인). `use_v2_sales_path` 임포트는 보존.
- [ ] **Step 3: 남은 참조 확인** — `grep -n "resolve_dispatch\|apply_decomposition\|filter_plan_by_phase\|has_diagnose_slots\|_steps_for_execution\|dispatch_execution\|triage_execution\|tasks.elayer_" app/api/routes/strategy.py` → 0건.
- [ ] **Step 4: 게이트** — `pytest -q --ignore=scripts`. v2 승인 경로 테스트(test_pipeline_v2: approve/resume) 통과 확인. diagnose/triage EP 테스트가 있었으면 그건 제거(다음 단계 또는 여기서 `git rm`).
- [ ] **Step 5: 커밋** — `git commit -am "refactor(decom): strategy.py approve를 v2-only로 — diagnose/triage EP·_steps_for_execution·레거시 dispatch 분기 제거"`

### Task A3: 레거시 Celery 태스크 제거 (elayer_tasks.py)
**Files:** Modify/Delete `app/tasks/elayer_tasks.py` · Modify `app/core/celery_app.py`

- [ ] **Step 1: 함수 제거** — elayer_tasks.py에서 `elayer_dispatch`·`elayer_synthesize`·`elayer_propose`·`elayer_diagnose`·`elayer_execute`·`reconcile_dispatches` `@shared_task` 함수 전체 삭제. 파일에 남는 태스크가 없으면 파일 전체 `git rm`(그 경우 celery_app·다른 곳의 import도 제거).
- [ ] **Step 2: beat·import 정리** — `grep -rn "elayer_tasks\|reconcile_dispatches\|tasks.elayer_" app/core` → celery_app.py의 beat schedule에 옛 태스크/`atomos_bridge_cycle` 항목 있으면 제거. (POS sync 스케줄은 보존.)
- [ ] **Step 3: 게이트** — `pytest -q --ignore=scripts` + `venv/bin/python -c "import app.core.celery_app"` → 에러 0.
- [ ] **Step 4: 커밋** — `git commit -am "chore(decom): remove legacy elayer_* celery tasks + beat"`

### Task A4: admin_settings.py 레거시 EP 제거
**Files:** Modify `app/api/routes/admin_settings.py`

- [ ] **Step 1: 제거** — 수동 synthesize EP(`@router.post(".../synthesize/{execution_id}")` + `synthesize_execution` import) 삭제. ATOMOS_BRIDGE 설정 EP(있으면 `bridge-settings` GET/PUT) 삭제. detection_settings EP는 보존.
- [ ] **Step 2: 참조 확인** — `grep -n "synthesize\|ATOMOS_BRIDGE\|atomos_bridge" app/api/routes/admin_settings.py` → 0건.
- [ ] **Step 3: 게이트** — `pytest -q --ignore=scripts` 그린.
- [ ] **Step 4: 커밋** — `git commit -am "chore(decom): remove admin manual-synthesize + bridge-settings EP"`

### Task A5: orphaned 서비스 모듈 삭제
**Files:** Delete `app/services/elayer_dispatch.py`·`elayer_ceo_gate.py`·`elayer_synthesis.py`·`elayer_propose.py`·`elayer_reconcile.py` · Delete `tests/test_hermes_dispatch.py`(+옛 모듈 단위테스트)

- [ ] **Step 1: orphan 재확인** — `grep -rn "elayer_dispatch\|elayer_ceo_gate\|elayer_synthesis\|elayer_propose\|elayer_reconcile\|ceo_gate\|synthesize_execution\|propose_execution\|reconcile_dispatches" app` → 0건(A2~A4로 호출부 제거됨).
- [ ] **Step 2: 삭제** — 위 5개 서비스 파일 `git rm` + `tests/test_hermes_dispatch.py` `git rm` + 옛 모듈 전용 테스트(`grep -rln "elayer_dispatch\|ceo_gate\|synthesize_execution\|propose_execution" tests`) `git rm`.
- [ ] **Step 3: 게이트** — `pytest -q --ignore=scripts` 그린(import 해소 확인).
- [ ] **Step 4: 커밋** — `git commit -m "chore(decom): delete orphaned legacy services (dispatch/ceo_gate/synthesis/propose/reconcile) + tests"`

### Task A6: elayer_routing.py 슬림 (use_v2_sales_path만)
**Files:** Modify `app/services/elayer_routing.py` · Modify `tests/test_v2_routing.py`(있으면)

- [ ] **Step 1: 슬림** — `use_v2_sales_path()` 함수와 그 docstring/import만 남기고 `_DOMAIN_SLOTS`·`SlotTarget`·`DispatchPlan`·`_Spec`·`resolve_dispatch`·`apply_decomposition`·`filter_plan_by_phase`·`has_diagnose_slots` 전부 삭제. (use_v2_sales_path가 dataclass/Spec를 안 쓰는지 확인 — 안 씀.)
- [ ] **Step 2: 테스트 정리** — test_v2_routing.py에서 `use_v2_sales_path` 테스트는 보존, `resolve_dispatch`/`apply_decomposition`/`filter_plan_by_phase`/`has_diagnose_slots` 테스트는 삭제. test_mcp_tool_surface 등 use_v2_sales_path 참조는 불변.
- [ ] **Step 3: 참조 확인** — `grep -rn "resolve_dispatch\|apply_decomposition\|filter_plan_by_phase\|has_diagnose_slots\|_DOMAIN_SLOTS\|SlotTarget\|DispatchPlan" app tests` → 0건.
- [ ] **Step 4: 게이트** — `pytest -q --ignore=scripts` 그린.
- [ ] **Step 5: 커밋** — `git commit -am "refactor(decom): slim elayer_routing to use_v2_sales_path only"`

### Task A7: atomos_bridge.py 슬림 + atomos_tasks 제거
**Files:** Modify `app/services/atomos_bridge.py` · Delete `app/tasks/atomos_tasks.py`(있으면)

- [ ] **Step 1: 생존 헬퍼 식별** — `grep -rn "from app.services.atomos_bridge import\|atomos_bridge\." app | grep -v "app/services/atomos_bridge.py"` → 생존 코드(elayer_pipeline_v2 등)가 import하는 심볼 목록 확보(최소 `_now_iso`). 그 심볼만 보존.
- [ ] **Step 2: 제거** — `PaperclipClient` 클래스·`build_*_issue` 빌더·`PROPOSAL_SCHEMA_DOC`/`REVIEW_SCHEMA_DOC`/`CONTENT_SCHEMA_DOC`·`_SALES_CHANNELS`·`atomos_bridge_cycle`·polling 헬퍼 삭제. Step1에서 확인한 생존 헬퍼는 보존. atomos_tasks.py 있으면 `git rm` + celery_app beat 참조 제거(A3에서 못했으면).
- [ ] **Step 3: 참조 확인** — `grep -rn "PaperclipClient\|build_sales_issue\|build_review_issue\|build_cost_issue\|build_cogs_issue\|atomos_bridge_cycle" app tests` → 0건.
- [ ] **Step 4: 게이트** — `pytest -q --ignore=scripts` 그린.
- [ ] **Step 5: 커밋** — `git commit -am "chore(decom): slim atomos_bridge to shared helpers; remove PaperclipClient + bridge cycle"`

### Task A8: config.py 레거시 플래그 제거
**Files:** Modify `app/core/config.py`

- [ ] **Step 1: 제거** — 다음 설정 정의 삭제: `ELAYER_CEO_GATE_ENABLED`·`ELAYER_CEO_DECOMPOSE_ENABLED`·`ELAYER_DISPATCH_ENABLED`·`ELAYER_SYNTHESIS_ENABLED`·`ELAYER_HERMES_DIAGNOSE_ENABLED`·`ATOMOS_CEO_AGENT_ID`·`ATOMOS_CEO_GATE_MODEL`·`ATOMOS_CEO_GATE_TIMEOUT_SEC`·`ATOMOS_CEO_GATE_RETRIES`·`ATOMOS_CEO_GATE_Z_THRESHOLD`·`ELAYER_SALES_MARKETING_ENABLED`·`ELAYER_SALES_CRM_ENABLED`·`ATOMOS_BRIDGE_*`·`PAPERCLIP_*`·`ATOMOS_*_AGENT_ID`/`ATOMOS_*_MODEL`(ANALYST 등 슬롯 에이전트, v2 미사용). **보존**: `ELAYER_PIPELINE_V2_SALES_ENABLED`·`ELAYER_SEND_*`·`ATOMOS_SEND_*`·`HERMES_VPS_*`·`HERMES_BIN/MODEL/PROVIDER`·`ATOMOS_MCP_*`·`KMA_SERVICE_KEY` 등.
- [ ] **Step 2: 참조 확인** — 삭제한 각 설정명을 `grep -rn "<name>" app tests` → 0건(0 아니면 그 참조도 정리).
- [ ] **Step 3: 게이트** — `pytest -q --ignore=scripts` 그린 + `venv/bin/python -c "from app.core.config import settings"` 에러 0.
- [ ] **Step 4: 커밋** — `git commit -am "chore(decom): remove legacy CEO/dispatch/bridge/paperclip config flags"`

### Task A9: BE 최종 회귀 + PR-A
- [ ] **Step 1: 전체 게이트** — `venv/bin/python -m pytest -q --ignore=scripts` → 그린. `grep -rn "elayer_dispatch\|ceo_gate\|PaperclipClient\|dispatch_execution\|_DOMAIN_SLOTS\|atomos_bridge_cycle" app` → 0건(최종 확인).
- [ ] **Step 2: 푸시** — `git push -u origin feat/phase3-decommission-be`
- [ ] **Step 3: PR-A 생성** — GCM 토큰 + GitHub API(reference_pr_automation_gcm 패턴), base=main. 본문에 제거 인벤토리·게이트 결과·"비-sales 자동처리 공백(Phase4)" 명시. 머지는 글렌 승인 후.

---

## Part B — FE 디커미션 (PR-B)

**브랜치 준비:** hbs 워크트리에서 `git fetch origin -q && git checkout -b feat/phase3-decommission-fe origin/main`. (없으면 `using-git-worktrees`로 hbs 워크트리 생성.) 베이스라인 게이트 기록.
**주의:** FE의 레거시 `diagnose()` 호출 제거는 BE diagnose EP 제거(A2)와 정합 — 휴면 행이라 위험 낮으나 PR-A 머지와 가깝게 배포.

### Task B1: types.ts 레거시 필드 제거
**Files:** Modify `src/api/types.ts`

- [ ] **Step 1: 제거** — `CeoPlan` 인터페이스에서 `decision`·`reasoning`·`triaged_at` 필드 삭제(신형 `diagnosis_summary`/`items`/`selected_kinds`/`source`/`proposed_at`는 보존). `FeedItem`에서 `paperclip_issue_id` 필드 삭제.
- [ ] **Step 2: 게이트** — `npx tsc --noEmit` → 타입에러 나는 참조 지점 목록 확보(B2/B3에서 정리). 이 단계는 tsc 에러가 B2/B3 대상이면 묶어서 통과시킨다(순서상 B3까지 마친 뒤 그린).
- [ ] **Step 3: 커밋(묶음)** — B1~B3를 한 커밋으로 묶어도 됨(타입 의존). 또는 B3 후 일괄 커밋.

### Task B2: overviewData.ts paperclip 참조 제거
**Files:** Modify `src/pages/atomic/overviewData.ts`

- [ ] **Step 1: 제거** — `paperclipIssueId()` 헬퍼 함수 + 그 호출처 + mock(`buildDemoFeed` 등)의 `paperclip_issue_id` 제거.
- [ ] **Step 2: 게이트** — `npx tsc --noEmit`(B1과 묶어).

### Task B3: ExecutionDetailModal.tsx 레거시 폴백 제거
**Files:** Modify `src/pages/atomic/ExecutionDetailModal.tsx`

- [ ] **Step 1: 제거** — `phase=null` 레거시 5탭 폴백 블록(`{!diagLoading && !phase && ( … )}` 전체)·레거시 `diagnose()` 호출(비-v2 행 진입)·레거시 `Tab` 타입/`tab` state/`costForm` state/`handleFinalize`·`handleCostSubmit`(레거시 전용) 삭제. **보존**: v2 phase 렌더(propose/execute/report/sent)·`ProposePanel`·`ReportContent`·`ProgressPanel`·`ToolActionPanel`·`ExecutionDetail`(신형). `ceo_plan.diagnosis_summary` 참조(신형)는 보존.
- [ ] **Step 2: 참조 확인** — `grep -rn "paperclip_issue_id\|paperclipIssueId\|triaged_at\|\.decision\b" src/pages/atomic src/api/types.ts` → 레거시 0건.
- [ ] **Step 3: 게이트** — `npx tsc --noEmit && npx vitest run && npm run build` → 전부 그린.
- [ ] **Step 4: 커밋** — `git commit -am "refactor(decom): remove FE legacy stack surface (5-tab fallback·diagnose·ceo triage fields·paperclip refs)"`

### Task B4: FE 최종 회귀 + PR-B
- [ ] **Step 1: 전체 게이트** — `npx tsc --noEmit && npx vitest run && npm run build` 그린.
- [ ] **Step 2: 푸시 + PR-B** — `git push -u origin feat/phase3-decommission-fe` → PR(base=main). 머지는 글렌 승인 후, **PR-A와 함께/직후** 배포(EP 정합).

---

## Self-Review (작성자 체크)
- **Spec 커버리지**: §3 BE 인벤토리 → A1~A8. FE 인벤토리 → B1~B3. §4 안전순서 → A1(leaf)→A2(호출부)→A5(orphan)→A6/A7(슬림)→A8(config). §5 DB/env → A8(코드)·Railway는 글렌 수동(plan 밖). §6 게이트 → 매 태스크. ✅
- **플래스홀더 스캔**: "TBD/적절히/etc" 없음. 줄번호는 이동성 때문에 심볼명+근사 줄로 지정(의도적). ✅
- **타입 일관성**: 보존 심볼명(use_v2_sales_path·_now_iso·run_analysis_v2·resume_after_approval_v2) 일관. ✅
- **위험**: A2가 최정교(approve 외과수술) → subagent-driven + 태스크간 리뷰 권장. 각 태스크 회귀게이트가 안전망.
