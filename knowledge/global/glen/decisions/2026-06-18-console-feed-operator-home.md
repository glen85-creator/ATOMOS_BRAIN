---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 콘솔 재설계 #2 — 피드/상황실 → 운영자 홈(결정 큐)"
tags: [domain/atomos, domain/frontend, domain/backend, status/done, priority/high, glen-wiki, type/decision]
---
# ADR: 콘솔 재설계 #2 — 피드/상황실 → 운영자 홈(결정 큐)

## 맥락

북극성 콘솔 재설계 5 surface 중 **#2**(#1 2-페이즈 생명주기 코어는 완료 [[global/glen/decisions/2026-06-17-console-redesign-2phase]]). 현 콘솔의 상황실+피드는 **2-페이즈 이전 모델**: feed EP가 `status` 3버킷(자동완료·실행중·예외승인)이라 #1이 도입한 6상태 `phase`와 두 관문(①제안 ②발송)을 모르고, `ExecutionCard`에 **인라인 블라인드 승인** 버튼(헌장이 금지)이 있었다.

## 결정 (brainstorming)

- **spine = 결정 큐 우선**: "지금 내 결정 필요"가 전면. 매장·6상태는 보조 렌즈.
- **단일 운영자 홈**: 상황실+피드 → 홈 하나로 통합(피드 탭 폐기).
- **큐 = 두 관문만 엄격히**: ①제안 승인(propose/detect pending) + ②보고 발송(report 미발송). 실패는 큐 밖 ⚠주의 섹션.
- **접근 A (BE phase-인지 EP)**: `GET /api/strategy/feed`를 SQL RPC `get_atomic_feed` → Python phase-인지로 재작성.

## 구현

- **BE**: 순수 `app/services/feed_classify.py`(`classify_feed_row`·`sort_decision_queue`, 우선순위 send>approve>attention>in_progress>done, /tmp 테스트). EP → **4그룹**(decision_queue/in_progress/recent_done/attention) + `FeedItem.gate`('approve'|'send')·`store`. migration 없음.
- **FE**: 신규 `OperatorHome`(슬림 요약 + 결정 큐 히어로 + 매장 필터 + 보조 섹션)·`DecisionCard`. `ExecutionCard` 일반화(인라인 액션 제거). 큐 카드 [열기] → #1 `ExecutionDetailModal`(무변경) 해당 관문 진입. 모달 닫기 시 `['strategy-feed']` invalidate. `ActivityFeed`·`ApprovalWorkbench`·`MiniActivity`·`SituationOverview` + 고아 `ApprovalDetail`·`useExecutionActions` 삭제(−243줄).

## 2단계 리뷰가 잡은 것

- **BE 코드품질**: (1) 재작성이 `is_auto`/`latest_decision_type`/`final_kpi_data`를 누락 → audit_log 배치로 복원. **is_auto는 `was_auto` 의미**(action_type=approve & decision_type=auto)로 — latest-only는 finalized auto-execution의 배지를 놓침(migration 004 주석 근거). (2) kpi_snapshot final이 복수 가능 → snapshot_at.desc 첫-seen으로 결정론화(stale delta 방지).
- **FE 코드품질**: (1) 모달이 처리 후 큐를 새로고침 안 함 → onClose에 `['strategy-feed']` invalidate(스펙 §4.4). (2) 고아 dead code 제거.

## 라이브 E2E서 발견·수정

배포 후 EP가 4그룹·gate 태깅(send 35/approve 1)은 정상이나 **store 라벨이 전부 빈값**. 근본: sales 실행은 top `st_uid`가 null이고 매장 식별자가 `trigger_context.st_id`(`ST-GG-RD-0026` 포맷). `stores` 테이블엔 st_id 컬럼 없음 → **`store_master_v2(st_id→store_name)`** 로 보강(FastAPI#34). review 등 top st_uid 보유 도메인은 `stores.st_name` 유지. 매장 라벨/필터 복구(35/35).

## 배포

FastAPI PR#33(EP)·#34(store-fix)·hbs PR#40(FE)·#41(docs). 전부 GCM API로 PR 생성+머지. Railway/Vercel 자동 배포. E2E: 4그룹 분류·gate 태깅·store 라벨·1-phase/legacy 무충돌 라이브 확인.

## 교훈

- **공유 repo 함정**: `~/hbs-dashboard`·`~/FastAPI`는 병렬 P4 세션이 활성 사용 중. 직접 편집/커밋하면 그들 브랜치에 내 커밋이 올라가는 사고 발생(실제로 spec 커밋이 feat/p4-phase15-fast-upload에 올라가 cherry-pick으로 복구). **반드시 워크트리(off origin/main)에서 작업·커밋**.
- **식별자 위치 함정**: 도메인마다 매장 식별자 위치가 다름(sales=trigger_context.st_id / review=top st_uid). 피드 같은 도메인-횡단 집계는 다중 소스 폴백 필수.
- 어드버서리얼 2단계 리뷰가 단독 구현이 놓친 contract 회귀(is_auto)·UX 갭(큐 새로고침)을 잡음.

다음: 콘솔 재설계 #3 감지 · #4 측정/회고/학습 · #5 발송/채널.

## 관련

- [[global/glen/decisions/2026-06-17-console-redesign-2phase]]
- [[global/glen/decisions/2026-06-18-agent-result-posting-file-python]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/superpowers/specs/2026-06-18-console-redesign-feed-situation-design.md
