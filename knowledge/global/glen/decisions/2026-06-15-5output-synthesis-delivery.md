---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 5산출물 합성 + 점주 리포트 전달 — E층 종착점 (2026-06-15)
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# 5산출물 합성 + 점주 리포트 전달 — E층 종착점 (2026-06-15)

## 맥락
E층 로드맵의 종착점("발송 버튼이 진짜 일하게" — 글렌 최초 문제). 감지→승인→슬롯 fan-out까지는 됐으나 **슬롯 산출물이 DB 적재만 되고 점주에게 전달 안 됨**. 이 슬라이스가 루프를 닫음: 슬롯 산출물(N개)을 **CEO 2차 합성**으로 점주 리포트화 → draft 전달.

## 결정 (브레인스토밍)
1. **범위 = 메커니즘 우선** (현 N슬롯 합성, N에 무관; "5"는 MARKETING 확장 시 자연 달성). 2. **합성 = CEO 에이전트(헌장 2차)** — 게이트 인프라 재사용. 3. **트리거 = 슬롯 완료 직후 자동**(별도 Celery task). 4. **전달 = draft-only 콘솔 리포트 탭**(외부발송 아님). 5. 합성 실패 → **결정론 번들 폴백**. "S3"=Stage-3(전달)이지 AWS S3 아님.

## 구현 (subagent-driven, 7태스크, 머지·배포)
- **FastAPI PR#11**: `elayer_synthesis.py`(build_synthesis_issue·_poll_synthesis·synthesize_execution·번들폴백; 게이트 빌딩블록 재사용, 게이트 파일 미터치) · dispatch gather 후 `tasks.elayer_synthesize` enqueue · `strategy_executions.synthesized_report` jsonb(migration) · `GET /api/strategy/executions/{id}/report` · `ELAYER_SYNTHESIS_ENABLED`. 성공경로 record 실패해도 리포트 유지(C1, 게이트 교훈 재적용).
- **ATOMOS_BRAIN PR#7**: CEO promptTemplate **task-agnostic 일반화**(게이트+합성 공용 — 이슈 본문이 작업 규정). 게이트 재검증 통과.
- **hbs-dashboard PR#6**: ExecutionDetailModal "점주 리포트" 탭(타입·client·hook). build 통과.
- 태스크별 spec+code-quality 2단계 리뷰 + 최종 교차리뷰(15/15 smoke, READY TO MERGE).

## 라이브 E2E (실매장 ST-ET-CR-0001 국수나무 노량진점)
approve → gate **GO**(fallback z) → **2 슬롯 완료**(ANALYST 실진단+RESEARCHER 외부요인) → **자동 합성 트리거** → 합성 CEO 타임아웃 → **번들 폴백** → `synthesized_report` 저장(deliverables 2·actions 8) → `GET /report` status=synthesized 조회 OK. **전 체인 end-to-end 입증.**

## 교훈
- **슬롯 이슈 빌드는 REAL store 필수.** `build_sales_issue`가 `st_id`→`pos_st_uid`(store_master_v2) 매핑 실패 시 None → 슬롯 산출물 0 → 합성 미발동. 첫 E2E가 가짜 store라 실패 → 실매장으로 재실행해 통과. **게이트는 evidence로만 판단해 store 불필요**(가짜 store에서 게이트만 떠 오해 유발). E2E seed는 항상 실데이터 정합성 확인.
- **CEO가 게이트+합성 둘 다 → 연속 부하 → 둘 다 타임아웃→폴백 흔함.** 폴백이 항상 유효 결과 보장(게이트=통계, 합성=번들). clean CEO 캡처는 비결정. agentic vehicle의 일관된 신뢰성 특성.
- **hbs-dashboard는 병렬 세션과 공유** — 정리 중 `git checkout main`이 병렬 세션 WIP(`feat/store-crud-master`·StoreMasterV2 미커밋)에 막혀 중단(다행). **공유 repo는 git reset/checkout 금지, 워크트리 off origin/main으로 작업.**

## 상태
E층 종착점 라이브·ON. draft-only(외부발송 아님). 다음: CEO clean synth 신뢰성(게이트·합성 부하분리)·MARKETING 슬롯 추가(진짜 5산출물)·실제 발송(needs_external). 보드에 E2E 게이트/슬롯/합성 이슈 잔류(403→UI 정리). ADR [[global/glen/decisions/2026-06-15-ceo-gate-v1-flag-off-harden]] 연속.

## 관련

- [[global/glen/decisions/2026-06-15-ceo-gate-v1-flag-off-harden]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-15-5output-synthesis-delivery-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-15-5output-synthesis-delivery.md
