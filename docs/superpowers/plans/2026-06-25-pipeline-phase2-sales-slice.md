# Phase 2 매출 수직 슬라이스 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 매출 이상 1건을 CEO·슬롯·Paperclip 없이 감지→단일역할 Hermes 분석+검증게이트→도구액션 승인→안전도구 레지스트리 실행→측정→보고 신뢰게이트까지 새 경로(플래그 뒤)로 관통.

**Architecture:** 옛 elayer_dispatch/CEO/슬롯/Paperclip 스택은 공존(제거는 Phase 3). 신경로는 플래그 ELAYER_PIPELINE_V2_SALES_ENABLED 뒤 단일 오케스트레이터(app/services/elayer_pipeline_v2.py)가 동기 관통. 분석엔진(hermes_runner)·MCP·검증게이트·승인/감사·측정 EP·발송 어댑터는 재사용, 신축은 안전도구 레지스트리와 보고 신뢰게이트 2곳.

**Tech Stack:** FastAPI + Celery + Supabase(PostgREST httpx) + Pydantic v2 / React+TS+Vite+Vitest. 테스트: FastAPI `cd ~/FastAPI && venv/bin/python -m pytest tests/<f> -q` (asyncio.run + monkeypatch idiom, NO pytest-asyncio marker); hbs `cd ~/hbs-dashboard && npx vitest run <path>` (순수 헬퍼 단위).

---

## Canonical Interfaces (authoritative)

이 슬라이스의 모든 이름은 아래 계약을 따른다. 어떤 드래프트가 다른 이름을 쓰면 이 계약으로 재작성한다.

**라우팅 / 플래그**
- `app/core/config.py` → `ELAYER_PIPELINE_V2_SALES_ENABLED: bool = False`
- `app/services/elayer_routing.py` → `use_v2_sales_path(domain: Optional[str], settings_obj=None) -> bool` (플래그 ON AND domain in (None,'sales'))

**오케스트레이터 (NEW `app/services/elayer_pipeline_v2.py`)**
- `async def run_analysis_v2(execution_id: str) -> dict` — analyze→validate_analysis→proposed_actions 영속→phase `'propose_v2'`에서 STOP. soft-fail(절대 raise 안 함; AnalysisFailed → phase `'analysis_failed'` + step failed). 멱등: phase in ('propose_v2','report','sent') 또는 proposed_actions_v2 존재 → already-done.
- `async def resume_after_approval_v2(execution_id: str, selected_action_ids: list[str]) -> dict` — 선택 액션(proposed_actions_v2[index])→tool params→`safe_tools.run_tool`→실행 前 `_capture_baseline` / 後 `_measure`→`report_gate.validate_report`→통과 시 `synthesized_report` draft 기록 + phase `'report'`. soft-fail. 멱등: phase in ('report','sent') → already.
- `def _build_v2_agenda(execution: dict) -> dict`
- `async def _persist_proposed_actions_v2(execution_id, analysis: dict) -> None`
- `def _is_v2(execution: dict) -> bool` (use_v2_sales_path(trigger_context.domain)에 위임)
- 측정 래퍼는 **여기 산다**(레거시 elayer_dispatch.py 에 추가 금지): `async def _capture_baseline(execution_id) -> dict`, `async def _measure(execution_id) -> dict` — `app.api.routes.atomic_engine.capture_kpi_baseline(KpiBaselineIn(...))`/`measure_kpi(MeasureKpiIn(...))`를 **모듈 속성**으로 lazy-import & call, soft-fail to `{ok:False,error}`.

**hermes**
- `run_hermes_analysis(agenda, *, role='ANALYST', dept='sales') -> dict` (keyword-only; 파라미터는 **dept** — NOT domain)
- `build_analysis_prompt(agenda, *, role='ANALYST') -> str`
- 오케스트레이터는 `run_hermes_analysis(agenda, role='ANALYST', dept='sales')`로 호출하고 **반드시 `asyncio.to_thread`로 오프로드**(blocking SSH).

**analysis gate**
- `validate_analysis(obj, agenda) -> (bool, list[str])` — ⑤trivial 강화(S2).

**safe tools (NEW `app/services/safe_tools.py`)**
- `async def run_tool(tool_tag, params, ctx) -> dict` → `{tool, status('executed'|'skipped_idempotent'), idempotency_key, audit_entity_id, result}`
- `REGISTRY` (`record_decision` + `create_task`), `get_tool`, `UnknownToolError`, `ToolParamError`, `SafeTool` dataclass
- `audit_log`에 query-guard 멱등 write. 오케스트레이터는 status in ('executed','skipped_idempotent')를 성공으로 본다.

**report gate (NEW `app/services/report_gate.py`)**
- `validate_report(report: dict, agenda: dict) -> (bool, list[str])`, `report_numbers(report)`, `REPORT_REQUIRED_KEYS`
- 두 곳에서 호출: (1) 오케스트레이터 resume의 synthesized_report 기록 직전, (2) `send_execution_report` EP의 발송 직전.

**approve (`app/api/routes/strategy.py`)**
- `ApproveIn.selected_actions: Optional[list[str]] = None`
- v2 분기(settings.ELAYER_PIPELINE_V2_SALES_ENABLED AND selected_actions is not None), 409 진단중 가드 **뒤** · 레거시 selected_kinds 로직 **앞**에 배치, early-return: proposed_actions_v2 에 대해 id 검증 → `await resume_after_approval_v2(execution_id, selected_action_ids)` → `_write_audit('approve_actions',...)`. 레거시 경로(selected_actions is None)는 **불변**. resume 는 분기 내부 lazy-import.

**run-v2 EP**
- `POST /api/strategy/executions/{execution_id}/run-v2` → `await run_analysis_v2(execution_id)` (ANALYZE only; 승인은 approve EP가 resume 트리거). 멱등 가드, 플래그 OFF → `{status:'v2_disabled'}`, 404 missing. **SYNC await — NO Celery.**

**DB (NEW migration `migrations/013_pipeline_v2.sql`)**
- `ALTER TABLE strategy_executions ADD COLUMN IF NOT EXISTS proposed_actions_v2 jsonb; ADD COLUMN IF NOT EXISTS ceo_plan_v2 jsonb;`
- Plan task = SQL 파일 write+commit **만**. prod Supabase 적용은 GLEN 의 배포 단계(MCP 적용 금지).

**영속 매핑**
- analysis.proposed_actions 배열 → `proposed_actions_v2` 컬럼
- summary items → `ceo_plan_v2`
- report draft → 기존 `synthesized_report`
- action id = proposed_actions_v2 의 index-as-string ("0".."n"); selected_action_ids = 그 문자열들.

**FE**
- NEW `src/pages/atomic/v2View.ts` (`isV2Execution`, `toToolActions`, `buildSelectedActions`, interface `ToolActionView`) + `v2View.test.ts`
- `src/api/types.ts` : `ProposedActionV2` + `proposed_actions_v2?: ProposedActionV2[] | null` on exec record
- `src/api/client.ts` : `approve({...selected_actions?:string[]})` + `runV2(id)`
- `ExecutionDetailModal.tsx` : v2 분기 ToolActionPanel(CEO/슬롯 어휘 없음) + 낙관 전이
- FE 필드명 = `proposed_actions_v2` 전역(드래프트의 `proposed_actions`는 RENAME). `isV2Execution`는 `proposed_actions_v2` 비어있지 않음 AND `ceo_plan` 부재로 판별.

---

## File Structure

| 파일 | 동작 | repo | Task |
|---|---|---|---|
| `migrations/013_pipeline_v2.sql` | Create | FastAPI | 1 |
| `app/core/config.py` | Modify (플래그) | FastAPI | 2 |
| `app/services/elayer_routing.py` | Modify (use_v2_sales_path) | FastAPI | 2 |
| `tests/test_v2_routing.py` | Create | FastAPI | 2 |
| `app/tasks/detection_tasks.py` | Modify (evidence·confidence) | FastAPI | 3 |
| `tests/test_detection_evidence.py` | Create | FastAPI | 3 |
| `app/services/hermes_prompt.py` | Modify (role 파라미터) | FastAPI | 4 |
| `tests/test_hermes_prompt.py` | Modify | FastAPI | 4 |
| `app/services/hermes_runner.py` | Modify (role/dept 파라미터) | FastAPI | 4 |
| `tests/test_hermes_runner.py` | Modify | FastAPI | 4 |
| `app/services/analysis_gate.py` | Modify (⑤trivial 강화) | FastAPI | 5 |
| `tests/test_analysis_gate.py` | Modify | FastAPI | 5 |
| `app/services/safe_tools.py` | Create | FastAPI | 6 |
| `tests/test_safe_tools.py` | Create | FastAPI | 6 |
| `app/services/report_gate.py` | Create | FastAPI | 7 |
| `tests/test_report_gate.py` | Create | FastAPI | 7 |
| `app/services/elayer_pipeline_v2.py` | Create (run_analysis_v2 + 헬퍼 + 측정 래퍼) | FastAPI | 8 |
| `tests/test_pipeline_v2.py` | Create | FastAPI | 8 |
| `app/services/elayer_pipeline_v2.py` | Modify (resume_after_approval_v2) | FastAPI | 9 |
| `tests/test_pipeline_v2.py` | Modify | FastAPI | 9 |
| `app/api/routes/strategy.py` | Modify (run-v2 EP + feed select) | FastAPI | 10 |
| `tests/test_run_v2_ep.py` | Create | FastAPI | 10 |
| `app/api/routes/strategy.py` | Modify (ApproveIn + v2 분기) | FastAPI | 11 |
| `tests/test_approve_actions.py` | Create | FastAPI | 11 |
| `app/api/routes/strategy.py` | Modify (send EP 게이트) | FastAPI | 12 |
| `tests/test_send_report_gate.py` | Create | FastAPI | 12 |
| `src/pages/atomic/v2View.ts` | Create | hbs | 13 |
| `src/pages/atomic/v2View.test.ts` | Create | hbs | 13 |
| `src/api/types.ts` | Modify (ProposedActionV2) | hbs | 13,14 |
| `src/api/client.ts` | Modify (approve·runV2) | hbs | 14 |
| `src/pages/atomic/ExecutionDetailModal.tsx` | Modify (ToolActionPanel) | hbs | 15 |
| `src/pages/atomic/AtomicConsole.tsx` | Modify (v2 필드 전달) | hbs | 15 |

> **repo 규칙**: FastAPI 라이브 repo = `~/FastAPI` (커밋·테스트 모두 여기). 스냅샷 `~/fastapi-prod-snap-pipeline`·`~/hbs-prod-snap-pipeline`은 읽기전용 참조용. hbs 라이브 repo = `~/hbs-dashboard`. 일부 드래프트가 스냅샷 경로(`cd ~/fastapi-prod-snap-pipeline`)로 테스트를 돌리는데, 본 plan에선 전부 라이브 repo(`cd ~/FastAPI`)에서 실행·커밋한다.

---

## Task 1: DB 마이그레이션 SQL 파일 (proposed_actions_v2, ceo_plan_v2)

**Files:**
- Create: `FastAPI/migrations/013_pipeline_v2.sql`

> repo: **FastAPI** (`~/FastAPI`). 기존 마이그레이션 번호는 012까지 → 013. 이 Task 는 SQL 파일을 **작성·커밋만** 한다. **prod Supabase 적용은 GLEN 의 배포 단계** — Supabase MCP(`apply_migration`/`execute_sql`)로 적용하지 말 것. glen 이 직접 적용한다.

- [ ] (작성) `FastAPI/migrations/013_pipeline_v2.sql` 신규 — 기존 마이그레이션 헤더 주석 스타일 미러:
```sql
-- 013_pipeline_v2.sql
-- Phase 2 매출 수직 슬라이스: v2 단일경로(CEO/슬롯/Paperclip 없음) 영속 컬럼.
-- proposed_actions_v2: Hermes 단일역할 분석의 proposed_actions 배열 전체(도구액션 승인 단위).
-- ceo_plan_v2: 승인 UI용 액션 요약(items)+diagnosis+confidence. (이름은 FE 호환을 위한 것이지 CEO 합성과 무관.)
-- 옛 ceo_plan/ai_recommendation 컬럼은 불변(공존). 적용 = glen 배포 단계(MCP 적용 금지).
ALTER TABLE strategy_executions ADD COLUMN IF NOT EXISTS proposed_actions_v2 jsonb;
ALTER TABLE strategy_executions ADD COLUMN IF NOT EXISTS ceo_plan_v2 jsonb;
```
- [ ] (적용은 glen) 이 Task 는 SQL 파일 생성·커밋까지만. 실제 ALTER 는 글렌이 prod Supabase에 수동 적용한다(에이전트는 MCP로 DB를 건드리지 않음). 테스트는 monkeypatch DB라 컬럼 미적용이어도 GREEN.
- [ ] (COMMIT) `cd ~/FastAPI && git add migrations/013_pipeline_v2.sql && git commit -m "feat(pipeline-v2): migration 013 — strategy_executions.proposed_actions_v2/ceo_plan_v2 (apply: glen)"`

---

## Task 2: 플래그 (config) + use_v2_sales_path 라우팅 헬퍼

**Files:**
- Modify: `FastAPI/app/core/config.py`
- Modify: `FastAPI/app/services/elayer_routing.py`
- Create/Test: `FastAPI/tests/test_v2_routing.py`

> repo: **FastAPI** (`~/FastAPI`).

- [ ] (RED) `FastAPI/tests/test_v2_routing.py` 신규 — 플래그 기본값 + 라우팅 헬퍼. `test_hermes_dispatch.py`의 `settings_obj` 주입 패턴 미러:
```python
from app.services.elayer_routing import use_v2_sales_path


class _V2On:
    ELAYER_PIPELINE_V2_SALES_ENABLED = True


class _V2Off:
    ELAYER_PIPELINE_V2_SALES_ENABLED = False


def test_flag_default_is_false():
    from app.core.config import Settings
    # 신규 인스턴스의 기본값 — env 미설정 시 False (무중립 배포 불변식)
    assert Settings().ELAYER_PIPELINE_V2_SALES_ENABLED is False


def test_v2_path_on_for_sales_when_flag_on():
    assert use_v2_sales_path("sales", _V2On()) is True
    assert use_v2_sales_path(None, _V2On()) is True   # domain 미지정 = sales 취급


def test_v2_path_off_when_flag_off():
    assert use_v2_sales_path("sales", _V2Off()) is False


def test_v2_path_off_for_non_sales_domain():
    assert use_v2_sales_path("review", _V2On()) is False
    assert use_v2_sales_path("cost-util", _V2On()) is False


def test_v2_path_uses_runtime_settings_when_not_injected(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    from app.services.elayer_routing import use_v2_sales_path
    assert use_v2_sales_path("sales") is True
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", False)
    assert use_v2_sales_path("sales") is False
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_v2_routing.py -q` → **FAIL** (ELAYER_PIPELINE_V2_SALES_ENABLED 속성 없음 / use_v2_sales_path ImportError).
- [ ] (GREEN) `app/core/config.py` ELAYER_* 플래그 군집(현 `ELAYER_HERMES_DIAGNOSE_ENABLED` 인근)에 한 줄 추가 — 기존 한 줄 속성 패턴 정확히 미러:
```python
    ELAYER_PIPELINE_V2_SALES_ENABLED: bool = False  # Phase2: sales 도메인을 v2 단일경로로(CEO 게이트/트리아지/팬아웃 스킵). Off=레거시 불변(무중립). 검증 후 on. 신규 env 없음(HERMES_VPS_*·ATOMOS_MCP_* 재사용).
```
- [ ] (GREEN) `app/services/elayer_routing.py`에 헬퍼 추가 — `has_diagnose_slots` 바로 아래, `resolve_dispatch`의 settings 지연 import·domain 정규화 패턴 미러:
```python
def use_v2_sales_path(domain: Optional[str], settings_obj=None) -> bool:
    """이 execution을 Phase2 v2 단일경로로 라우팅할지.
    조건: 플래그 ON AND 도메인이 sales(미지정=sales 취급). OFF면 레거시(CEO/팬아웃) 불변.
    settings_obj 미주입 시 런타임 실 settings 지연 import(resolve_dispatch 패턴)."""
    if settings_obj is None:
        from app.core.config import settings as settings_obj
    if not getattr(settings_obj, "ELAYER_PIPELINE_V2_SALES_ENABLED", False):
        return False
    return (domain or "sales") == "sales"
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_v2_routing.py -q` → **PASS** (5개).
- [ ] (회귀) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_hermes_dispatch.py -q` → 레거시 라우팅 불변 PASS(`_DOMAIN_SLOTS`·resolve_dispatch 미변경).
- [ ] (COMMIT) `cd ~/FastAPI && git add app/core/config.py app/services/elayer_routing.py tests/test_v2_routing.py && git commit -m "feat(pipeline-v2): ELAYER_PIPELINE_V2_SALES_ENABLED flag + use_v2_sales_path routing helper"`

---

## Task 3: 감지 evidence 충실도 보존 + _sales_confidence_score

**Files:**
- Modify: `FastAPI/app/tasks/detection_tasks.py`
- Create/Test: `FastAPI/tests/test_detection_evidence.py`

> repo: **FastAPI** (`~/FastAPI`). RPC `confidence`는 numeric 이 아니라 문자열 라벨('low'/'normal'). 다운스트림(strategy.py)이 `float(...)`로 소비하므로 numeric 점수로 매핑. low→0.5(히스토리 부족=z null), normal→0.8(robust-z 산출), 미지/None→0.5(보수적). 0.7 고정 금지.

- [ ] (RED) `FastAPI/tests/test_detection_evidence.py` 신규 — 매핑 헬퍼 + evidence 충실도:
```python
from app.tasks.detection_tasks import _sales_confidence_score, build_sales_proposal_record


def test_confidence_score_normal():
    # RPC: z 산출됨 → 'normal' → 0.8
    assert _sales_confidence_score("normal") == 0.8


def test_confidence_score_low():
    # RPC: z IS NULL(히스토리 부족) → 'low' → 0.5
    assert _sales_confidence_score("low") == 0.5


def test_confidence_score_unknown_falls_back_low():
    assert _sales_confidence_score(None) == 0.5
    assert _sales_confidence_score("weird") == 0.5


def test_confidence_score_is_float_not_label():
    # 다운스트림 strategy.py 가 float(...) 로 소비 — numeric 보장
    v = _sales_confidence_score("normal")
    assert isinstance(v, float)


def _rpc_store():
    # detect_store_alerts RPC stores[] 항목 실제 모양 (rpc.sql jsonb_build_object 기준)
    return {
        "st_id": "ST-SE-OF-0007",
        "store_name": "청년다방 구로점",
        "br_id": "BR-CN-0003",
        "check_date": "2026-06-18",
        "gross": 1200000,
        "dow": 4,
        "z": -3.4,
        "mu": 2000000,
        "sigma": 235000,
        "n": 8,
        "alert_level": "critical",
        "confidence": "normal",
        "axes": {
            "dod": {"actual": 1200000, "expected": 1800000, "delta_pct": -0.333, "available": True},
            "mom": {"actual": 1200000, "expected": 1900000, "delta_pct": -0.368, "available": True},
        },
        "reasons": {
            "sales_drop_z": -3.4,
            "below_baseline_pct": -0.4,
            "dod_delta_pct": -0.333,
            "mom_delta_pct": -0.368,
        },
    }


def test_evidence_preserves_rpc_fidelity_fields():
    rec = build_sales_proposal_record(_rpc_store(), "2026-06-18")
    ev = rec["trigger_context"]["evidence"]
    # 기존(역호환) 키 보존
    assert ev["z"] == -3.4
    assert ev["gross"] == 1200000
    assert ev["mu"] == 2000000
    assert ev["dod_delta_pct"] == -0.333
    assert ev["mom_delta_pct"] == -0.368
    # 신규 보존 키
    assert ev["sigma"] == 235000
    assert ev["n"] == 8
    assert ev["dow"] == 4
    assert ev["below_baseline_pct"] == -0.4


def test_confidence_derived_from_rpc_not_hardcoded_07():
    rec = build_sales_proposal_record(_rpc_store(), "2026-06-18")
    conf = rec["ai_recommendation"]["confidence"]
    assert conf == 0.8          # 'normal' → 0.8
    assert conf != 0.7          # 옛 하드코딩 제거 증명
    assert isinstance(conf, float)


def test_confidence_low_history_store():
    s = _rpc_store()
    s["confidence"] = "low"
    s["z"] = None              # 히스토리 부족 시 RPC z null
    rec = build_sales_proposal_record(s, "2026-06-18")
    assert rec["ai_recommendation"]["confidence"] == 0.5


def test_below_baseline_pct_null_safe():
    # reasons.below_baseline_pct 가 없는(mu<=0) 경우 None 으로 안전 보존
    s = _rpc_store()
    s["reasons"] = {"sales_drop_z": -3.4}
    rec = build_sales_proposal_record(s, "2026-06-18")
    assert rec["trigger_context"]["evidence"]["below_baseline_pct"] is None
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_detection_evidence.py -q` → **FAIL** (`ImportError: _sales_confidence_score` / `KeyError: 'sigma'` / `assert 0.7 == 0.8`).
- [ ] (GREEN) `app/tasks/detection_tasks.py` `build_sales_proposal_record` 정의 위(파일 상단 import 직후)에 헬퍼 추가:
```python
# RPC(detect_store_alerts) confidence 라벨 → ai_recommendation 점수.
# RPC 의 confidence 는 문자열('low'=z IS NULL 히스토리부족 / 'normal'=robust-z 산출)이며
# 다운스트림(strategy.py)은 float 로 소비 → numeric 매핑. 0.7 고정(옛 하드코딩) 폐기.
_SALES_CONFIDENCE_SCORE = {"low": 0.5, "normal": 0.8}


def _sales_confidence_score(rpc_label: str | None) -> float:
    return _SALES_CONFIDENCE_SCORE.get(rpc_label, 0.5)
```
- [ ] (GREEN) `build_sales_proposal_record` 수정 — `ai_recommendation.confidence` 와 `evidence` 두 곳(전부 additive, 옛 키 z/dod_delta_pct/mom_delta_pct/gross/mu 보존):
  - `ai_recommendation` 블록의 `"confidence": 0.7,` 를 `"confidence": _sales_confidence_score(store.get("confidence")),` 로 교체.
  - `evidence` 블록에 신규 키 추가(기존 키 유지):
```python
            "evidence": {
                "z": store.get("z"),
                "dod_delta_pct": dod,
                "mom_delta_pct": mom,
                "gross": store.get("gross"),
                "mu": store.get("mu"),
                # S1: RPC 산출 충실도 보존 (옛 None 드롭 제거)
                "sigma": store.get("sigma"),
                "n": store.get("n"),
                "dow": store.get("dow"),
                "below_baseline_pct": (store.get("reasons") or {}).get("below_baseline_pct"),
            },
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_detection_evidence.py -q` → **PASS** (9개).
- [ ] (회귀) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_reject_cooldown.py -q` → cogs/cost/contract/review 빌더·`atomos_bridge.execution_to_alert`(None 하드코딩, Phase3 대상) 무변경 PASS. `git diff --stat` 로 변경 파일이 detection_tasks.py + test_detection_evidence.py 둘뿐인지 확인.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/tasks/detection_tasks.py tests/test_detection_evidence.py && git commit -m "feat(detection): persist RPC sigma/n/dow/below_baseline_pct + derive confidence (S1 evidence fidelity, drop 0.7 hardcode)"`

---

## Task 4: hermes_runner role/dept 파라미터화 (+ build_analysis_prompt role)

**Files:**
- Modify: `FastAPI/app/services/hermes_prompt.py`
- Modify: `FastAPI/tests/test_hermes_prompt.py`
- Modify: `FastAPI/app/services/hermes_runner.py`
- Modify: `FastAPI/tests/test_hermes_runner.py`

> repo: **FastAPI** (`~/FastAPI`). **순서**: `build_analysis_prompt` role 파라미터를 **먼저**, 그다음 `run_hermes_analysis` role/dept. 현재 `run_hermes_analysis(agenda)`는 `_mint_token_for` 안에 role='ANALYST'·dept='sales' 하드코딩. **canonical: 파라미터는 `dept`(NOT domain).** 스키마/그라운딩/재시도/AnalysisFailed/_knowledge_calls delta 검증은 전부 불변.

### 4a — build_analysis_prompt role 파라미터화

- [ ] (RED) `FastAPI/tests/test_hermes_prompt.py`에 추가:
```python
def test_prompt_role_parameterized():
    p = build_analysis_prompt(AGENDA, role="SCM")
    assert "SCM" in p          # 역할 라벨 반영
    assert "knowledge_search" in p   # 도구 절차는 불변


def test_prompt_default_role_analyst():
    p = build_analysis_prompt(AGENDA)  # 무인자 = 기존 동작
    assert "ANALYST" in p
    assert "-3.4" in p
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_hermes_prompt.py -q` → 신규 2 FAIL(role 인자 미수용 TypeError).
- [ ] (GREEN) `app/services/hermes_prompt.py` — 시그니처에 keyword-only role 추가, 헤더 역할 라벨만 치환(도메인 절차·_SCHEMA·도구목록 불변):
```python
def build_analysis_prompt(agenda: dict, *, role: str = "ANALYST") -> str:
    tc = agenda.get("trigger_context") or {}
    ev = tc.get("evidence") or {}
    ev_lines = "\n".join(f"  - {k} = {v}" for k, v in ev.items() if v is not None)
    schema = json.dumps(_SCHEMA, ensure_ascii=False, indent=2)
    return f"""당신은 HBS 본사의 매출 분석가({role})입니다. 한 매장의 매출 급락 안건을 진단하고 안전한 대응 액션을 제안합니다.
...  # 이하 본문 불변(기존 f-string 내용 그대로 유지)
"""
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_hermes_prompt.py -q` → **PASS** (기존 3 + 신규 2).
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/hermes_prompt.py tests/test_hermes_prompt.py && git commit -m "feat(pipeline-v2): parameterize role label in build_analysis_prompt (default ANALYST)"`

### 4b — run_hermes_analysis role/dept 파라미터화

- [ ] (RED) `FastAPI/tests/test_hermes_runner.py`에 role/dept 전파 + 하위호환 추가:
```python
def test_run_passes_role_dept_to_token(monkeypatch):
    captured = {}
    def fake_mint(agenda, role, dept):
        captured["role"], captured["dept"] = role, dept
        return "tok"
    monkeypatch.setattr(hermes_runner, "_ssh_run_hermes", lambda p, t: VALID_JSON)
    monkeypatch.setattr(hermes_runner, "_mint_token_for", fake_mint)
    monkeypatch.setattr(hermes_runner, "_knowledge_calls", _kc(0, 1))
    run_hermes_analysis(AGENDA, role="SCM", dept="cogs")
    assert captured == {"role": "SCM", "dept": "cogs"}


def test_run_defaults_backward_compatible(monkeypatch):
    # 무인자 호출(레거시 caller)은 ANALYST/sales 기본값으로 동작
    captured = {}
    monkeypatch.setattr(hermes_runner, "_ssh_run_hermes", lambda p, t: VALID_JSON)
    monkeypatch.setattr(hermes_runner, "_mint_token_for",
                        lambda agenda, role, dept: captured.update(role=role, dept=dept) or "tok")
    monkeypatch.setattr(hermes_runner, "_knowledge_calls", _kc(0, 1))
    result = run_hermes_analysis(AGENDA)
    assert result["confidence"] == 0.72
    assert captured == {"role": "ANALYST", "dept": "sales"}
```
  **GOTCHA(필수):** 기존 테스트들은 `_mint_token_for`를 `lambda agenda: "tok"`(1-인자)로 monkeypatch 중이다. 시그니처를 `(agenda, role, dept)`로 바꾸면 그 패치들이 TypeError로 깨진다. **같은 커밋에서** 기존 patch 람다 전부를 `lambda agenda, role, dept: "tok"`로 일괄 수정한다(test_run_success_first_try·test_run_retries_then_fails·test_run_retry_recovers·test_run_rejects_forged_knowledge 등).
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_hermes_runner.py -q` → 신규 2 FAIL(role/dept 인자 미수용 TypeError).
- [ ] (GREEN) `app/services/hermes_runner.py` — `_mint_token_for`에 role/dept 인자, `run_hermes_analysis`에 keyword-only role/dept 추가(`build_analysis_prompt(agenda, role=role)` 호출은 4a 머지 후 유효):
```python
def _mint_token_for(agenda: dict, role: str, dept: str) -> str:
    tc = agenda.get("trigger_context") or {}
    return mint_session_token(
        execution_id=str(agenda.get("execution_id") or ""),
        store_id=str(tc.get("st_id") or ""),
        brand_id=str(agenda.get("br_uid") or ""),
        dept=dept,
        role=role,
        ttl_sec=settings.ATOMOS_MCP_SESSION_TTL_SEC,
        secret=settings.ATOMOS_MCP_SESSION_SECRET,
    )


def run_hermes_analysis(agenda: dict, *, role: str = "ANALYST", dept: str = "sales") -> dict:
    exec_id = str(agenda.get("execution_id") or "")
    token = _mint_token_for(agenda, role, dept)
    base_prompt = build_analysis_prompt(agenda, role=role)
    ...  # 이하 재시도 루프/검증 불변
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_hermes_runner.py -q` → **PASS** (기존 + 신규 2).
- [ ] (회귀) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_hermes_dispatch.py tests/test_mcp_server_app.py -q` → 레거시 caller(elayer_dispatch·poc 무인자 호출) 불변 PASS.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/hermes_runner.py tests/test_hermes_runner.py && git commit -m "feat(pipeline-v2): parameterize role/dept in run_hermes_analysis (default ANALYST/sales)"`

---

## Task 5: analysis_gate ⑤ trivial-rejection 강화

**Files:**
- Modify: `FastAPI/app/services/analysis_gate.py`
- Modify: `FastAPI/tests/test_analysis_gate.py`

> repo: **FastAPI** (`~/FastAPI`). 현 ⑤는 `diagnosis len(strip)>=20` 단일 체크뿐 → "전반적으로 매출이 감소한 것으로 보입니다 추가 분석 필요"(20자 넘는 일반론)가 통과한다. (a) placeholder/일반론 거부 + (b) proposed_actions 각 액션의 what/how 실질성 검사로 강화. ①스키마·③그라운딩·tool_tag·confidence 불변. (②수치재계산·④환각 실값대조는 범위 외 fast-follow.)

- [ ] (RED) `FastAPI/tests/test_analysis_gate.py`에 추가:
```python
def test_placeholder_diagnosis_rejected():
    # 20자 넘지만 수치근거 없는 일반론/플레이스홀더 → 거부
    bad = dict(GOOD, diagnosis="전반적으로 매출이 감소한 것으로 보이며 추가 분석이 필요합니다 TODO",
               evidence_cited=["z=-3.4"])
    ok, reasons = validate_analysis(bad, AGENDA)
    assert not ok
    assert any(("trivial" in r) or ("substance" in r) for r in reasons)


def test_trivial_action_rejected():
    # 액션 키는 다 있으나 what/how가 placeholder → 거부
    bad = dict(GOOD, proposed_actions=[dict(GOOD["proposed_actions"][0], what="TODO", how="N/A")])
    ok, reasons = validate_analysis(bad, AGENDA)
    assert not ok
    assert any(("trivial" in r) or ("substance" in r) for r in reasons)


def test_good_output_still_passes_after_hardening():
    ok, reasons = validate_analysis(GOOD, AGENDA)
    assert ok, reasons   # 회귀: 정상 출력은 여전히 통과
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_analysis_gate.py -q` → 신규 거부 2 FAIL(현 게이트가 placeholder·trivial action 통과). `test_good_output_still_passes_after_hardening`는 현재도 통과(가드).
- [ ] (GREEN) `app/services/analysis_gate.py`에 헬퍼 + 체크 추가:
```python
_PLACEHOLDER_PHRASES = ("todo", "tbd", "n/a", "없음", "추후", "해당 없음", "placeholder", "...", "추가 분석 필요")


def _is_trivial_text(s: str, min_len: int = 8) -> bool:
    """실질 없는 텍스트 판별: 공백제거 길이 부족 or placeholder 문구 지배적."""
    t = (s or "").strip()
    if len(t) < min_len:
        return True
    low = t.lower()
    return any(p in low for p in _PLACEHOLDER_PHRASES)
```
  `validate_analysis` 안, 기존 diagnosis len>=20 체크 직후에:
```python
    # ⑤ trivial 강화: diagnosis 일반론/placeholder 거부
    if isinstance(diagnosis, str) and len(diagnosis.strip()) >= 20 and _is_trivial_text(diagnosis, min_len=20):
        reasons.append("substance: diagnosis is trivial/placeholder (일반론·내용없음)")
```
  그리고 proposed_actions 루프 안, ACTION_KEYS 통과·tool_tag 검사 곁에:
```python
            if _is_trivial_text(str(a.get("what"))) or _is_trivial_text(str(a.get("how"))):
                reasons.append(f"substance: action[{i}] what/how is trivial/placeholder")
```
  주의: GOOD 의 diagnosis 는 수치 포함 실질 문장이라 placeholder 미매칭(회귀 가드). `_PLACEHOLDER_PHRASES`는 흔한 한국어 일반론을 좁게 한정해 정상 출력 오탐 방지.
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_analysis_gate.py -q` → **PASS** (기존 6 + 신규 3).
- [ ] (회귀) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_hermes_runner.py tests/test_hermes_prompt.py -q` → run_hermes_analysis 가 VALID_JSON(수치 실질 diagnosis)을 여전히 통과시키는지 확인.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/analysis_gate.py tests/test_analysis_gate.py && git commit -m "feat(pipeline-v2): strengthen analysis_gate rule (5) — reject trivial/placeholder diagnosis+actions"`

---

## Task 6: safe_tools 레지스트리 + record_decision + create_task

**Files:**
- Create: `FastAPI/app/services/safe_tools.py`
- Create/Test: `FastAPI/tests/test_safe_tools.py`

> repo: **FastAPI** (`~/FastAPI`). 신규 leaf 모듈 — 내부 DB write·가역·멱등·매장 스코프·외부발송 0. 1차 2도구: record_decision·create_task. 둘 다 audit_log 재사용(신규 테이블 0). S4.md 본문이 이 모듈의 canonical. 세 서브태스크를 한 흐름으로 진행(레지스트리 골격 → record_decision executor → create_task executor).

### 6a — 레지스트리 골격 + 조회/미등록 거부

- [ ] (RED) `FastAPI/tests/test_safe_tools.py` 신규:
```python
import asyncio
import pytest
from app.services import safe_tools
from app.services.safe_tools import get_tool, run_tool, UnknownToolError, ToolParamError, SafeTool, REGISTRY


def test_registry_has_two_tools():
    assert set(REGISTRY.keys()) == {"record_decision", "create_task"}


def test_registry_safety_attrs():
    for tag in ("record_decision", "create_task"):
        t = get_tool(tag)
        assert isinstance(t, SafeTool)
        assert t.reversible and t.idempotent and t.scoped  # 내부 DB·가역·멱등·스코프


def test_get_tool_unknown_raises():
    with pytest.raises(UnknownToolError):
        get_tool("delete_store")


def test_run_tool_unknown_rejected():
    with pytest.raises(UnknownToolError):
        asyncio.run(run_tool("notify", {}, {"execution_id": "e1", "st_uid": "ST-1"}))
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_safe_tools.py -q` → ImportError(safe_tools 없음)로 FAIL.
- [ ] (GREEN) `FastAPI/app/services/safe_tools.py` 신규:
```python
"""안전도구 레지스트리(Phase 2 S4). 내부 DB write·가역·멱등·매장 스코프·외부발송 0.
1차 2도구: record_decision · create_task. 둘 다 audit_log 재사용(신규 테이블 0)."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.api.routes.cost import _query, _upsert  # cost.py 는 app 무의존 → 순환 import 없음


class UnknownToolError(Exception): ...
class ToolParamError(Exception): ...


Executor = Callable[[dict, dict], Awaitable[dict]]


@dataclass(frozen=True)
class SafeTool:
    id: str
    required_params: tuple[str, ...]
    reversible: bool
    idempotent: bool
    scoped: bool
    executor: Executor


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_tool(tool_tag: str) -> SafeTool:
    t = REGISTRY.get(tool_tag)
    if t is None:
        raise UnknownToolError(f"미등록 안전도구: {tool_tag!r}")
    return t


# executors 는 6b/6c 에서 채움 — 골격에선 실 함수로 정의(placeholder 금지)
async def _exec_record_decision(params: dict, ctx: dict) -> dict: ...   # 6b
async def _exec_create_task(params: dict, ctx: dict) -> dict: ...       # 6c


REGISTRY: dict[str, SafeTool] = {
    "record_decision": SafeTool("record_decision", ("verdict", "note", "scope"), True, True, True, _exec_record_decision),
    "create_task":     SafeTool("create_task",     ("owner", "action", "due"),  True, True, True, _exec_create_task),
}


def _idempotency_key(tool_tag: str, params: dict, ctx: dict) -> str:
    if ctx.get("idempotency_key"):
        return str(ctx["idempotency_key"])
    basis = "|".join([tool_tag, str(ctx.get("execution_id", "")), str(ctx.get("st_uid", "")),
                      json.dumps(params, sort_keys=True, ensure_ascii=False)])
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


async def run_tool(tool_tag: str, params: dict, ctx: dict) -> dict:
    tool = get_tool(tool_tag)  # 미등록 → UnknownToolError
    missing = [k for k in tool.required_params if k not in params]
    if missing:
        raise ToolParamError(f"{tool_tag}: 필수 params 누락 {missing}")
    if tool.scoped and not ctx.get("st_uid"):
        raise ToolParamError(f"{tool_tag}: 매장 스코프(ctx.st_uid) 필수")
    idem = _idempotency_key(tool_tag, params, ctx)
    ctx = {**ctx, "_idem": idem}
    return await tool.executor(params, ctx)
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_safe_tools.py -q` → green(4건). executor 호출 테스트는 아직 없음.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/safe_tools.py tests/test_safe_tools.py && git commit -m "feat(safe-tools): registry skeleton + run_tool dispatch + unknown-tool rejection (Phase2 S4)"`

### 6b — record_decision executor (audit_log 재사용·멱등·스코프)

- [ ] (RED) `FastAPI/tests/test_safe_tools.py`에 추가(cost.py 헬퍼는 safe_tools 모듈명에 setattr):
```python
def _fake_db():
    """_query/_upsert 모의. upserts 리스트에 기록, _query 는 등록된 응답 반환."""
    state = {"upserts": [], "query_returns": []}
    async def fake_query(table, params=None):
        state["upserts"].append(("query", table, params))
        return state["query_returns"].pop(0) if state["query_returns"] else []
    async def fake_upsert(table, data, on_conflict=None):
        row = data[0] if isinstance(data, list) else data
        state["upserts"].append(("upsert", table, row))
        return [{**row, "id": 123}]
    return state, fake_query, fake_upsert


def test_record_decision_writes_audit(monkeypatch):
    state, fq, fu = _fake_db()
    monkeypatch.setattr(safe_tools, "_query", fq)
    monkeypatch.setattr(safe_tools, "_upsert", fu)
    out = asyncio.run(run_tool("record_decision",
        {"verdict": "approve", "note": "강남점 급락 대응 승인", "scope": "ST-1"},
        {"execution_id": "e1", "st_uid": "ST-1"}))
    assert out["status"] == "executed"
    up = [u for u in state["upserts"] if u[0] == "upsert"]
    assert up and up[0][1] == "audit_log"
    row = up[0][2]
    assert row["action_type"] == "record_decision"
    assert row["entity_type"] == "strategy_execution" and row["entity_id"] == "e1"
    assert row["decision_type"] == "approve"
    assert row["metadata"]["idempotency_key"] == out["idempotency_key"]
    assert row["metadata"]["st_uid"] == "ST-1"


def test_record_decision_idempotent_skips(monkeypatch):
    state, fq, fu = _fake_db()
    state["query_returns"] = [[{"id": 99}]]  # 기존 row 존재 → 멱등 스킵
    monkeypatch.setattr(safe_tools, "_query", fq)
    monkeypatch.setattr(safe_tools, "_upsert", fu)
    out = asyncio.run(run_tool("record_decision",
        {"verdict": "approve", "note": "n", "scope": "ST-1"},
        {"execution_id": "e1", "st_uid": "ST-1"}))
    assert out["status"] == "skipped_idempotent"
    assert not [u for u in state["upserts"] if u[0] == "upsert"]  # 재기록 없음(가역·멱등)


def test_record_decision_requires_scope(monkeypatch):
    monkeypatch.setattr(safe_tools, "_query", lambda *a, **k: (_ for _ in ()).throw(AssertionError("불호출")))
    with pytest.raises(ToolParamError):
        asyncio.run(run_tool("record_decision", {"verdict": "v", "note": "n", "scope": "s"},
                             {"execution_id": "e1"}))  # st_uid 없음
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_safe_tools.py -k record_decision -q` → executor 가 `...`(None 반환)이라 FAIL.
- [ ] (GREEN) `_exec_record_decision` 본문 + 멱등 query-guard 헬퍼 채움:
```python
async def _find_existing(tool_tag: str, idem: str) -> bool:
    """audit_log 에 동일 멱등키 row 가 이미 있는지(query-guard 멱등; audit_log 엔 unique 제약 없음)."""
    rows = await _query("audit_log", {
        "select": "id",
        "action_type": f"eq.{tool_tag}",
        "metadata->>idempotency_key": f"eq.{idem}",
        "limit": "1",
    })
    return bool(rows)


async def _exec_record_decision(params: dict, ctx: dict) -> dict:
    idem = ctx["_idem"]
    eid = str(ctx.get("execution_id") or "")
    st_uid = str(ctx["st_uid"])
    if await _find_existing("record_decision", idem):
        return {"tool": "record_decision", "status": "skipped_idempotent",
                "idempotency_key": idem, "audit_entity_id": eid, "result": {}}
    row = {
        "action_type": "record_decision",
        "entity_type": "strategy_execution",
        "entity_id": eid,
        "decision_type": str(params["verdict"]),
        "after_data": {"verdict": params["verdict"], "note": params["note"], "scope": params["scope"]},
        "metadata": {"tool": "record_decision", "idempotency_key": idem,
                     "st_uid": st_uid, "source": "safe_tools", "recorded_at": _now_iso()},
    }
    inserted = await _upsert("audit_log", row)
    return {"tool": "record_decision", "status": "executed", "idempotency_key": idem,
            "audit_entity_id": eid, "result": {"audit_id": (inserted[0].get("id") if inserted else None)}}
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_safe_tools.py -k record_decision -q` → green(3건).
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/safe_tools.py tests/test_safe_tools.py && git commit -m "feat(safe-tools): record_decision executor — audit_log write, query-guard idempotent, store-scoped (Phase2 S4)"`

### 6c — create_task executor + 전체 회귀

- [ ] (RED) `FastAPI/tests/test_safe_tools.py`에 추가(6b 의 `_fake_db` 재사용):
```python
def test_create_task_writes_audit(monkeypatch):
    state, fq, fu = _fake_db()
    monkeypatch.setattr(safe_tools, "_query", fq)
    monkeypatch.setattr(safe_tools, "_upsert", fu)
    out = asyncio.run(run_tool("create_task",
        {"owner": "ANALYST", "action": "점주 통화로 급락 원인 확인", "due": "2026-06-30"},
        {"execution_id": "e1", "st_uid": "ST-1"}))
    assert out["status"] == "executed"
    row = [u for u in state["upserts"] if u[0] == "upsert"][0][2]
    assert row["action_type"] == "create_task" and row["entity_id"] == "e1"
    assert row["after_data"]["owner"] == "ANALYST"
    assert row["after_data"]["due"] == "2026-06-30"
    assert row["after_data"]["task_status"] == "open"
    assert row["after_data"]["st_uid"] == "ST-1"
    assert row["metadata"]["idempotency_key"] == out["idempotency_key"]


def test_create_task_idempotent_skips(monkeypatch):
    state, fq, fu = _fake_db()
    state["query_returns"] = [[{"id": 7}]]
    monkeypatch.setattr(safe_tools, "_query", fq)
    monkeypatch.setattr(safe_tools, "_upsert", fu)
    out = asyncio.run(run_tool("create_task",
        {"owner": "ANALYST", "action": "a", "due": None},
        {"execution_id": "e1", "st_uid": "ST-1"}))
    assert out["status"] == "skipped_idempotent"
    assert not [u for u in state["upserts"] if u[0] == "upsert"]


def test_create_task_missing_param_rejected():
    with pytest.raises(ToolParamError):
        asyncio.run(run_tool("create_task", {"owner": "ANALYST", "action": "a"},  # due 누락
                             {"execution_id": "e1", "st_uid": "ST-1"}))
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_safe_tools.py -k create_task -q` → executor 미구현으로 FAIL.
- [ ] (GREEN) `_exec_create_task` 본문 채움:
```python
async def _exec_create_task(params: dict, ctx: dict) -> dict:
    idem = ctx["_idem"]
    eid = str(ctx.get("execution_id") or "")
    st_uid = str(ctx["st_uid"])
    if await _find_existing("create_task", idem):
        return {"tool": "create_task", "status": "skipped_idempotent",
                "idempotency_key": idem, "audit_entity_id": eid, "result": {}}
    row = {
        "action_type": "create_task",
        "entity_type": "strategy_execution",
        "entity_id": eid,
        "after_data": {"owner": params["owner"], "action": params["action"],
                       "due": params["due"], "st_uid": st_uid, "task_status": "open"},
        "metadata": {"tool": "create_task", "idempotency_key": idem,
                     "st_uid": st_uid, "source": "safe_tools", "recorded_at": _now_iso()},
    }
    inserted = await _upsert("audit_log", row)
    return {"tool": "create_task", "status": "executed", "idempotency_key": idem,
            "audit_entity_id": eid, "result": {"audit_id": (inserted[0].get("id") if inserted else None)}}
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_safe_tools.py -q` → 전체 green(6a~6c 합산 10건).
- [ ] (회귀, 옛 경로 불변) `cd ~/FastAPI && venv/bin/python -m pytest tests/ -q` → 기존 전 테스트 통과(safe_tools 는 신규 leaf 모듈, 기존 import 영향 0).
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/safe_tools.py tests/test_safe_tools.py && git commit -m "feat(safe-tools): create_task executor + full suite green; both tools internal/reversible/idempotent/scoped (Phase2 S4)"`

---

## Task 7: report_gate.validate_report (순수 신뢰게이트 모듈)

**Files:**
- Create: `FastAPI/app/services/report_gate.py`
- Create/Test: `FastAPI/tests/test_report_gate.py`

> repo: **FastAPI** (`~/FastAPI`). 순수함수 모듈(부수효과·발송 없음). substance(trivial/placeholder/과도단축 거부) + grounding(report 수치 vs evidence 대조) + schema 완전성. `analysis_gate.validate_analysis`와 동일 `(obj, agenda)->(ok, reasons)` 계약. S6.md 본문이 canonical. 두 서브태스크(schema+substance → grounding)로 진행.

### 7a — substance + schema

- [ ] (RED) `FastAPI/tests/test_report_gate.py` 신규:
```python
from app.services.report_gate import validate_report, report_numbers, REPORT_REQUIRED_KEYS

AGENDA = {
    "title": "[자동감지] 매출 급락 대응: 강남점",
    "trigger_context": {"st_id": "ST-1", "domain": "sales", "evidence": {
        "z": -3.4, "dod_delta_pct": -0.42, "mom_delta_pct": -0.18,
        "gross": 850000, "mu": 1460000}},
}
GOOD = {
    "executive_summary": "강남점 일매출이 같은 요일 대비 z=-3.4로 급락. gross 850000은 평소 mu 1460000 대비 약 42% 낮습니다.",
    "prioritized_actions": [
        {"action": "점주에게 급락 통지", "owner": "ANALYST", "priority": "high", "rationale": "gross 850000 즉시 확인 필요"},
    ],
    "deliverables": [{"slot": "ATOMOS_ANALYST", "kind": "diagnosis", "summary": "z=-3.4 급락 진단"}],
    "store_message": "사장님, 어제 매출이 평소(1460000원) 대비 850000원으로 크게 낮았습니다. 원인 확인을 요청드립니다.",
}


def test_required_keys_constant():
    assert REPORT_REQUIRED_KEYS == {"executive_summary", "prioritized_actions", "deliverables", "store_message"}


def test_good_report_passes():
    ok, reasons = validate_report(GOOD, AGENDA)
    assert ok, reasons


def test_missing_required_key_blocked():
    bad = {k: v for k, v in GOOD.items() if k != "store_message"}
    ok, reasons = validate_report(bad, AGENDA)
    assert not ok and any("schema" in r for r in reasons)


def test_empty_prioritized_actions_blocked():
    bad = dict(GOOD, prioritized_actions=[])
    ok, reasons = validate_report(bad, AGENDA)
    assert not ok and any("schema" in r for r in reasons)


def test_placeholder_summary_blocked():
    bad = dict(GOOD, executive_summary="(자동 합성 미수행 — 원본 산출물 묶음)")
    ok, reasons = validate_report(bad, AGENDA)
    assert not ok and any("substance" in r for r in reasons)


def test_over_short_message_blocked():
    bad = dict(GOOD, store_message="확인", executive_summary="짧음")
    ok, reasons = validate_report(bad, AGENDA)
    assert not ok and any("substance" in r for r in reasons)
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_report_gate.py -q` → `ModuleNotFoundError: app.services.report_gate`.
- [ ] (GREEN) `FastAPI/app/services/report_gate.py` 신규(substance + schema 만; grounding 은 7b). `analysis_gate.py` 스타일 1:1:
```python
"""보고 신뢰게이트(Phase 2 매출 슬라이스) — synthesized_report 발송 적격성 검증.
substance(trivial/placeholder/과도단축 거부) + grounding(report 수치 vs evidence 대조)
+ schema 완전성(SYNTH 필수키). analysis_gate.validate_analysis 와 동일 (report, agenda)->(ok, reasons) 계약.
순수함수 — 부수효과·발송 없음. _fallback(bundle/direct) 리포트도 이 게이트를 통과해야 발송 가능."""
import re

REPORT_REQUIRED_KEYS = {"executive_summary", "prioritized_actions", "deliverables", "store_message"}
# _synthesis_fallback / 빈 리포트 산물에서 나오는 무실질 문구
_PLACEHOLDER_MARKERS = (
    "자동 합성 미수행", "원본 산출물 묶음", "리포트 본문 없음",
    "todo", "tbd", "n/a", "없음",
)
_MIN_SUMMARY_LEN = 20   # analysis_gate diagnosis 기준과 동일
_MIN_MESSAGE_LEN = 20
_NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def evidence_numbers(agenda: dict) -> set[str]:
    """안건 evidence 수치를 문자열 집합으로(analysis_gate.evidence_numbers 미러)."""
    ev = ((agenda.get("trigger_context") or {}).get("evidence") or {})
    out: set[str] = set()
    for v in ev.values():
        if isinstance(v, (int, float)):
            out.add(str(v)); out.add(str(round(float(v), 2)))
    return {s for s in out if s not in ("", "None")}


def report_numbers(report: dict) -> set[str]:
    """리포트 본문 텍스트에서 숫자 토큰 추출(콤마 제거)."""
    parts = [str(report.get("executive_summary") or ""), str(report.get("store_message") or "")]
    for a in (report.get("prioritized_actions") or []):
        if isinstance(a, dict):
            parts += [str(a.get("action") or ""), str(a.get("rationale") or "")]
    hay = " ".join(parts)
    return {m.group(0).replace(",", "") for m in _NUM_RE.finditer(hay)}


def _has_placeholder(text: str) -> bool:
    low = (text or "").strip().lower()
    return any(m in low for m in _PLACEHOLDER_MARKERS)


def validate_report(report: dict, agenda: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not isinstance(report, dict):
        return False, ["schema: not an object"]

    # schema 완전성
    missing = REPORT_REQUIRED_KEYS - set(report.keys())
    if missing:
        reasons.append(f"schema: missing required keys {sorted(missing)}")
    actions = report.get("prioritized_actions")
    if not isinstance(actions, list) or not actions:
        reasons.append("schema: prioritized_actions must be non-empty list")
    deliverables = report.get("deliverables")
    if not isinstance(deliverables, list) or not deliverables:
        reasons.append("schema: deliverables must be non-empty list")

    summary = str(report.get("executive_summary") or "").strip()
    message = str(report.get("store_message") or "").strip()

    # substance: placeholder / 과도단축
    if _has_placeholder(summary) or _has_placeholder(message):
        reasons.append("substance: placeholder/auto-bundle text in report")
    if len(summary) < _MIN_SUMMARY_LEN:
        reasons.append("substance: executive_summary too short")
    # store_message 는 점주 본문 — summary 가 충실하면 message 비어도 build_owner_email 이 summary 폴백.
    # 그러나 둘 다 부실하면 거부.
    if len(summary) < _MIN_SUMMARY_LEN and len(message) < _MIN_MESSAGE_LEN:
        reasons.append("substance: no substantive owner-facing body")

    return (len(reasons) == 0), reasons
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_report_gate.py -q` → 6 passed.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/report_gate.py tests/test_report_gate.py && git commit -m "feat(pipeline-v2): report trust gate — substance+schema (S6)"`

### 7b — grounding 축 + _fallback 거부

- [ ] (RED) `FastAPI/tests/test_report_gate.py` 말미에 추가:
```python
def test_report_numbers_extracts_values():
    nums = report_numbers(GOOD)
    assert "850000" in nums and "1460000" in nums


def test_ungrounded_report_blocked():
    # evidence 수치를 하나도 인용하지 않은 두루뭉술 리포트
    bad = dict(GOOD,
               executive_summary="강남점 매출이 전반적으로 좀 떨어진 것으로 보입니다 확인 바랍니다.",
               store_message="사장님 매출이 평소보다 낮아 보입니다 한번 봐주세요 부탁드립니다.",
               prioritized_actions=[{"action": "상황 점검", "owner": "ANALYST", "priority": "med", "rationale": "추세 확인"}])
    ok, reasons = validate_report(bad, AGENDA)
    assert not ok and any("grounding" in r for r in reasons)


def test_fallback_bundle_report_blocked():
    # _synthesis_fallback 산물(placeholder summary + 빈 store_message) — 게이트가 차단해야 함
    fb = {"executive_summary": "(자동 합성 미수행 — 원본 산출물 묶음)",
          "prioritized_actions": [{"action": "급락 원인 진단", "owner": "ATOMOS_ANALYST", "priority": "med", "rationale": "원본 슬롯 액션"}],
          "deliverables": [{"slot": "ATOMOS_ANALYST", "kind": "output", "summary": "진단"}],
          "store_message": "", "_fallback": "bundle"}
    ok, reasons = validate_report(fb, AGENDA)
    assert not ok
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_report_gate.py -q -k "grounding or fallback or report_numbers"` → `test_ungrounded_report_blocked` FAIL(grounding 미구현).
- [ ] (GREEN) `validate_report` 의 `return` 직전에 grounding 블록 추가:
```python
    # grounding: evidence 수치가 리포트 본문에 최소 1개 인용됐는가
    ev_nums = evidence_numbers(agenda)
    if ev_nums:
        rep_nums = report_numbers(report)
        if not (ev_nums & rep_nums):
            reasons.append("grounding: no evidence number cited in report body")
```
  (evidence 가 비어 있으면 grounding skip — analysis_gate 와 동일하게 evidence 없는 안건엔 강제 안 함.)
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_report_gate.py -q` → 9 passed.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/report_gate.py tests/test_report_gate.py && git commit -m "feat(pipeline-v2): report gate grounding + fallback rejection (S6)"`

---

## Task 8: elayer_pipeline_v2 오케스트레이터 — run_analysis_v2 + 헬퍼 + 측정 래퍼

**Files:**
- Create: `FastAPI/app/services/elayer_pipeline_v2.py`
- Create/Test: `FastAPI/tests/test_pipeline_v2.py`

> repo: **FastAPI** (`~/FastAPI`). 신규 오케스트레이터 모듈. `_is_v2`는 use_v2_sales_path 에 위임. `_build_v2_agenda`·`_persist_proposed_actions_v2`·`run_analysis_v2`(분석→검증→영속→STOP at 'propose_v2'). **측정 래퍼 `_capture_baseline`/`_measure`는 이 모듈에 산다**(레거시 elayer_dispatch.py 에 추가 금지). hermes 호출은 `asyncio.to_thread`로 오프로드, `dept='sales'`(NOT domain). 세 서브태스크.

### 8a — _is_v2 + _build_v2_agenda + 측정 래퍼

- [ ] (RED) `FastAPI/tests/test_pipeline_v2.py` 신규(test_hermes_dispatch.py monkeypatch 이디엄 미러):
```python
import asyncio
from app.services import elayer_pipeline_v2 as v2

_SALES_EXEC = {"execution_id": "e-v2-1", "title": "[자동감지] 매출 급락 대응: 강남점",
               "br_uid": "BR-1",
               "trigger_context": {"domain": "sales", "st_id": "ST-1", "check_date": "2026-06-19",
                                   "evidence": {"z": -3.4, "gross": 850000, "mu": 1460000}}}
_COGS_EXEC = {"execution_id": "e-c", "trigger_context": {"domain": "cogs-ig", "evidence": {}}}


def test_is_v2_requires_flag_and_sales(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    assert v2._is_v2(_SALES_EXEC) is True
    assert v2._is_v2(_COGS_EXEC) is False          # 도메인 sales 아님
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", False)
    assert v2._is_v2(_SALES_EXEC) is False          # 플래그 OFF → 레거시 불변


def test_build_v2_agenda_preserves_evidence():
    a = v2._build_v2_agenda(_SALES_EXEC)
    assert a["execution_id"] == "e-v2-1"
    assert a["br_uid"] == "BR-1"
    assert a["trigger_context"]["evidence"]["z"] == -3.4   # 충실도 보존(S1)
    assert a["trigger_context"]["evidence"]["gross"] == 850000


class _Snap:  # KpiSnapshotResult 스텁(속성 접근만 필요)
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_capture_baseline_forwards_execution_id_and_unwraps(monkeypatch):
    import app.api.routes.atomic_engine as ae
    rec = {}
    async def _fake(body):
        rec["body"] = body
        return _Snap(message="ok", snapshot_id=11, snapshot_type="baseline",
                     created=True, kpi_data={"revenue": 1000})
    monkeypatch.setattr(ae, "capture_kpi_baseline", _fake)
    out = asyncio.run(v2._capture_baseline("e-1"))
    assert rec["body"].execution_id == "e-1"
    assert out == {"ok": True, "snapshot_id": 11, "snapshot_type": "baseline",
                   "created": True, "kpi_data": {"revenue": 1000}}


def test_measure_unwraps_verdict_and_comparison(monkeypatch):
    import app.api.routes.atomic_engine as ae
    async def _fake(body):
        return _Snap(message="ok", snapshot_id=22, snapshot_type="final", created=True,
                     kpi_data={"revenue": 1100},
                     comparison_data={"revenue_delta_pct": 10.0},
                     verdict_suggested="achieved")
    monkeypatch.setattr(ae, "measure_kpi", _fake)
    out = asyncio.run(v2._measure("e-1"))
    assert out["ok"] is True
    assert out["verdict_suggested"] == "achieved"
    assert out["comparison_data"]["revenue_delta_pct"] == 10.0
    assert out["snapshot_id"] == 22


def test_measure_wrappers_soft_fail(monkeypatch):
    """측정 글리치가 v2 신경로를 깨면 안 됨 → raise 금지, ok=False 반환."""
    import app.api.routes.atomic_engine as ae
    from fastapi import HTTPException
    async def _boom_http(body):
        raise HTTPException(status_code=422, detail="no KPI data")
    async def _boom_generic(body):
        raise RuntimeError("supabase down")
    monkeypatch.setattr(ae, "capture_kpi_baseline", _boom_http)
    monkeypatch.setattr(ae, "measure_kpi", _boom_generic)
    b = asyncio.run(v2._capture_baseline("e-1"))
    m = asyncio.run(v2._measure("e-1"))
    assert b["ok"] is False and "422" in b["error"]
    assert m["ok"] is False and "supabase down" in m["error"]
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_pipeline_v2.py -q` → `ModuleNotFoundError: app.services.elayer_pipeline_v2` / AttributeError.
- [ ] (GREEN) `FastAPI/app/services/elayer_pipeline_v2.py` 신규 — 모듈 docstring + 라우팅/agenda 헬퍼 + 측정 래퍼. 측정 래퍼는 `app.api.routes.atomic_engine`을 **모듈 속성**으로 lazy-import & call(monkeypatch 가 먹으려면 필수), soft-fail:
```python
"""v2 단일역할 매출 파이프라인 오케스트레이터(플래그 뒤). CEO/팬아웃/Paperclip 없음.
진입점①(분석) = run_analysis_v2: evidence→Hermes 단일역할 분석→검증게이트→proposed_actions_v2 영속→승인대기 STOP.
진입점②(실행후) = resume_after_approval_v2: 승인액션 safe_tools 실행→측정→보고 신뢰게이트→synthesized_report draft.
측정 래퍼(_capture_baseline/_measure)는 atomic_engine 재사용·soft-fail(여기 상주; 레거시 elayer_dispatch 미사용)."""
import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.services.elayer_routing import use_v2_sales_path

logger = logging.getLogger(__name__)


def _is_v2(execution: dict) -> bool:
    """이 execution을 v2 경로로 처리할지 — use_v2_sales_path(trigger_context.domain)에 위임."""
    tc = execution.get("trigger_context") or {}
    return use_v2_sales_path(tc.get("domain"))


def _build_v2_agenda(execution: dict) -> dict:
    """execution row → Hermes agenda(evidence 충실 보존). elayer_dispatch._build_agenda와 동형."""
    return {
        "execution_id": execution.get("execution_id"),
        "title": execution.get("title"),
        "br_uid": execution.get("br_uid"),
        "trigger_context": execution.get("trigger_context") or {},
    }


async def _capture_baseline(execution_id: str) -> dict:
    """v2 오케스트레이터용 — 도구실행 前 baseline 캡처를 in-process 재사용.
    atomic_engine.capture_kpi_baseline(멱등) 직호출. soft-fail(예외 없이 ok=False 반환)."""
    import app.api.routes.atomic_engine as ae
    try:
        snap = await ae.capture_kpi_baseline(ae.KpiBaselineIn(execution_id=execution_id))
    except Exception as e:  # noqa: BLE001 — 측정 실패가 v2 신경로를 중단시키면 안 됨
        logger.warning("[pipeline_v2] baseline 캡처 실패 (execution %s): %s", execution_id, e)
        return {"ok": False, "error": str(e)[:300]}
    return {
        "ok": True,
        "snapshot_id": snap.snapshot_id,
        "snapshot_type": snap.snapshot_type,
        "created": snap.created,
        "kpi_data": snap.kpi_data,
    }


async def _measure(execution_id: str) -> dict:
    """v2 오케스트레이터용 — 도구실행 後 measure(final 스냅샷+comparison+verdict 제안)를 in-process 재사용.
    atomic_engine.measure_kpi 직호출. verdict_suggested 는 제안값(확정은 운영자 finalize). soft-fail."""
    import app.api.routes.atomic_engine as ae
    try:
        snap = await ae.measure_kpi(ae.MeasureKpiIn(execution_id=execution_id))
    except Exception as e:  # noqa: BLE001
        logger.warning("[pipeline_v2] KPI 측정 실패 (execution %s): %s", execution_id, e)
        return {"ok": False, "error": str(e)[:300]}
    return {
        "ok": True,
        "snapshot_id": snap.snapshot_id,
        "comparison_data": snap.comparison_data,
        "verdict_suggested": snap.verdict_suggested,
        "kpi_data": snap.kpi_data,
    }
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_pipeline_v2.py -q` → 6 passed.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/elayer_pipeline_v2.py tests/test_pipeline_v2.py && git commit -m "feat(pipeline-v2): elayer_pipeline_v2 skeleton — _is_v2/_build_v2_agenda + in-process measure wrappers (_capture_baseline/_measure, soft-fail)"`

### 8b — run_analysis_v2 (분석→검증→proposed_actions_v2 영속→STOP) + _persist_proposed_actions_v2

- [ ] (RED) `FastAPI/tests/test_pipeline_v2.py`에 추가(_query/_update 는 v2 모듈이 lazy import 하는 cost 모듈 속성 교체):
```python
import app.services.hermes_runner as hr
import app.api.routes.cost as cost
import app.api.routes.atomic_engine as ae

_ANALYSIS = {"diagnosis": "x" * 30, "evidence_cited": ["z=-3.4"],
             "knowledge_used": ["매출 급락 대응 플레이북"],
             "proposed_actions": [{"title": "결정 기록", "what": "급락 확인", "how": "기록",
                                   "owner": "ANALYST", "eta": "즉시", "tool_tag": "record_decision",
                                   "expected_effect": "추적"}],
             "confidence": 0.72, "risk": "데이터결함"}


def _patch_db(monkeypatch):
    rows = [dict(_SALES_EXEC)]
    patched = {}
    async def _q(table, params=None): return rows
    async def _u(table, params, data): patched.update(data); return [data]
    monkeypatch.setattr(cost, "_query", _q)
    monkeypatch.setattr(cost, "_update", _u)
    return patched


def test_run_analysis_v2_persists_actions_and_stops(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    patched = _patch_db(monkeypatch)
    monkeypatch.setattr(hr, "run_hermes_analysis", lambda agenda, **kw: _ANALYSIS)
    async def _rso(inp): return None
    async def _rar(inp): return None
    monkeypatch.setattr(ae, "record_step_output", _rso)
    monkeypatch.setattr(ae, "record_agent_run", _rar)
    summary = asyncio.run(v2.run_analysis_v2("e-v2-1"))
    assert summary["result"] == "proposed"
    assert patched["phase"] == "propose_v2"          # 승인대기 STOP
    assert patched["proposed_actions_v2"]            # 액션 영속
    assert patched["proposed_actions_v2"][0]["tool_tag"] == "record_decision"


def test_run_analysis_v2_surfaces_analysis_failed(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    patched = _patch_db(monkeypatch)
    from app.services.hermes_runner import AnalysisFailed
    def boom(agenda, **kw): raise AnalysisFailed(["grounding: 인용 0"], "garbage")
    monkeypatch.setattr(hr, "run_hermes_analysis", boom)
    rec = {}
    async def _rso(inp): rec["step"] = inp
    async def _rar(inp): rec["run"] = inp
    monkeypatch.setattr(ae, "record_step_output", _rso)
    monkeypatch.setattr(ae, "record_agent_run", _rar)
    summary = asyncio.run(v2.run_analysis_v2("e-v2-1"))
    assert summary["result"] == "analysis_failed"
    assert rec["step"].status == "failed"            # step 닫힘(reconcile/UI 오인 방지)
    assert patched["phase"] == "analysis_failed"     # 사람 표면화
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_pipeline_v2.py -q -k run_analysis_v2` → AttributeError(run_analysis_v2 미정의).
- [ ] (GREEN) `app/services/elayer_pipeline_v2.py`에 추가(elayer_dispatch._dispatch_one_slot_hermes 의 record_step_output/record_agent_run 패턴 차용; hermes 는 `asyncio.to_thread`로 오프로드, **`dept='sales'`**):
```python
async def run_analysis_v2(execution_id: str) -> dict:
    """진입점① — run-v2 EP가 호출. 분석→검증게이트→proposed_actions_v2 영속→승인대기 STOP. 항상 dict(soft-fail)."""
    from app.api.routes.cost import _query, _update, _upsert
    from app.api.routes.atomic_engine import (
        StepOutputIn, AgentRunIn, record_step_output, record_agent_run)
    from app.services.hermes_runner import run_hermes_analysis, AnalysisFailed
    from app.services.atomos_bridge import _now_iso

    summary: dict[str, Any] = {"execution_id": execution_id, "started_at": _now_iso()}
    if not settings.ELAYER_PIPELINE_V2_SALES_ENABLED:
        summary["result"] = "disabled"
        return summary
    rows = await _query("strategy_executions", {"execution_id": f"eq.{execution_id}", "limit": "1"})
    if not rows:
        summary["result"] = "execution_not_found"
        return summary
    execution = rows[0]
    if not _is_v2(execution):
        summary["result"] = "not_v2"
        return summary
    # 멱등: 이미 v2 처리됨 → 재실행 가드(spec S0)
    if execution.get("phase") in ("propose_v2", "report", "sent") or execution.get("proposed_actions_v2"):
        summary["result"] = "already_v2"
        return summary
    # 분석 step 1행 전개(running) — Hermes 단일역할
    now = _now_iso()
    step_rows = await _query("strategy_step_log",
        {"execution_id": f"eq.{execution_id}", "select": "step_log_id,step_name,status",
         "order": "step_index.asc"})
    analysis_step = next((s for s in step_rows if s.get("step_name") == "분석 (ANALYST·v2)"), None)
    if analysis_step:
        step_log_id = analysis_step["step_log_id"]
    else:
        ins = await _upsert("strategy_step_log", {
            "execution_id": execution_id, "step_index": len(step_rows),
            "step_name": "분석 (ANALYST·v2)", "step_type": "manual", "status": "running",
            "started_at": now})
        step_log_id = ins[0]["step_log_id"] if ins else None
    agenda = _build_v2_agenda(execution)
    try:
        analysis = await asyncio.to_thread(
            run_hermes_analysis, agenda, role="ANALYST", dept="sales")
    except AnalysisFailed as e:
        await record_step_output(StepOutputIn(
            execution_id=execution_id, step_log_id=step_log_id,
            output_payload={"analysis_failed": e.reasons, "last_output": (e.last_output or "")[:2000]},
            status="failed"))
        await record_agent_run(AgentRunIn(
            worker_role="ATOMOS_ANALYST", platform="hermes_vps", trigger_source="pipeline_v2",
            execution_id=execution_id, step_log_id=step_log_id,
            llm_model=settings.HERMES_MODEL, llm_provider="openrouter", status="failed",
            note=f"v2 analysis failed: {'; '.join(e.reasons)[:180]}"))
        await _update("strategy_executions", {"execution_id": f"eq.{execution_id}"},
                      {"phase": "analysis_failed", "updated_at": now})
        summary["result"] = "analysis_failed"
        summary["reasons"] = e.reasons
        return summary
    except Exception as e:  # noqa: BLE001 — SSH 등 soft-fail, step 닫음
        logger.exception("[pipeline_v2] run_analysis_v2 예외 (execution %s)", execution_id)
        await record_step_output(StepOutputIn(
            execution_id=execution_id, step_log_id=step_log_id,
            output_payload={"v2_error": str(e)[:2000]}, status="failed"))
        await _update("strategy_executions", {"execution_id": f"eq.{execution_id}"},
                      {"phase": "analysis_failed", "updated_at": now})
        summary["result"] = f"error: {str(e)[:200]}"
        return summary
    await record_step_output(StepOutputIn(
        execution_id=execution_id, step_log_id=step_log_id, output_payload=analysis, status="completed"))
    await record_agent_run(AgentRunIn(
        worker_role="ATOMOS_ANALYST", platform="hermes_vps", trigger_source="pipeline_v2",
        execution_id=execution_id, step_log_id=step_log_id,
        llm_model=settings.HERMES_MODEL, llm_provider="openrouter", status="success", note="v2 analysis"))
    await _persist_proposed_actions_v2(execution_id, analysis)
    summary["result"] = "proposed"
    summary["proposed_actions"] = analysis.get("proposed_actions") or []
    return summary


async def _persist_proposed_actions_v2(execution_id: str, analysis: dict) -> None:
    """proposed_actions_v2(분석 proposed_actions 배열)+phase='propose_v2'(승인대기) 영속.
    ceo_plan_v2.items=액션 요약(승인 UI용; 이름은 FE 호환용이며 CEO 합성과 무관)."""
    from app.api.routes.cost import _update
    from app.services.atomos_bridge import _now_iso
    actions = analysis.get("proposed_actions") or []
    items = [{"idx": i, "title": a.get("title"), "tool_tag": a.get("tool_tag"),
              "what": a.get("what"), "owner": a.get("owner")} for i, a in enumerate(actions)]
    await _update("strategy_executions", {"execution_id": f"eq.{execution_id}"}, {
        "proposed_actions_v2": actions,
        "ceo_plan_v2": {"items": items, "diagnosis": analysis.get("diagnosis"),
                        "confidence": analysis.get("confidence")},
        "phase": "propose_v2", "status": "running", "updated_at": _now_iso()})
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_pipeline_v2.py -q -k run_analysis_v2` → 2 passed.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/elayer_pipeline_v2.py tests/test_pipeline_v2.py && git commit -m "feat(pipeline-v2): run_analysis_v2 — single-role Hermes analysis, validation gate, persist proposed_actions_v2, STOP at propose_v2"`

---

## Task 9: elayer_pipeline_v2 — resume_after_approval_v2 (실행→측정→보고게이트→draft)

**Files:**
- Modify: `FastAPI/app/services/elayer_pipeline_v2.py`
- Modify: `FastAPI/tests/test_pipeline_v2.py`

> repo: **FastAPI** (`~/FastAPI`). `resume_after_approval_v2(execution_id, selected_action_ids: list[str])`: selected_action_ids(=proposed_actions_v2 의 index-as-string)로 액션 선택→tool params 매핑→`safe_tools.run_tool`→실행 前 `_capture_baseline` / 後 `_measure`→`report_gate.validate_report`→통과 시 synthesized_report draft + phase 'report'. soft-fail. 멱등: phase in ('report','sent') → already. run_tool 결과 status in ('executed','skipped_idempotent')를 성공으로 본다.

- [ ] (RED) `FastAPI/tests/test_pipeline_v2.py`에 추가(safe_tools.run_tool·report_gate.validate_report 는 모듈 속성 monkeypatch):
```python
import app.services.safe_tools as st_mod
import app.services.report_gate as rg_mod
import app.api.routes.atomic_engine as ae2


def test_resume_runs_tools_measures_and_writes_draft(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    exec_row = dict(_SALES_EXEC, st_uid="ST-SE-OF-0007", phase="propose_v2",
                    proposed_actions_v2=_ANALYSIS["proposed_actions"],
                    ceo_plan_v2={"items": [{"idx": 0, "tool_tag": "record_decision"}],
                                 "diagnosis": "강남점 z=-3.4 급락 gross 850000"})
    rows = [exec_row]; patched = {}
    async def _q(table, params=None): return rows
    async def _u(table, params, data): patched.update(data); return [data]
    monkeypatch.setattr(cost, "_query", _q); monkeypatch.setattr(cost, "_update", _u)
    called = {}
    async def _run_tool(tool_tag, params, ctx):
        called["tool"] = tool_tag
        return {"tool": tool_tag, "status": "executed", "idempotency_key": "k1",
                "audit_entity_id": "e-v2-1", "result": {}}
    monkeypatch.setattr(st_mod, "run_tool", _run_tool)
    # 측정 래퍼 우회 — capture_kpi_baseline/measure_kpi 스텁
    class _Kpi:
        snapshot_id = 1; snapshot_type = "final"; created = True; kpi_data = {}
        comparison_data = {"revenue_delta_pct": 6.0}; verdict_suggested = "achieved"
    async def _base(body): return _Kpi()
    async def _meas(body): return _Kpi()
    monkeypatch.setattr(ae2, "capture_kpi_baseline", _base)
    monkeypatch.setattr(ae2, "measure_kpi", _meas)
    # 보고 신뢰게이트 — 통과
    monkeypatch.setattr(rg_mod, "validate_report", lambda rep, ag: (True, []))
    summary = asyncio.run(v2.resume_after_approval_v2("e-v2-1", ["0"]))
    assert summary["result"] == "reported"
    assert called["tool"] == "record_decision"        # 승인 액션 실행됨
    assert patched["synthesized_report"]               # draft 기록
    assert patched["phase"] == "report"


def test_resume_blocks_on_trust_gate_fail(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    exec_row = dict(_SALES_EXEC, st_uid="ST-1", phase="propose_v2",
                    proposed_actions_v2=_ANALYSIS["proposed_actions"],
                    ceo_plan_v2={"diagnosis": "x"})
    rows = [exec_row]; patched = {}
    async def _q(t, p=None): return rows
    async def _u(t, p, d): patched.update(d); return [d]
    monkeypatch.setattr(cost, "_query", _q); monkeypatch.setattr(cost, "_update", _u)
    async def _run_tool(tt, pa, c):
        return {"tool": tt, "status": "executed", "idempotency_key": "k", "audit_entity_id": "e", "result": {}}
    monkeypatch.setattr(st_mod, "run_tool", _run_tool)
    class _K:
        snapshot_id = 1; snapshot_type = "final"; created = True; kpi_data = {}
        comparison_data = None; verdict_suggested = "inconclusive"
    async def _base(b): return _K()
    async def _meas(b): return _K()
    monkeypatch.setattr(ae2, "capture_kpi_baseline", _base); monkeypatch.setattr(ae2, "measure_kpi", _meas)
    monkeypatch.setattr(rg_mod, "validate_report", lambda rep, ag: (False, ["substance: 일반론"]))
    summary = asyncio.run(v2.resume_after_approval_v2("e-v2-1", ["0"]))
    assert summary["result"] == "report_blocked"
    assert "synthesized_report" not in patched          # 차단 → draft 미기록
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_pipeline_v2.py -q -k resume` → AttributeError(resume_after_approval_v2 미정의).
- [ ] (GREEN) `app/services/elayer_pipeline_v2.py`에 추가(액션 선택 = selected_action_ids 의 index-as-string; 측정은 _capture_baseline/_measure 래퍼; 보고게이트는 report_gate.validate_report 를 **모듈 속성**으로 호출):
```python
def _select_actions_by_ids(execution: dict, selected_action_ids: list) -> list:
    """승인된 액션 = proposed_actions_v2[int(id)] (id는 index-as-string). 범위밖/비정수 제외, 순서 보존."""
    actions = execution.get("proposed_actions_v2") or []
    out = []
    seen = set()
    for sid in selected_action_ids or []:
        try:
            idx = int(sid)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(actions) and idx not in seen:
            seen.add(idx)
            out.append(actions[idx])
    return out


def _action_to_params(action: dict, execution: dict) -> dict:
    """proposed_action → safe_tools params. tool_tag별 필수 params 매핑(레지스트리 required_params 기준)."""
    tag = action.get("tool_tag")
    st_id = (execution.get("trigger_context") or {}).get("st_id")
    if tag == "record_decision":
        return {"verdict": "approve", "note": action.get("what") or action.get("title") or "", "scope": st_id}
    if tag == "create_task":
        return {"owner": action.get("owner") or "ANALYST", "action": action.get("what") or action.get("title") or "",
                "due": action.get("eta")}
    return dict(action)


def _draft_report(execution: dict, actions: list, diagnosis: str, comparison: dict) -> dict:
    """synthesized_report draft(SYNTH 형태). v2는 단일역할이라 CEO 합성 없이 결정론 draft."""
    return {
        "executive_summary": (diagnosis or "")[:400],
        "prioritized_actions": [{"action": a.get("title"), "owner": a.get("owner"),
                                 "priority": "med", "rationale": a.get("what")} for a in actions],
        "deliverables": [{"slot": "ATOMOS_ANALYST", "kind": "diagnosis",
                          "summary": (diagnosis or "")[:200]}],
        "store_message": "", "_v2": True, "measurement": comparison or {},
    }


async def resume_after_approval_v2(execution_id: str, selected_action_ids: list) -> dict:
    """진입점② — approve EP가 호출. 승인액션 safe_tools 실행→측정→보고게이트→synthesized_report draft. soft-fail."""
    from app.api.routes.cost import _query, _update
    from app.services import safe_tools
    from app.services import report_gate
    from app.services.atomos_bridge import _now_iso

    summary: dict[str, Any] = {"execution_id": execution_id, "started_at": _now_iso()}
    if not settings.ELAYER_PIPELINE_V2_SALES_ENABLED:
        summary["result"] = "disabled"
        return summary
    rows = await _query("strategy_executions", {"execution_id": f"eq.{execution_id}", "limit": "1"})
    if not rows:
        summary["result"] = "execution_not_found"
        return summary
    execution = rows[0]
    if execution.get("phase") in ("report", "sent"):       # 멱등
        summary["result"] = "already_reported"
        return summary
    actions = _select_actions_by_ids(execution, selected_action_ids)
    ctx = {"execution_id": execution_id, "st_uid": execution.get("st_uid"),
           "st_id": (execution.get("trigger_context") or {}).get("st_id")}
    # 도구 실행 前 baseline
    await _capture_baseline(execution_id)
    tool_results = []
    for a in actions:
        tag = a.get("tool_tag")
        try:
            r = await safe_tools.run_tool(tag, _action_to_params(a, execution), ctx)
            ok = r.get("status") in ("executed", "skipped_idempotent")
        except Exception as e:  # noqa: BLE001 — 도구별 soft-fail
            logger.exception("[pipeline_v2] run_tool 실패 tag=%s execution=%s", tag, execution_id)
            r = {"tool": tag, "status": "error", "error": str(e)[:200]}
            ok = False
        tool_results.append({"tool_tag": tag, "ok": ok, **r})
    summary["tools"] = tool_results
    # 도구 실행 後 measure(soft-fail — st_uid 부재 등은 보고를 막지 않음)
    measured = await _measure(execution_id)
    comparison = (measured.get("comparison_data") or {}) if measured.get("ok") else {}
    if measured.get("ok") and measured.get("verdict_suggested"):
        comparison = {**comparison, "verdict_suggested": measured["verdict_suggested"]}
    diag = (execution.get("ceo_plan_v2") or {}).get("diagnosis") or ""
    report = _draft_report(execution, actions, diag, comparison)
    ok, reasons = report_gate.validate_report(report, execution)
    if not ok:
        await _update("strategy_executions", {"execution_id": f"eq.{execution_id}"},
                      {"phase": "report_blocked", "updated_at": _now_iso()})
        summary["result"] = "report_blocked"
        summary["gate_reasons"] = reasons
        return summary
    await _update("strategy_executions", {"execution_id": f"eq.{execution_id}"},
                  {"synthesized_report": report, "phase": "report", "updated_at": _now_iso()})
    summary["result"] = "reported"
    return summary
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_pipeline_v2.py -q -k resume` → 2 passed.
- [ ] (전체 모듈 회귀) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_pipeline_v2.py -q` → 전부 passed(8a~9 합산).
- [ ] (COMMIT) `cd ~/FastAPI && git add app/services/elayer_pipeline_v2.py tests/test_pipeline_v2.py && git commit -m "feat(pipeline-v2): resume_after_approval_v2 — run approved safe_tools, baseline/measure, report_gate, write synthesized_report draft"`

---

## Task 10: run-v2 EP + feed/detail v2-컬럼 노출

**Files:**
- Modify: `FastAPI/app/api/routes/strategy.py`
- Create/Test: `FastAPI/tests/test_run_v2_ep.py`

> repo: **FastAPI** (`~/FastAPI`). `POST /api/strategy/executions/{id}/run-v2` → `await run_analysis_v2(execution_id)` (ANALYZE only). diagnose EP(라인 ~656-700) 구조 미러하되 send_task 아니라 오케스트레이터 **동기 await**. 플래그 OFF → {status:'v2_disabled'}, 404 missing, 멱등(run_analysis_v2 내부 already_v2 가 처리). 또 feed EP select 에 `proposed_actions_v2,ceo_plan_v2` 추가(FE 렌더용).

- [ ] (RED) `FastAPI/tests/test_run_v2_ep.py` 신규 — 핸들러를 `asyncio.run` 직호출 + `strategy._query` monkeypatch:
```python
import asyncio
import pytest
from fastapi import HTTPException
from app.api.routes import strategy
from app.api.routes.strategy import run_v2_execution


_EXEC = {"execution_id": "e1", "phase": "detect", "status": "pending",
         "trigger_context": {"domain": "sales", "st_id": "ST-1",
                             "evidence": {"sigma": -3.4, "n": 28, "dow": "Fri", "confidence": 0.82}}}


def _patch_query(monkeypatch, rows):
    async def fake_query(table, params=None):
        return rows
    monkeypatch.setattr(strategy, "_query", fake_query)


def test_run_v2_404_when_missing(monkeypatch):
    _patch_query(monkeypatch, [])
    monkeypatch.setattr(strategy.settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(run_v2_execution("e1"))
    assert ei.value.status_code == 404


def test_run_v2_disabled_when_flag_off(monkeypatch):
    _patch_query(monkeypatch, [dict(_EXEC)])
    monkeypatch.setattr(strategy.settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", False)
    out = asyncio.run(run_v2_execution("e1"))
    assert out["status"] == "v2_disabled"


def test_run_v2_invokes_orchestrator(monkeypatch):
    _patch_query(monkeypatch, [dict(_EXEC)])
    monkeypatch.setattr(strategy.settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    import app.services.elayer_pipeline_v2 as pv2
    async def fake_run(execution_id):
        assert execution_id == "e1"
        return {"result": "proposed", "execution_id": "e1"}
    monkeypatch.setattr(pv2, "run_analysis_v2", fake_run)
    out = asyncio.run(run_v2_execution("e1"))
    assert out["status"] == "ok"
    assert out["result"]["result"] == "proposed"


def test_run_v2_idempotent_passthrough(monkeypatch):
    # 이미 propose_v2 → 오케스트레이터가 already_v2 반환(멱등은 run_analysis_v2 내부 책임)
    _patch_query(monkeypatch, [dict(_EXEC, phase="propose_v2")])
    monkeypatch.setattr(strategy.settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    import app.services.elayer_pipeline_v2 as pv2
    async def fake_run(execution_id):
        return {"result": "already_v2", "execution_id": "e1"}
    monkeypatch.setattr(pv2, "run_analysis_v2", fake_run)
    out = asyncio.run(run_v2_execution("e1"))
    assert out["result"]["result"] == "already_v2"
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_run_v2_ep.py -q` → FAIL(run_v2_execution 미정의).
- [ ] (GREEN) `strategy.py`에 EP 추가 — diagnose EP 구조 미러, **동기 await**(enqueue 아님):
```python
@router.post(
    "/executions/{execution_id}/run-v2",
    summary="매출 v2 단일경로 분석 동기 트리거 (Phase2, 테스트·시연용)",
)
async def run_v2_execution(execution_id: str):
    """sales execution 1건을 v2 경로(CEO/슬롯/Paperclip 없이)로 분석 관통(ANALYZE only).
    승인은 approve EP가 resume 트리거. 플래그 OFF→v2_disabled. 멱등은 run_analysis_v2 내부 already_v2."""
    _validate_execution_id(execution_id)
    rows = await _query("strategy_executions", {"execution_id": f"eq.{execution_id}", "limit": "1"})
    if not rows:
        raise HTTPException(404, f"execution_id={execution_id} 없음")
    if not settings.ELAYER_PIPELINE_V2_SALES_ENABLED:
        return {"execution_id": execution_id, "status": "v2_disabled"}
    from app.services.elayer_pipeline_v2 import run_analysis_v2
    result = await run_analysis_v2(execution_id)
    return {"execution_id": execution_id, "status": "ok", "result": result}
```
- [ ] (GREEN) feed EP `get_atomic_feed_ep`(라인 ~1597) select 문자열에 `proposed_actions_v2,ceo_plan_v2` 추가(FE 가 v2 row 렌더 가능하도록):
```python
    exec_params = {
        "select": (
            "execution_id,status,phase,ceo_plan,ceo_plan_v2,proposed_actions_v2,user_decision,send_status,sent_at,"
            "synthesized_report,st_uid,trigger_context,title,ai_recommendation,created_at,completed_at"
        ),
        "order": "created_at.desc",
        "limit": "200",
        "status": "neq.cancelled",
    }
```
  (상세/리스트 EP는 `select: "*"`라 신규 컬럼 자동 포함 — 추가 작업 불요.)
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_run_v2_ep.py -q` → 4 passed.
- [ ] (회귀) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_feed_classify.py -q` → feed 분류 불변 PASS(컬럼 추가는 additive).
- [ ] (COMMIT) `cd ~/FastAPI && git add app/api/routes/strategy.py tests/test_run_v2_ep.py && git commit -m "feat(pipeline-v2): POST /executions/{id}/run-v2 sync analyze trigger + expose proposed_actions_v2/ceo_plan_v2 in feed select"`

---

## Task 11: ApproveIn.selected_actions + v2 approve 분기 (resume_after_approval_v2 호출)

**Files:**
- Modify: `FastAPI/app/api/routes/strategy.py`
- Create/Test: `FastAPI/tests/test_approve_actions.py`

> repo: **FastAPI** (`~/FastAPI`). `ApproveIn.selected_actions: Optional[list[str]] = None`(selected_kinds 와 공존). v2 분기는 **409 진단중 가드 뒤(strategy.py:858-860)·레거시 selected_kinds 로직 앞(strategy.py:867)**에 삽입, early-return: id 검증 → `await resume_after_approval_v2(execution_id, selected_action_ids)` → `_write_audit('approve_actions',...)`. 레거시 경로(selected_actions is None)는 **불변**. resume 는 분기 내부 lazy-import.

- [ ] (RED) `FastAPI/tests/test_approve_actions.py` 신규:
```python
import asyncio
import pytest
from fastapi import HTTPException
from app.api.routes import strategy
from app.api.routes.strategy import ApproveIn, _approve_one
from app.core.config import settings


_ACTIONS = [
    {"title": "결정 기록", "tool_tag": "record_decision", "what": "w", "how": "h",
     "owner": "ANALYST", "eta": "1d", "expected_effect": "e"},
    {"title": "후속 태스크", "tool_tag": "create_task", "what": "w2", "how": "h2",
     "owner": "ANALYST", "eta": "2d", "expected_effect": "e2"},
]


def test_approvein_accepts_selected_actions():
    body = ApproveIn(execution_id="e1", selected_actions=["0", "1"])
    assert body.selected_actions == ["0", "1"]
    # 옛 필드 공존 — selected_actions 미지정 시 None(레거시)
    assert ApproveIn(execution_id="e1", selected_kinds=["sales"]).selected_actions is None


def _make_exec(phase="propose_v2"):
    return {"execution_id": "e1", "phase": phase, "status": "running",
            "user_decision": "pending", "trigger_context": {"domain": "sales", "st_id": "ST-1"},
            "st_uid": "ST-1", "proposed_actions_v2": _ACTIONS,
            "ceo_plan_v2": {"items": [{"idx": 0}, {"idx": 1}]}}


def _patch_db(monkeypatch, execution):
    async def fake_query(table, params=None):
        if table == "strategy_executions":
            return [execution]
        return []
    async def fake_update(table, match, patch): execution.update(patch); return [execution]
    async def fake_audit(*a, **k): return None
    monkeypatch.setattr(strategy, "_query", fake_query)
    monkeypatch.setattr(strategy, "_update", fake_update)
    monkeypatch.setattr(strategy, "_write_audit", fake_audit)


def test_v2_branch_calls_resume_with_selected_ids(monkeypatch):
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    captured = {}
    import app.services.elayer_pipeline_v2 as pv2
    async def fake_resume(execution_id, selected_action_ids):
        captured["ids"] = selected_action_ids; return {"result": "reported"}
    monkeypatch.setattr(pv2, "resume_after_approval_v2", fake_resume)
    _patch_db(monkeypatch, _make_exec())
    out = asyncio.run(_approve_one(ApproveIn(execution_id="e1", selected_actions=["0", "1"])))
    assert captured["ids"] == ["0", "1"]
    assert out.get("v2") is True


def test_v2_branch_validates_ids(monkeypatch):
    # 범위밖 id 는 제외하고 유효한 것만 resume 에 전달
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    captured = {}
    import app.services.elayer_pipeline_v2 as pv2
    async def fake_resume(execution_id, selected_action_ids):
        captured["ids"] = selected_action_ids; return {"result": "reported"}
    monkeypatch.setattr(pv2, "resume_after_approval_v2", fake_resume)
    _patch_db(monkeypatch, _make_exec())
    asyncio.run(_approve_one(ApproveIn(execution_id="e1", selected_actions=["1", "99"])))
    assert captured["ids"] == ["1"]   # "99"는 proposed_actions_v2 범위밖 → 제외


def test_v2_blocked_while_diagnosing(monkeypatch):
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    _patch_db(monkeypatch, _make_exec(phase="diagnose"))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(_approve_one(ApproveIn(execution_id="e1", selected_actions=["0"])))
    assert ei.value.status_code == 409


def test_legacy_path_does_not_call_resume(monkeypatch):
    # selected_actions 미지정(옛 경로) → resume 호출 0 (옛 슬롯/디스패치 경로 불변)
    monkeypatch.setattr(settings, "ELAYER_PIPELINE_V2_SALES_ENABLED", True)
    called = {"n": 0}
    import app.services.elayer_pipeline_v2 as pv2
    async def fake_resume(*a, **k): called["n"] += 1; return {}
    monkeypatch.setattr(pv2, "resume_after_approval_v2", fake_resume)
    exe = _make_exec(phase=None)
    exe["ai_recommendation"] = {"steps": []}
    exe.pop("ceo_plan_v2", None); exe.pop("proposed_actions_v2", None)
    async def fake_upsert(table, row): return [row] if isinstance(row, dict) else row
    monkeypatch.setattr(strategy, "_upsert", fake_upsert)
    _patch_db(monkeypatch, exe)
    asyncio.run(_approve_one(ApproveIn(execution_id="e1")))  # selected_actions=None
    assert called["n"] == 0
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_approve_actions.py -q` → FAIL(ApproveIn.selected_actions 없음 / v2 분기 미구현).
- [ ] (GREEN) `ApproveIn`(strategy.py:386 selected_kinds 바로 아래)에 필드 추가:
```python
    selected_actions: Optional[list[str]] = Field(
        default=None,
        description="v2 도구액션 승인 — proposed_actions_v2 의 index-as-string('0'..'n') 리스트. None=옛 경로(불변).",
    )
```
- [ ] (GREEN) `_approve_one`(strategy.py:837)에 v2 분기 삽입 — 409 가드(라인 858-860) **뒤**, 레거시 selected_kinds 병합(라인 867) **앞**. early-return:
```python
    # ── v2 단일경로: 도구액션 단위 승인 (옛 슬롯/CEO/Celery 경로 우회). selected_actions None=레거시 ──
    if settings.ELAYER_PIPELINE_V2_SALES_ENABLED and body.selected_actions is not None:
        proposed = execution.get("proposed_actions_v2") or []
        # id 검증 — proposed_actions_v2 범위 내 index-as-string 만 통과(순서 보존·중복 제거)
        valid_ids: list[str] = []
        seen: set[int] = set()
        for sid in body.selected_actions:
            try:
                idx = int(sid)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(proposed) and idx not in seen:
                seen.add(idx)
                valid_ids.append(str(idx))
        from app.services.elayer_pipeline_v2 import resume_after_approval_v2
        result = await resume_after_approval_v2(body.execution_id, valid_ids)
        await _write_audit("approve_actions", "strategy_execution", body.execution_id,
                           decision_type=body.decision_type, before_data=before_data,
                           after_data={"v2": True, "selected_actions": valid_ids},
                           metadata={"v2_result": result.get("result"), "selected_actions": valid_ids})
        return {"message": f"실행 {body.execution_id} v2 도구액션 {len(valid_ids)}건 승인·실행",
                "steps_created": 0, "actions_executed": len(valid_ids),
                "decision_type": body.decision_type, "v2": True, "v2_result": result.get("result")}
```
  주의: `before_data`는 라인 862-864에서 이미 계산되므로 v2 분기에서도 사용 가능(409 가드 뒤·before_data 계산 뒤에 배치). 레거시 경로(selected_actions is None)는 이 분기를 건너뛰어 **완전 불변**.
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_approve_actions.py -q` → 전부 PASS.
- [ ] (회귀, 옛 경로 불변) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_batch_decisions.py tests/test_feed_classify.py tests/test_hermes_dispatch.py -q` → 전부 PASS.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/api/routes/strategy.py tests/test_approve_actions.py && git commit -m "feat(pipeline-v2): ApproveIn.selected_actions + _approve_one v2 branch — call resume_after_approval_v2 (legacy unchanged)"`

---

## Task 12: send_execution_report 신뢰게이트 통합

**Files:**
- Modify: `FastAPI/app/api/routes/strategy.py`
- Create/Test: `FastAPI/tests/test_send_report_gate.py`

> repo: **FastAPI** (`~/FastAPI`). send EP `send_execution_report`(strategy.py:615)의 `sent_at` 멱등 체크 직후·`from app.services.elayer_send import ...` 직전에 `report_gate.validate_report` 게이트 삽입. fallback 포함 모든 리포트가 통과해야 발송. 발송 자체는 SANDBOX·ENABLED OFF 불변. select 절에 `trigger_context` 추가(grounding evidence 확보).

- [ ] (RED) `FastAPI/tests/test_send_report_gate.py` 신규(batch_decisions monkeypatch+asyncio.run 미러):
```python
import asyncio
import pytest
from app.api.routes import strategy
from app.services import elayer_send

AGENDA_EVID = {"z": -3.4, "gross": 850000, "mu": 1460000}


def _setup(monkeypatch, report, *, enabled=True, sent_at=None):
    monkeypatch.setattr(strategy.settings, "ATOMOS_SEND_TOKEN", "tok", raising=False)
    monkeypatch.setattr(strategy.settings, "ELAYER_SEND_ENABLED", enabled, raising=False)
    monkeypatch.setattr(strategy.settings, "ATOMOS_SEND_SANDBOX_TO", "glen@example.com", raising=False)
    row = {"execution_id": "e1", "title": "[자동감지] 매출 급락 대응: 강남점",
           "synthesized_report": report, "sent_at": sent_at, "send_to": None, "st_uid": "ST-SE-OF-0007",
           "trigger_context": {"evidence": AGENDA_EVID}}
    async def fake_query(table, params):
        return [row]
    updates = []
    async def fake_update(table, where, data):
        updates.append(data); return [{}]
    audits = []
    async def fake_audit(*a, **k):
        audits.append((a, k))
    sent = []
    async def fake_send(to, subject, body):
        sent.append((to, subject)); return {"ok": True, "id": "re_1"}
    monkeypatch.setattr(strategy, "_query", fake_query)
    monkeypatch.setattr(strategy, "_update", fake_update)
    monkeypatch.setattr(strategy, "_write_audit", fake_audit)
    monkeypatch.setattr(elayer_send, "send_email", fake_send)
    return updates, audits, sent


GOOD = {
    "executive_summary": "강남점 일매출이 z=-3.4로 급락. gross 850000은 평소 mu 1460000 대비 약 42% 낮습니다.",
    "prioritized_actions": [{"action": "점주 통지", "owner": "ANALYST", "priority": "high", "rationale": "gross 850000 확인"}],
    "deliverables": [{"slot": "ATOMOS_ANALYST", "kind": "diagnosis", "summary": "급락"}],
    "store_message": "사장님 어제 매출이 평소 1460000원 대비 850000원으로 낮았습니다. 확인 부탁드립니다.",
}
FALLBACK = {"executive_summary": "(자동 합성 미수행 — 원본 산출물 묶음)",
            "prioritized_actions": [{"action": "진단", "owner": "ANALYST", "priority": "med", "rationale": "원본 슬롯 액션"}],
            "deliverables": [{"slot": "ATOMOS_ANALYST", "kind": "output", "summary": "진단"}],
            "store_message": "", "_fallback": "bundle"}


def test_gate_blocks_fallback_report(monkeypatch):
    updates, audits, sent = _setup(monkeypatch, FALLBACK)
    with pytest.raises(strategy.HTTPException) as ei:
        asyncio.run(strategy.send_execution_report("e1", x_atomos_send_token="tok"))
    assert ei.value.status_code == 422
    assert sent == []                                   # send_email 미호출
    assert any(u.get("send_status") == "gate_blocked" for u in updates)


def test_gate_allows_good_report(monkeypatch):
    updates, audits, sent = _setup(monkeypatch, GOOD)
    out = asyncio.run(strategy.send_execution_report("e1", x_atomos_send_token="tok"))
    assert out["status"] == "sent"
    assert len(sent) == 1


def test_disabled_short_circuits_before_gate(monkeypatch):
    updates, audits, sent = _setup(monkeypatch, FALLBACK, enabled=False)
    out = asyncio.run(strategy.send_execution_report("e1", x_atomos_send_token="tok"))
    assert out["status"] == "disabled"                  # ENABLED OFF 불변식 보존
    assert sent == []
```
- [ ] (RED 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_send_report_gate.py -q` → `test_gate_blocks_fallback_report` FAIL(현재는 FALLBACK 도 sent 처리).
- [ ] (GREEN) `send_execution_report` 의 `sent_at` 멱등 체크 직후, `from app.services.elayer_send import ...` 직전에 게이트 삽입:
```python
    if execution.get("sent_at"):
        return {"status": "already_sent", "send_to": execution.get("send_to"), "sent_at": execution.get("sent_at")}

    # 보고 신뢰게이트(S6) — fallback 포함 모든 리포트가 통과해야 발송 적격
    from app.services.report_gate import validate_report
    ok, reasons = validate_report(execution.get("synthesized_report") or {}, execution)
    if not ok:
        await _update("strategy_executions", {"execution_id": f"eq.{execution_id}"},
                      {"send_status": "gate_blocked"})
        await _write_audit("send_blocked", "strategy_execution", execution_id,
                           metadata={"reasons": reasons})
        raise HTTPException(422, f"보고 신뢰게이트 차단: {reasons}")

    from app.services.elayer_send import build_owner_email, send_email
```
  주의: `validate_report(report, agenda)`의 agenda 로 `execution` row 자체를 넘긴다(trigger_context.evidence 포함).
- [ ] (GREEN) select 절 보강 — 동 EP `_query(... "select": "execution_id,title,synthesized_report,sent_at,send_to,st_uid")` 를 `"...,send_to,st_uid,trigger_context"` 로 수정(grounding 대조 evidence 확보):
```python
        "select": "execution_id,title,synthesized_report,sent_at,send_to,st_uid,trigger_context"})
```
- [ ] (GREEN 실행) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_send_report_gate.py -q` → 3 passed.
- [ ] (회귀 + 불변식) `cd ~/FastAPI && venv/bin/python -m pytest tests/test_batch_decisions.py tests/test_analysis_gate.py -q` → PASS. grep 으로 SANDBOX 하드코딩·ENABLED OFF 가드가 게이트 추가 후에도 존재 확인: `grep -n "ATOMOS_SEND_SANDBOX_TO\|ELAYER_SEND_ENABLED" app/api/routes/strategy.py`.
- [ ] (COMMIT) `cd ~/FastAPI && git add app/api/routes/strategy.py tests/test_send_report_gate.py && git commit -m "feat(pipeline-v2): wire report trust gate into send EP — block fallback/ungrounded (S6)"`

---

## Task 13: FE — v2View.ts 순수 헬퍼 + v2View.test.ts + ProposedActionV2 타입

**Files:**
- Create: `hbs-dashboard/src/pages/atomic/v2View.ts`
- Create/Test: `hbs-dashboard/src/pages/atomic/v2View.test.ts`
- Modify: `hbs-dashboard/src/api/types.ts`

> repo: **hbs** (`~/hbs-dashboard`). atomic 테스트는 전부 순수 함수 vitest. FE 로직을 헬퍼로 추출해 TDD. v2 분석 산출 shape는 FastAPI `hermes_prompt.py _SCHEMA` 의 `proposed_actions[]{title,what,how,owner,eta,tool_tag,expected_effect}`와 1:1. **canonical: FE 필드명 = `proposed_actions_v2`(타입 `ProposedActionV2`). `isV2Execution`는 `proposed_actions_v2` 비어있지 않음 AND `ceo_plan` 부재로 판별.**

- [ ] (RED) `src/api/types.ts`에 타입 추가(테스트 import 가능하도록 최소 선언):
```ts
// (types.ts, CeoProposalItem/CeoPlan 인근에 추가)
export interface ProposedActionV2 {
  title: string;
  what: string;
  how: string;
  owner: string;
  eta: string;
  tool_tag: string;
  expected_effect: string;
}
```
  그리고 `StrategyExecRecord`에 선택 필드 추가(`phase?` 라인 아래):
```ts
proposed_actions_v2?: ProposedActionV2[] | null;   // v2(Phase2) 분석 산출 — 도구액션 승인 단위
```
  (FeedItem 은 extends StrategyExecRecord 이므로 자동 상속.)
- [ ] (RED) `src/pages/atomic/v2View.test.ts` 신규:
```ts
import { describe, it, expect } from "vitest";
import { isV2Execution, toToolActions, buildSelectedActions } from "./v2View";
import type { ProposedActionV2 } from "@/api/types";

const act = (p: Partial<ProposedActionV2> = {}): ProposedActionV2 => ({
  title: "t", what: "w", how: "h", owner: "o", eta: "e",
  tool_tag: "record_decision", expected_effect: "x", ...p,
});

describe("isV2Execution", () => {
  it("proposed_actions_v2 있고 ceo_plan 없으면 v2", () => {
    expect(isV2Execution({ proposed_actions_v2: [act()], ceo_plan: null })).toBe(true);
  });
  it("ceo_plan 있으면(레거시 2P) v2 아님", () => {
    expect(isV2Execution({ proposed_actions_v2: [act()], ceo_plan: { items: [] } })).toBe(false);
  });
  it("proposed_actions_v2 비었거나 없으면 v2 아님", () => {
    expect(isV2Execution({ proposed_actions_v2: [], ceo_plan: null })).toBe(false);
    expect(isV2Execution({ ceo_plan: null })).toBe(false);
  });
});

describe("toToolActions", () => {
  it("index 기반 id 부여 + 필드 매핑", () => {
    const v = toToolActions([act({ title: "A", tool_tag: "create_task", expected_effect: "+5%" })]);
    expect(v).toHaveLength(1);
    expect(v[0]).toMatchObject({ id: "0", title: "A", toolTag: "create_task", expectedEffect: "+5%" });
  });
  it("null/undefined → []", () => {
    expect(toToolActions(null)).toEqual([]);
    expect(toToolActions(undefined)).toEqual([]);
  });
});

describe("buildSelectedActions", () => {
  it("체크된 id만 원래 순서로", () => {
    expect(buildSelectedActions(["0", "1", "2"], new Set(["2", "0"]))).toEqual(["0", "2"]);
  });
  it("아무것도 안 체크 → []", () => {
    expect(buildSelectedActions(["0", "1"], new Set())).toEqual([]);
  });
});
```
- [ ] (RED 실행) `cd ~/hbs-dashboard && npx vitest run src/pages/atomic/v2View.test.ts` → `Cannot find module './v2View'` FAIL.
- [ ] (GREEN) `src/pages/atomic/v2View.ts` 신규:
```ts
/** v2(Phase2 매출 슬라이스) 콘솔 표시 — CEO/슬롯 없는 도구액션 승인용 순수 헬퍼. */
import type { ProposedActionV2, CeoPlan } from "@/api/types";

export interface ToolActionView {
  id: string;          // proposed_actions_v2 배열 index(문자열) — selected_actions 식별자
  title: string;
  toolTag: string;
  what: string;
  how: string;
  expectedEffect: string;
}

/** v2 판별: 분석 산출 proposed_actions_v2 가 있고 레거시 ceo_plan 이 없음. */
export function isV2Execution(row: { proposed_actions_v2?: ProposedActionV2[] | null; ceo_plan?: CeoPlan | null }): boolean {
  const acts = row.proposed_actions_v2;
  return Array.isArray(acts) && acts.length > 0 && !row.ceo_plan;
}

export function toToolActions(actions: ProposedActionV2[] | null | undefined): ToolActionView[] {
  if (!Array.isArray(actions)) return [];
  return actions.map((a, i) => ({
    id: String(i),
    title: a.title,
    toolTag: a.tool_tag,
    what: a.what,
    how: a.how,
    expectedEffect: a.expected_effect,
  }));
}

/** 전체 id 순서를 보존하며 체크된 것만. */
export function buildSelectedActions(allIds: string[], checkedIds: Set<string>): string[] {
  return allIds.filter(id => checkedIds.has(id));
}
```
- [ ] (GREEN 실행) `cd ~/hbs-dashboard && npx vitest run src/pages/atomic/v2View.test.ts` → 모든 it PASS.
- [ ] (COMMIT) `cd ~/hbs-dashboard && git add src/pages/atomic/v2View.ts src/pages/atomic/v2View.test.ts src/api/types.ts && git commit -m "feat(atomic-v2): v2 도구액션 뷰 순수 헬퍼 + ProposedActionV2 타입 (S7-1)"`

---

## Task 14: FE — types.ts + client.ts (approve selected_actions + runV2)

**Files:**
- Modify: `hbs-dashboard/src/api/client.ts`
- (Task 13에서 types.ts ProposedActionV2 추가 완료)

> repo: **hbs** (`~/hbs-dashboard`). client.ts 함수는 순수 단위테스트 대상 아님(http 의존). 검증 = tsc 빌드 통과 + 사용처(Task 15) 컴파일. `approve`에 `selected_actions?:string[]`, `runV2(id)` 추가.

- [ ] (GREEN) `src/api/client.ts` `strategyExecApi.approve` 시그니처에 `selected_actions` 추가(기존 동작 불변, 필드만 확장):
```ts
  // POST /api/strategy/approve
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  approve: async (body: { execution_id: string; modifications?: any; decision_type?: string; selected_kinds?: string[]; selected_actions?: string[] }): Promise<any> => {
    const { data } = await http.post('/api/strategy/approve', body);
    return data;
  },
```
- [ ] (GREEN) 같은 `strategyExecApi` 객체에 `runV2` 추가(`diagnose` 인근):
```ts
  // POST /api/strategy/executions/{id}/run-v2 — Phase2 v2 단일경로 분석 동기 트리거(시연·테스트용).
  runV2: async (id: string): Promise<{ execution_id: string; status: string; result?: any }> => {
    const { data } = await http.post<{ execution_id: string; status: string; result?: any }>(
      `/api/strategy/executions/${id}/run-v2`,
      {},
    );
    return data;
  },
```
- [ ] (타입체크/회귀) `cd ~/hbs-dashboard && npx tsc -b --noEmit` → 에러 0. `cd ~/hbs-dashboard && npx vitest run src/pages/atomic` → 전부 PASS(헬퍼·기존 테스트 불변).
- [ ] (COMMIT) `cd ~/hbs-dashboard && git add src/api/client.ts && git commit -m "feat(atomic-v2): approve selected_actions 필드 + runV2 클라이언트 (S7-2)"`

---

## Task 15: FE — ExecutionDetailModal v2 ToolActionPanel + 낙관 전이 + 빌드 게이트

**Files:**
- Modify: `hbs-dashboard/src/pages/atomic/ExecutionDetailModal.tsx`
- Modify: `hbs-dashboard/src/pages/atomic/AtomicConsole.tsx`

> repo: **hbs** (`~/hbs-dashboard`). propose 분기에서 v2 row면 `ProposePanel`(CEO 카피) 대신 신규 `ToolActionPanel` 렌더. 승인은 `selected_actions`로. '눌러도 안 변함' 해소 = 승인 성공 시 패널을 "완료" 전이 상태로 즉시 교체(낙관) + onClose 시 기존 invalidate가 피드 갱신. 헬퍼 로직은 Task 13에서 검증됨(여기선 배선만). **CEO/슬롯 어휘 전혀 없음 — '제안 액션'·'승인'만.**

- [ ] import 추가(파일 상단):
```ts
import { isV2Execution, toToolActions, buildSelectedActions, type ToolActionView } from "./v2View";
import type { ProposedActionV2 } from "@/api/types";
```
  `Props`에 v2 산출 전달 필드 추가(없으면 기존 동작 불변):
```ts
/** v2(Phase2) 분석 산출 — 있으면 CEO 카피 없는 도구액션 패널로 렌더 */
initialProposedActions?: ProposedActionV2[] | null;
```
  함수 시그니처: `export function ExecutionDetailModal({ executionId, onClose, initialPhase, initialCeoPlan, initialProposedActions }: Props) {`
- [ ] 신규 `ToolActionPanel` 컴포넌트 추가(`ProposePanel` 인근, CEO 어휘 없음):
```tsx
/** v2 도구액션 승인 패널 — CEO/슬롯 카피 없음. proposed_actions_v2 각각을 승인 단위로 노출. */
function ToolActionPanel({
  actions, executionId, onClose,
}: { actions: ProposedActionV2[]; executionId: string; onClose: () => void }) {
  const views: ToolActionView[] = toToolActions(actions);
  const allIds = views.map(v => v.id);
  const [checked, setChecked] = useState<Set<string>>(new Set(allIds));
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);      // 승인 후 즉시 전이(낙관) — '눌러도 안 변함' 해소
  const [error, setError] = useState<string | null>(null);

  const toggle = (id: string) => setChecked(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const doApprove = async () => {
    setBusy(true); setError(null);
    try {
      await strategyExecApi.approve({
        execution_id: executionId,
        decision_type: 'approve',
        selected_actions: buildSelectedActions(allIds, checked),
      });
      setDone(true);   // 화면 즉시 전이
    } catch (e: any) {
      setError(`승인 실패: ${e?.response?.data?.detail ?? e?.message ?? e}`);
    } finally { setBusy(false); }
  };

  if (done) {
    return (
      <div style={{ padding: '24px 4px' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 20,
          background: '#dcfce7', color: '#15803d', fontSize: 13, fontWeight: 600, marginBottom: 16,
        }}>
          ✅ 승인 완료 — 실행 단계로 이동했습니다
        </div>
        <div style={{ marginTop: 4 }}>
          <button onClick={onClose} style={{ background: '#2563eb', color: '#fff', padding: '8px 18px', borderRadius: 5, border: 'none', fontWeight: 600, cursor: 'pointer' }}>
            닫기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '4px 0' }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-sub)', marginBottom: 12 }}>
        분석이 제안한 대응 액션입니다. 실행할 항목을 선택해 승인하세요.
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
        {views.length === 0 && (
          <div style={{ fontSize: 13, color: 'var(--text-sub)' }}>제안 액션이 없습니다.</div>
        )}
        {views.map(v => (
          <label key={v.id} style={{
            display: 'flex', gap: 10, alignItems: 'flex-start', cursor: 'pointer',
            padding: '10px 14px', border: '1px solid var(--border, #e5e7eb)', borderRadius: 8,
          }}>
            <input type="checkbox" checked={checked.has(v.id)} onChange={() => toggle(v.id)} style={{ marginTop: 2, flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>
                {v.title}
                <span style={{ marginLeft: 6, fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#e0f2fe', color: '#0369a1' }}>
                  {v.toolTag}
                </span>
              </div>
              {v.what && <div style={{ fontSize: 12, color: 'var(--text-sub)', marginTop: 2, lineHeight: 1.5 }}>{v.what}</div>}
              {v.expectedEffect && <div style={{ fontSize: 11, color: '#0369a1', marginTop: 2 }}>기대효과: {v.expectedEffect}</div>}
            </div>
          </label>
        ))}
      </div>
      {error && <ErrorBanner msg={error} />}
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          disabled={busy || checked.size === 0}
          onClick={doApprove}
          style={{
            background: checked.size === 0 ? '#e5e7eb' : '#16a34a',
            color: checked.size === 0 ? '#9ca3af' : '#fff',
            padding: '8px 18px', borderRadius: 5, border: 'none', fontWeight: 600,
            cursor: (busy || checked.size === 0) ? 'not-allowed' : 'pointer', opacity: busy ? 0.6 : 1, fontSize: 13,
          }}
        >
          {busy ? '처리 중…' : `승인 (${checked.size}건 실행)`}
        </button>
        <button
          disabled={busy}
          onClick={async () => { setBusy(true); try { await strategyExecApi.reject(executionId, '운영자 반려'); setDone(true); } catch (e: any) { setError(`반려 실패: ${e?.message ?? e}`); } finally { setBusy(false); } }}
          style={{ background: 'transparent', color: '#ef4444', padding: '8px 18px', borderRadius: 5, border: '1px solid #ef4444', fontWeight: 600, cursor: busy ? 'wait' : 'pointer', opacity: busy ? 0.6 : 1, fontSize: 13 }}
        >
          반려
        </button>
      </div>
    </div>
  );
}
```
- [ ] propose 렌더 분기 교체(`{phase === 'propose' && !onePhase && ceoPlan && (...)}` 블록 위에 v2 우선 분기 추가). v2면 ToolActionPanel, 아니면 기존 ProposePanel:
```tsx
{phase === 'propose' && !onePhase && isV2Execution({ proposed_actions_v2: initialProposedActions, ceo_plan: ceoPlan }) && (
  <ToolActionPanel
    actions={initialProposedActions ?? []}
    executionId={executionId}
    onClose={onClose}
  />
)}
{phase === 'propose' && !onePhase && ceoPlan && !isV2Execution({ proposed_actions_v2: initialProposedActions, ceo_plan: ceoPlan }) && (
  <ProposePanel plan={ceoPlan} executionId={executionId} onClose={onClose} />
)}
```
- [ ] `src/pages/atomic/AtomicConsole.tsx` 모달 호출에 v2 필드 전달:
```tsx
<ExecutionDetailModal
  executionId={detailItem.execution_id}
  initialPhase={detailItem.phase}
  initialCeoPlan={detailItem.ceo_plan ?? null}
  initialProposedActions={detailItem.proposed_actions_v2 ?? null}
  onClose={() => { setDetailItem(null); queryClient.invalidateQueries({ queryKey: ['strategy-feed'] }); }}
/>
```
- [ ] (선택, e2e 시연 진입점) detect/진단 phase 패널에 "v2로 관통(시연)" 버튼 추가(spec S0 run-v2 멱등 트리거를 콘솔에서 시연):
```tsx
<button
  onClick={async () => { setBusy(true); try { await strategyExecApi.runV2(executionId); onClose(); } catch (e: any) { setError(`run-v2 실패: ${e?.response?.data?.detail ?? e?.message}`); } finally { setBusy(false); } }}
  disabled={busy}
  style={{ background: '#7c3aed', color: '#fff', padding: '6px 14px', borderRadius: 5, border: 'none', fontWeight: 600, fontSize: 12, cursor: busy ? 'wait' : 'pointer' }}
>
  ⚡ v2로 관통(시연)
</button>
```
- [ ] (타입체크 + 회귀) `cd ~/hbs-dashboard && npx tsc -b --noEmit` → 에러 0. `cd ~/hbs-dashboard && npx vitest run src/pages/atomic` → 전부 PASS(기존 propose/CEO 경로 불변 — isV2Execution=false면 v2 분기 미진입).
- [ ] (빌드 게이트, CLAUDE.md 필수) `cd ~/hbs-dashboard && npm run build` → 성공.
- [ ] (COMMIT) `cd ~/hbs-dashboard && git add src/pages/atomic/ExecutionDetailModal.tsx src/pages/atomic/AtomicConsole.tsx && git commit -m "feat(atomic-v2): v2 도구액션 승인 패널(CEO 카피 없음)+승인 후 전이+run-v2 시연 버튼 (S7-3/4)"`

---

## Task 16: 최종 회귀 + e2e 체크리스트

**Files:** (없음 — 검증 전용)

> repo: **FastAPI** (`~/FastAPI`) + **hbs** (`~/hbs-dashboard`).

- [ ] (FastAPI 전체 회귀) `cd ~/FastAPI && venv/bin/python -m pytest tests/ -q` → 신규(v2_routing·detection_evidence·hermes_runner·hermes_prompt·analysis_gate·safe_tools·report_gate·pipeline_v2·run_v2_ep·approve_actions·send_report_gate) 전부 통과 + 기존 회귀 0. 특히 test_batch_decisions·test_hermes_dispatch(레거시 경로 불변).
- [ ] (hbs 빌드+vitest) `cd ~/hbs-dashboard && npm run build && npx vitest run src/pages/atomic` → 빌드 성공 + 전 atomic 테스트 PASS.
- [ ] (수동 e2e — glen 트리거) 다음 순서로 라이브 1건 관통:
  1. 마이그레이션 적용: glen 이 prod Supabase에 `migrations/013_pipeline_v2.sql` 적용(proposed_actions_v2·ceo_plan_v2 컬럼).
  2. `ELAYER_PIPELINE_V2_SALES_ENABLED=true` 설정(Railway env, web+worker).
  3. 실 sales execution 1건에 `POST /api/strategy/executions/{id}/run-v2` → 콘솔에 **도구액션 제안**(CEO/슬롯 카피 없음) 표시 확인. phase=`propose_v2`.
  4. 도구액션 선택 후 승인 → `resume_after_approval_v2`가 safe_tools 실행(record_decision·create_task) → 측정(before/after) → `report_gate` 통과 → `synthesized_report` draft.
  5. phase 사다리 `propose_v2`→`report` 확인. orphaned pending / CEO / slot / paperclip 흔적 0 확인.
  6. (발송) ENABLED OFF·SANDBOX 유지 — "신뢰게이트 통과한 draft"까지가 합격선. 실 점주 수신자는 풀 사용자 인증 후(범위 외).
- [ ] (커밋 없음 — 검증 단계. 회귀 통과 로그를 PR 본문에 기록.)

---

## Self-Review notes

사람 리뷰어를 위한 메모(드래프트 조립 시 정규화·판단한 지점):

1. **Celery 래퍼 드롭(ORCH-4).** ORCH.md는 `tasks.elayer_run_v2`/`tasks.elayer_resume_v2` Celery 태스크 + `_approve_one`의 enqueue 분기를 제안했으나, canonical 계약은 "모든 게 sync await"다. → Celery 태스크 전부 삭제, approve 분기는 `await resume_after_approval_v2(...)` 직호출, run-v2 EP도 `await run_analysis_v2(...)`. `app/tasks/elayer_tasks.py`는 이 슬라이스에서 손대지 않는다.

2. **측정 래퍼 위치 이동(S5).** S5.md는 `capture_baseline_for_execution`/`measure_kpi_for_execution`를 레거시 `elayer_dispatch.py`에 두었으나, canonical은 `elayer_pipeline_v2.py`의 `_capture_baseline`/`_measure`로 이동·개명. 본문은 S5 그대로(soft-fail·모듈 속성 호출), 위치/이름만 정규화. test도 `ed.capture_baseline_for_execution` → `v2._capture_baseline`로 갱신.

3. **resume 시그니처 변경.** ORCH.md의 `resume_after_approval_v2(execution_id)`(승인액션을 ceo_plan_v2.selected_actions에서 읽음)를 canonical `resume_after_approval_v2(execution_id, selected_action_ids: list[str])`로 변경. selected_action_ids는 approve EP가 검증해 직접 전달(index-as-string). `_select_actions_by_ids`/`_action_to_params`/`_draft_report` 헬퍼는 ORCH._selected_actions/_draft_report를 정규화해 합성.

4. **report gate seam 통일.** ORCH.md는 `_report_trust_gate` seam(`elayer_report_gate.report_trust_gate` lazy import)을 뒀으나, canonical은 `report_gate.validate_report`를 모듈 속성으로 직접 호출. seam 제거, 모듈명 `report_gate`·함수명 `validate_report`로 통일(S6와 일치).

5. **hermes dept(NOT domain).** ORCH-2 드래프트가 `run_hermes_analysis(agenda, role="ANALYST", domain="sales")`로 호출 — canonical 파라미터는 `dept`. → `dept="sales"`로 정규화. hermes 호출은 `asyncio.to_thread`로 오프로드(blocking SSH).

6. **FE 필드명 proposed_actions → proposed_actions_v2.** S7.md 전반이 `proposed_actions`/`ProposedAction`을 썼으나 canonical은 `proposed_actions_v2`/`ProposedActionV2`. types.ts·v2View.ts·테스트·모달·AtomicConsole 전부 RENAME.

7. **run-v2 EP는 ANALYZE only.** S0.md의 run-v2 EP는 phase=`v2_done` 기록 + `run_v2_sales` 단일 진입점을 가정했으나, canonical은 run_analysis_v2(분석만)만 호출하고 phase 기록은 오케스트레이터가(propose_v2). EP는 phase를 직접 쓰지 않고 결과만 반환. 멱등 가드도 EP가 아니라 run_analysis_v2 내부(already_v2). 테스트의 `phase="v2_done"`/`status="already_v2"` 가정을 propose_v2/already_v2 패스스루로 갱신.

8. **테스트 repo 경로 통일.** S4/S6 드래프트가 `cd ~/fastapi-prod-snap-pipeline`(스냅샷)에서 테스트를 돌렸는데, 라이브 repo `cd ~/FastAPI`로 통일(스냅샷은 읽기전용). pytest 호출도 `python` → `venv/bin/python`(Tech Stack 규약)으로 통일.

9. **safe_tools params 매핑.** ORCH.md resume는 `run_tool(tag, a, ctx)`로 action dict 전체를 params로 넘겼으나, safe_tools required_params(record_decision: verdict/note/scope, create_task: owner/action/due)와 불일치. → `_action_to_params`로 tool_tag별 변환 추가(proposed_action → 레지스트리 required_params). 이는 두 모듈 계약을 잇는 새 글루이며, 본문 코드 외 유일한 합성 로직이므로 리뷰 권장.

10. **검증 못 한 신선도.** 로컬 스냅샷(`~/fastapi-prod-snap-pipeline`)으로 시그니처를 확인했으나, MEMORY의 "로컬 FastAPI는 origin보다 상습 stale" 경고가 있다. 구현 착수 전 `cd ~/FastAPI && git fetch && git log origin/main` 으로 prod=origin/main 최신을 확인하고, `_approve_one` 라인 번호(837/858/867)·feed select·send EP select가 그대로인지 재확인 권장.
