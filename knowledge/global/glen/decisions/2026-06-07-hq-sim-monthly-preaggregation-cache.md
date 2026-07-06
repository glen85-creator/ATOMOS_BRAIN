---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: HQ 시뮬 집계를 월별 사전집계 캐시 + jsonb RPC로 전환"
tags: [domain/hbs-dashboard, domain/backend, domain/performance, status/accepted, glen-wiki, type/decision]
---
# ADR: HQ 시뮬 집계를 월별 사전집계 캐시 + jsonb RPC로 전환

## 컨텍스트

본사 단가 인상 전사 시뮬(`POST /api/hq/sim/aggregate`)은 `sales_items` 101만행을 전 매장에 걸쳐 매 요청 집계해야 했다. 이 실시간 집계가 Supabase `statement_timeout`(8s)을 초과해 500 오류를 유발했고(qty RPC 약 4.9s 이상), `menu_cost_master` 조회도 PostgREST `max-rows` 1000 캡 때문에 약 6왕복 페이징이 필요했다. 본사 화면은 첫 진입 즉시 전사 KPI가 떠야 하는 요구가 있었다.

## 결정

`sales_items` 실시간 집계를 폐기하고 **월별 사전집계 캐시 테이블 + jsonb RPC**(`hq_sim_menu_qty`·`hq_sim_complete_months`·`hq_sim_store_pos`)로 전환한다. `menu_cost_master` 페이징은 `hq_sim_cost_rows` jsonb RPC 1회 호출 + `asyncio.gather` 2-wave 병렬로 대체한다. 매출/객수는 `sales_closing`(rep_sales_amount/count) + `delivery_orders`(actual_amount/건수)로 정정해 종합 대시보드와 일치시킨다.

캐시는 영속 테이블이므로 **POS(`sales_items`) 적재 후 반드시 `SELECT hq_sim_refresh_cache();`를 실행**해 재계산한다(운영 필수 절차). 마이그레이션: `2026-06-07-hq-sim-{qty-rpc,monthly-cache,pos-revenue,add-delivery-revenue}.sql`, `-hq-sim-cost-rows-rpc.sql`.

## 결과

**긍정**: qty RPC 4.9s→0.18s, aggregate warm 5.2s→2.3s로 `statement_timeout` 회피·첫 진입 즉시 응답(`Layout` prefetch 캐시 적중). 결과값은 실시간 집계와 동일함을 검증.

**부정/리스크**: 캐시가 stale될 수 있어 POS 적재 후 `hq_sim_refresh_cache()` **수동 실행이 운영 필수 절차**가 됨(미실행 시 수량 stale) — 자동화(트리거/크론) 미적용. 완전한 달 판정(distinct 일수 ≥28)에 의존. 캐시 갱신 누락이 데이터 신뢰도 사고로 직결되므로 `USER_MANUAL`에 "관리자 캐시 새로고침 필요" 경고를 명시.

## 대안 검토

- **실시간 집계 유지 + 쿼리/인덱스 튜닝**: 101만행 규모상 8s 벽을 안정적으로 넘기 어려워 기각.
- **트리거 기반 자동 캐시 갱신**: 갱신 누락 위험을 없애지만 적재 파이프라인 결합도·복잡도 상승으로 1차 보류(향후 후보).

## 참고

- 2026-06-08-hbs-hq-sim-pricing (구현 요약)
- 관련 메모리: `project_hq_sim_cache` (Claude Code 자동메모리)

## 관련

- [[global/glen/entities-projects/HBS-FastAPI]]
- [[global/glen/entities-technologies/Supabase]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/superpowers/plans/2026-06-06-hq-integrated-sales-sim-redesign.md
- raw/docs/hbs-dashboard/memory/hq-sales-sim-p0.md
