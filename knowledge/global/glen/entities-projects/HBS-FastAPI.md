---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: HBS FastAPI
tags: [status/active, domain/food-franchise, domain/backend, glen-wiki, type/project]
---
# HBS FastAPI

## 개요

[[global/glen/entities-projects/HBS-Dashboard]]의 백엔드 API + 데이터 파이프라인. POS(메타시티) + 배달앱(배민/쿠팡/요기요) 매출 수집 + Supabase 적재 + 대시보드용 집계 API를 제공.

## 아키텍처

- [[global/glen/entities-technologies/FastAPI]] (Python 3.13) + Celery 수집 파이프라인
- [[global/glen/entities-technologies/Railway]] 배포
- [[global/glen/entities-technologies/Supabase]] (Postgres 17) — 프로젝트 `nmeiydjbusrtyckrsyai`
- 프로덕션 URL: `https://fastapi-production-3c6e.up.railway.app`
- 로컬: `D:\WORK\HBS\FastAPI\`

## 기술 스택

- [[global/glen/entities-technologies/FastAPI]] + Celery (수집)
- Anthropic Claude Haiku (리뷰 답변 생성, 선택적)
- POS 하이픈 API (METACITY), 배민/쿠팡/요기요 하이픈 API
- Vercel AI Gateway (Strategy V2 Phase 1)
- Ollama Cloud Qwen 3 (저비용 분류 작업)

## 핵심 모듈

- `app/services/sync_service.py` — 하이픈 API 호출 (수정 금지, 데이터 파이프라인 안정성 최우선)
- `app/tasks/sales_tasks.py` — Celery POS 수집 태스크
- `app/api/routes/admin_master.py` — CRUD + 엑셀 업로드 + 매장 배포 API
- `app/api/routes/dashboard.py` — 대시보드 집계 API (+ `/underperforming` 부진매장, `/cogs-alerts` COGS 감지)
- `app/api/routes/hq_sim.py` · `hq_sim_p1h.py` · `hq_sim_p2h.py` — 본사 전사 단가 시뮬(`/api/hq/sim/aggregate`·`store-menus`, BOM 대체·scenario+RLS). 상세 2026-06-08-hbs-hq-sim-pricing
- `app/api/routes/sim.py` — 점주 채널가 공헌이익 시뮬(`POST /api/sim/menu-price`)
- `app/api/routes/strategy.py` — 전략실행 루프(approve/finalize/cost/rollback/gate-check/autonomy-policy·feed·timeline) + `POST /propose`(감지→제안, dedup_key 멱등, 무인증·디퍼드). 상세 2026-06-09-hbs-atomic-detect-to-execution
- `app/api/routes/atomic_engine.py` — ATOMOS 엔진 표면(prefix `/api/atomic/engine`, X-Engine-Token 게이트, store-kpi/executions/propose). 상세 2026-06-08-hbs-atomic-console-engine-impl
- `app/api/routes/cost.py` — 통합 손익·인건비·고정비 21 EP

## 주요 환경변수

- `SUPABASE_URL` = `https://nmeiydjbusrtyckrsyai.supabase.co`
- `SUPABASE_SERVICE_KEY` (service_role, 노출 금지)
- `ANTHROPIC_API_KEY` (선택)
- POS·배달 API 자격증명

## 주요 결정사항 (ADR)

- POS 수집 코드(`sync_service.py`, `sales_tasks.py`) 수정 금지 — 안정성 최우선
- `v_menu_engineering`, `v_delivery_diagnosis` view는 대시보드 의존 — 스키마 변경 시 동시 갱신
- 전략실행 Supabase 직결 → FastAPI 경유 전환(Phase 1a/1b) — [[global/glen/decisions/2026-05-30-strategy-supabase-to-fastapi-phase1a]]
- ATOMIC 엔진 = Paperclip(껍데기) + Hermes(슬롯 두뇌) 거버넌스 분할 — [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]
- HQ 시뮬 월별 사전집계 캐시 전환 — [[global/glen/decisions/2026-06-07-hq-sim-monthly-preaggregation-cache]]

## ⚠️ 운영 필수 절차

- **POS(`sales_items`) 적재 후 반드시 `SELECT hq_sim_refresh_cache();` 실행** — 미실행 시 HQ 시뮬 수량 stale(영속 캐시 미갱신). 자세히: [[global/glen/decisions/2026-06-07-hq-sim-monthly-preaggregation-cache]]

## 노트

- 본 볼트에서는 백엔드 docs를 별도로 적재하지 않음 (필요 시 추가 인제스트)
- main push → Railway 자동 배포

## 관련

- [[global/glen/entities-projects/HBS-Dashboard]]
- [[global/glen/entities-organizations/HBS]]
- [[global/glen/entities-technologies/FastAPI]]
- [[global/glen/entities-technologies/Supabase]]
- [[global/glen/entities-technologies/Railway]]
- [[global/glen/decisions/2026-06-16-store-master-data-conventions]]
- [[global/glen/decisions/2026-06-07-hq-sim-monthly-preaggregation-cache]]
- [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]
- [[global/glen/decisions/2026-05-30-strategy-supabase-to-fastapi-phase1a]]

## 출처(원본)

- raw/docs/hbs-dashboard/root/PROJECT_CONTEXT
