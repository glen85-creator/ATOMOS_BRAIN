---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: POS 매출 마감(sales_closing) 과소수집 복구 + 재발 방지"
tags: [domain/hbs-dashboard, domain/pos, domain/data-integrity, status/active, type/adr, glen-wiki, type/decision]
---
# ADR: POS 매출 마감(sales_closing) 과소수집 복구 + 재발 방지

## 맥락
글렌이 "매출 비는 날짜/덜 받아진 케이스 점검 가능?"을 물었고, 증거 기반 조사 결과 **만성 과소수집**을 발견. 대시보드·`sales_closing_monthly`·감지·KPI가 전부 `sales_closing.rep_sales_amount`를 읽으므로 하류 전체가 오염(감지 근거성 직격).

## 근본 원인 (코드 추적 + 라이브 프로브로 확정)
POS 일별수집 4 API: BS(영수증)·GSS(품목)·SPT(결제)·**SC(마감 요약)**. SC는 **POS 점주가 "마감" 확정해야 값이 차는 지연형**. daily 02:00(D-1) 또는 당일 조기 수집 시점에 미마감이면 SC가 **0/부분을 정상(rtn000)으로 반환** — 영수증·결제(실시간)는 상대적으로 채워짐. 게다가 재수집 경로가 못 고침: `daily_sync`=행 없는 날만, `sync_date_range(bulk)`=bills+items 있으면 skip → **0/부분 마감 영구 고착**.

## 스코프
90일 기준 `마감 < 영수증합(1%↑)` = **2,656 store-day · 147매장 · ≈5.7억** 과소. 거의 매일 5~10개 매장 산발 = 만성.

## 핵심 결정
1. **복구 = 재수집(`sync_daily_sales` 4 EP 전체)만.** derive(상세서 산출) **불채택** — 프로브로 망가진 날은 상세도 부분임을 확인(구로 6/18: 마감 0→2,244,700, 영수증 136→180건). 재호출만 finalize된 진짜값 복원.
2. **탐지기에 1% 허용오차.** 라이브 검증서 `마감≠영수증` 2,156건 중 절반이 반올림 소차(100~500원)·over(영수증쪽 부족)임을 발견 → `마감 < 영수증×0.99`로 좁혀 양성 제외(2,156→1,617 진짜). 재수집해도 안 고쳐지는 소차의 무한 재플래그 방지.
3. **`sync_service.py` 무수정** — 신규 모듈+RPC+beat+EP만(병렬 P4 세션 충돌 최소).

## 솔루션 (FastAPI#42)
- RPC `find_unreconciled_sales(lookback, include_gaps)` — 마감<영수증×0.99(0·부분) + no_sync 갭.
- `sales_reconcile.py` — 회수액 큰 순·limit·멱등·개별실패격리(`_summarize` 순수).
- `reconcile_tasks.py` `tasks.reconcile_sales`(never-raise) + beat `reconcile-sales-daily` 04:45 KST(refresh_aggregates 05:00·감지 05:30 전).
- `POST /sync/reconcile` 1회 복구 트리거.

## 결과 / 운영
PR#42 머지·배포. 라이브: reconcile 청크가 store-day별 BS→GSS→SPT→SC 재수집→마감=영수증 일치→불일치집합 제거(I22092000005/05-16: 0→2,233,800). 과거 backlog는 **점진적 청크 드레인**(`/sync/reconcile limit200`, 큰금액순, 워커1 점유로 P4 공존), 일일 beat가 최근10일 steady-state. 진행은 `sales_closing`/`api_sync_logs`로 확인.

## 프로세스
systematic-debugging(원인) → brainstorming → spec → writing-plans → subagent-driven(코드 태스크 2단계 리뷰 전부 통과). 환경: 독립클론·`git -C` 절대경로.

## 다음
- backlog 완전 드레인까지 청크 반복(또는 스케줄).
- D: 상시 정합성 점검 surface(불일치·갭·재수집후 잔존 플래그, 감지 근거성 연결) — 후속 spec.
- 메모리 `project_pos_reconcile`.

## 관련

- [[global/glen/concepts/ATOMOS]]
- [[global/glen/entities-technologies/FastAPI]]
- [[global/glen/entities-technologies/Supabase]]
- [[global/glen/entities-organizations/메타시티]]

## 출처(원본)

- raw/meetings/claude-conversations/57256c3e-1a31-49a3-9065-6d95d7d9cd60.md
