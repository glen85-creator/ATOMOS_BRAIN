---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: HBS Dashboard
tags: [status/active, domain/food-franchise, domain/b2b-saas, glen-wiki, type/project]
---
# HBS Dashboard

## 개요

[[global/glen/entities-organizations/HBS]]가 자체 운영하는 외식 프랜차이즈 운영 SaaS의 **프런트엔드**. 국수나무·청년38국수 등 6개 브랜드 287매장의 POS + 배달 플랫폼 통합 매출 분석 + 전략 실행 시스템. B2C(점주 도구) → B2B(본사 통합 관제 SaaS) 전환 중. 백엔드는 [[global/glen/entities-projects/HBS-FastAPI]].

## 아키텍처

```
[프런트 (Vercel)] ── HTTPS ──→ [FastAPI (Railway)] ── service_role ──→ [Supabase Postgres]
```

- 단방향 호출. 프런트가 Supabase 직접 접근 **금지** (service_role 키 노출 방지)
- 모든 API는 `src/api/client.ts` 경유
- 응답 타입은 `src/api/types.ts`에 백엔드 스키마와 1:1 정의

## 기술 스택

- [[global/glen/entities-technologies/React]] 18 + [[global/glen/entities-technologies/Vite]] + TypeScript
- TanStack Query (서버 상태) + Zustand (클라이언트 상태)
- Tailwind CSS + shadcn/ui + Recharts + Lucide
- React Router v6 + Axios
- [[global/glen/entities-technologies/Vercel]] 배포

## 주요 페이지 (39개, FEATURES.md 기반)

- 운영: `/dashboard`, `/channel`, `/menu-engineering`, `/delivery`, `/simulator`
- 전략: `/dashboard/strategy-v2`, `/strategy-timeline`
- 본사 관제: `/dashboard/hq`, `/brand-kpi`, `/store-grading`, `/store-alerts`
- 시뮬레이션(2026-06): `/dashboard/hq-sim`(본사 전사 단가 인상 시뮬), `/dashboard/price-sim`(점주 단가비교), `/dashboard/hq-sim-advanced`
- AI 콘솔(2026-06): `/dashboard/atomic`(ATOMIC 콘솔 — `strategy-v2`/`strategy-hub`/`gap` redirect)
- 운영 도메인 6: `/sourcing`, `/hq/strategy`, `/sv`, `/menu-rd`, `/franchise`, `/brand-development`
- 마스터 v2: `/master/v2/{codes,suppliers,ingredients,recipes,stores,deployments,menu-costs,supply-chain,unmapped}`
- 설정: `/admin/*` (목표·채널·배달계정·외부연결·인력비용·고정비·권한)

## 핵심 인물

- [[global/glen/entities-people/glen]] (1인 개발 + LLM 보조)

## 주요 결정사항 (ADR)

- 프런트 ↔ 백엔드 분리 (`HBS_ARCHITECTURE_DECISION_FRONTEND_BACKEND_SEPARATION.md`)
- Atomic v1.1 — Nous Research Hermes Agent 전면 도입, 자체 12 워커 풀 폐기 → Skill로 이식 (ATOMIC_ASSISTANT_DESIGN.md v1.1, 2026-05-17)
- B2C → B2B 전환 로드맵 + Pivot Gate 1/2/3 확정 (2026-05-07)
- 권한 매트릭스 38 메뉴 × 7 역할 v1.0 (2026-05-17)

## 노트

- 환경: `VITE_API_URL` (로컬 `http://localhost:8000` / 프로덕션 `https://fastapi-production-3c6e.up.railway.app`)
- DB: Supabase 프로젝트 `nmeiydjbusrtyckrsyai` (`HBS_POS_DATA_HUB`, ap-southeast-1)
- main 브랜치 push → Vercel/Railway 자동 배포
- **주 작업 환경: WSL/우분투 `/home/glen_85/hbs-dashboard`** (2026-05-30 이전, D드라이브는 pull 전용 백업). 상세: [[global/glen/decisions/2026-05-30-dev-env-to-wsl-ubuntu]]
- 본 볼트에서의 위치: `raw/docs/hbs-dashboard/` + `raw/meetings/claude-conversations/`

## Cost Hub (Phase 0) — 2026-05-30 FastAPI 전환 완료

- 페이지 3종: `/dashboard/cost-hub`(통합 손익), `/admin/utility-bills`(공과금), `/admin/vendors`(벤더 D-day). 커밋 `59d0f0b`(2026-05-28). 상세: 2026-05-28-cost-hub-phase0
- DB 실적용 확인: `utility_bill_entry`·`vendor_contract` 테이블, `store_targets.target_utility_rate/target_opex_rate` 컬럼, RPC `get_store_monthly_pnl(p_st_id, p_month)` 모두 존재·동작. 시드(공과금 3 + 벤더 7, 시범매장 ST-SE-RD-0015) 적재됨.
- ✅ **아키텍처 규칙 위반 해소**: cost 페이지의 Supabase 직접 호출 6곳을 FastAPI `/api/cost/*` 9개 엔드포인트 경유로 전환(백엔드 `415314a` Railway 배포 완료, 프런트 Vercel 배포 대기). 상세: 2026-05-30-cost-hub-fastapi-migration
- ⚠️ RPC 출력에서 **인건비·고정비가 0** (원천 데이터 누락 의심), COGS는 실측 아닌 비율(0.35 fallback) 기반 — Phase 1에서 정교화 예정.
- ⚠️ **보안 부채(Phase B)**: 백엔드 cost 엔드포인트에 인증/scope 검사 없음(service_role이 RLS 우회). `app/core/auth.py` JWT+scope 403 별도 티켓.

## ATOMIC 콘솔·엔진 + HQ 시뮬 (2026-06-08 갱신)

- **ATOMIC 콘솔·엔진(ATOMOS S0~S3 구현)**: 전략허브 V2 → `/dashboard/atomic` 전면개편, 실행루프(approve/finalize/cost/rollback/gate-check/autonomy-policy) 실동작, S0 엔진(Paperclip+Hermes, X-Engine-Token 게이트)·S1 부진매장·S3 COGS 감지. 상세: 2026-06-08-hbs-atomic-console-engine-impl. ADR: [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]] · [[global/glen/decisions/2026-05-30-strategy-supabase-to-fastapi-phase1a]]
- **본사 단가 인상 전사 시뮬 + 점주 단가비교**: `/dashboard/hq-sim` 3단 구조(전사 요약→매장 그리드→메뉴 드릴다운), `/dashboard/price-sim` 신설, 월별 사전집계 캐시(qty RPC 4.9s→0.18s). 상세: 2026-06-08-hbs-hq-sim-pricing. ADR: [[global/glen/decisions/2026-06-07-hq-sim-monthly-preaggregation-cache]]

## ATOMIC 콘솔 후속 (2026-06-09)

- **상황실(S2)·자율성 규칙(S3-A)·감지 슬라이스(D-REVIEW·D-COST)·감지 탭 UI 개편**을 순차 구현·배포. 콘솔 탭이 🎛상황실(기본)·🔔피드·🔍감지·📊회고로 정착. 🔍감지 탭은 4 도메인(매장·COGS·리뷰·비용)을 **요약 카드 그리드 + 클릭 드릴**로 개편(`StoreStatusPanel` → `DetectionPanel` + `UnderperformingPanel` + `detectionSummary`, 감지로직/EP 무변경). 상세: 2026-06-09-hbs-atomic-detect-ui-redesign · 2026-06-09-hbs-atomic-s2-situation-room · 2026-06-09-hbs-atomic-s3a-autonomy-rules · 2026-06-09-hbs-atomic-s3-review-detection · 2026-06-09-hbs-atomic-s3-cost-detection
- **감지 → 실행 연결 (2026-06-09)**: 감지 행 [+제안] → `POST /api/strategy/propose`(dedup_key 멱등) → proposed execution → 피드 '예외 승인 대기'/승인 워크벤치. detectProposal·ProposeModal·ProposeButton. store/cost는 st_id≠st_uid라 trigger_context.st_id로 격리. prod curl 검증 완료. 상세: 2026-06-09-hbs-atomic-detect-to-execution
- **기회/우수사례 전파 (2026-06-09)**: 감지 탭 5번째 🌟기회 카드(매출 성장 상위 우수 매장, underperforming 쿼리 공유) → 행 전파 → PropagateModal(대상 부진 선택) → best_practice_propagation(SC-BP-001, 시드) 제안 → 동일 propose 루프/피드. 위협만 보던 감지를 "잘되는 패턴 전파"까지 확장(인과는 실행 analyst). prod 검증 완료. 상세: 2026-06-09-hbs-atomic-opportunity-propagation
- **감지 확장성 + ATOMOS 설정 화면 (2026-06-09)**: 부진/기회 RPC를 sales_bills 풀스캔(6s, 타임아웃 위험)→sales_closing_monthly 캐시(9.7ms) + Celery 05:00 자동 갱신. `/admin/atomos` 신규 설정 페이지 — 감지 임계값 편집(detection_settings, 감지 EP authoritative)·캐시 상태/지금갱신·자율성 콘솔 링크. 상세: 2026-06-09-hbs-detection-scaling-cache-refresh · 2026-06-09-hbs-atomos-settings-screen

## 비용 수집·재료 매핑·매장별 원가 (2026-07-06)

Cost Hub Phase 0(2026-05) 이후 비용/원가 전면 확장. 상세 ADR: [[global/glen/decisions/2026-07-06-cost-mail-to-menu-cost]]

- **비용 메일 수집**: Resend Inbound(`*@atomos.im`) → `cost_transaction`. 쿠팡/식봄/네이버페이 파싱 + 쿠팡 품목 자동분류(식자재/소모품/비품)·전체품목 `line_items`. 메일함·거래검토 화면.
- **비용·손익 통합 허브**: `/dashboard/cost-hub`를 탭(손익요약·거래검토·계약·고정비공과금·인건비고용)으로. 메일함(`/admin/mail-inbox`)·메일계정·목표는 성격 달라 분리.
- **실거래→레시피 재료 매핑 + 채널단가**: `/master/v2/ingredient-mapping` — **매핑=전사**(`ingredient_alias`)·**가격=매장별**(`supply_chain_record`). 매장 실효단가(전채널 수량가중평균)·채널비교(물류 vs 쿠팡)·메뉴원가 **표준 vs 실제** overlay(`StoreMenuCosts`). 마이그 019~022(매핑/실효단가 RPC·EP `/api/master/ingredient-mapping/*`).
- **메뉴원가 정합 정리(구로)**: 이상 원가는 대부분 가격 아닌 **데이터 정합**(자동백필 단가·레시피 오연결·미사용 배포). **고원가 17→3·평균 원가율 79.4%→30.1%**. WMS 실매입=ground truth.
- **손익 구성 시작**: 임대계약서 OCR 판독 → 계약(`vendor_contract`)+월 고정비(`fixed_cost_entry`, 임대료 280만) 등록. ⚠️ 인건비·관리비·공과금 미입력(진행중) → line 115의 "인건비·고정비 0" 부분 해소 착수. 문서 OCR 자동수집(임대→관리비→정수기→공과금, Claude비전+검토후등록)은 방향 확정·미구현.
- ⚠️ **보안 부채 지속**: 비용/매핑 EP 무인증(service_role RLS 우회). 실데이터/공개 전 인증 선결.

## DB 마이그레이션 인덱스

`raw/docs/hbs-dashboard/migrations/` 의 Supabase 마이그레이션 정본 목록(개별 요약 대신 인덱스로 추적). 미래 일자(06-15~)는 Strategy V2 Phase 1용으로 선작성된 파일.

| 일자 | 파일 | 내용 |
|---|---|---|
| 2026-05-08 | 2026-05-08-organization-and-scope.sql | B2B 멀티테넌트 기반 — 조직→브랜드→매장 3단계 계층(`organization_master`) + 계정별 scope(`user_scope`). 데이터 모델만(RLS는 추후). |
| 2026-05-14 | 2026-05-14-ingredient-mapping-pipeline-v2.sql | 식재료 매핑 자동화 파이프라인 v2 — 5단계(큐 적재→추정 매핑→신규 IG 생성→역동기화→백필). `auto_match_unmapped()` cron, idempotent. |
| 2026-05-17 | 2026-05-17-rls-comprehensive-policies.sql | 전체 public 테이블 RLS 정비(90 활성 / 18 완전차단 / 72 정책). super_admin 전체 접근, service_role 우회. |
| 2026-05-17 | 2026-05-17-hermes-integration.sql | Nous Hermes Agent 도입 스키마 보강 — `agent_run`에 `via_oauth`/`chain_depth`/`parent_request_id` + skill_chain. |
| 2026-05-28 | 2026-05-28-cost-hub-phase0.sql | Cost Hub Phase 0 — `utility_bill_entry`·`vendor_contract` + `store_targets` 2컬럼 + RPC `get_store_monthly_pnl` + 시드. 요약: 2026-05-28-cost-hub-phase0 |
| 2026-06-15 | 2026-06-15-phase1-tables.sql | Strategy V2 Phase 1 — 8 신규 테이블(`strategy_scenario`/`strategy_trigger`/`strategy_step_log`/`strategy_cost`/`kpi_snapshot`/`agent_run`/`strategy_learning`). |
| 2026-06-15 | 2026-06-15-phase1-rls.sql | Strategy V2 Phase 1 테이블 RLS 활성화 + 정책. |
| 2026-06-15 | 2026-06-15-phase1-seed.sql | Strategy V2 시나리오 시드(SC-SR-001 매출 급락 종합 대응 등). |
| 2026-06-22 | 2026-06-22-sales-watch-fn.sql | Sales Watch 감지 함수 `detect_sales_anomalies` — 지역기준 -25%×4일 AND 자기기준 -20%×3일. |
| 2026-06-29 | 2026-06-29-kpi-fn.sql | Phase 1 KPI 집계 함수 `compute_kpi_for_store`(매출 중심, Phase 2+ 14종 확장 예정). |

## 관련

- [[global/glen/entities-projects/HBS-FastAPI]]
- [[global/glen/entities-organizations/HBS]]
- [[global/glen/entities-people/glen]]
- [[global/glen/concepts/ATOMOS]]
- [[global/glen/concepts/Strategy-V2]]
- [[global/glen/concepts/Olympus-Console]]
- [[global/glen/decisions/2026-05-30-dev-env-to-wsl-ubuntu]]
- [[global/glen/decisions/2026-05-30-strategy-supabase-to-fastapi-phase1a]]
- [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]
- [[global/glen/decisions/2026-06-07-hq-sim-monthly-preaggregation-cache]]
- [[global/glen/decisions/2026-07-06-cost-mail-to-menu-cost]]

## 출처(원본)

- raw/docs/hbs-dashboard/root/PROJECT_CONTEXT
- raw/docs/hbs-dashboard/root/README
- raw/docs/hbs-dashboard/root/CLAUDE
- raw/docs/hbs-dashboard/docs/BUSINESS_PLAN
- raw/docs/hbs-dashboard/docs/ROADMAP_B2C_TO_B2B
