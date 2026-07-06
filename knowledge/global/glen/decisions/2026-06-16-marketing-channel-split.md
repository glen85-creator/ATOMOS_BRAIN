---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: MARKETING 채널 분리 (콘텐츠 초안 슬롯) — 2026-06-16
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# MARKETING 채널 분리 (콘텐츠 초안 슬롯) — 2026-06-16

## 맥락
sales fan-out의 단일 MARKETING 슬롯은 SNS·POP·리뷰를 "제안(actions[])"으로 통합 산출했다. 글렌 결정: 채널별로 분리해 각 채널이 **바로 쓸 콘텐츠 초안**(SNS 게시문·POP 카피·프로모션 메시지·리뷰 운영 콘텐츠)을 생성하게 — 시스템에 없던 ready-to-use 산출물 capability. 원래 MARKETING 슬롯 설계의 C안(보류) 실현.

## 결정 (브레인스토밍)
1. 산출물 = **채널별 콘텐츠 초안**(A안). 분할제안(B)·보류(C) 기각.
2. 채널 4개: SNS·POP·프로모션/재방문·리뷰운영. 글렌이 4개 전부 선택(리뷰 포함).
3. 단일 `sales-marketing` 슬롯 **교체**(coexist 아님).
4. **공유 파라미터화 빌더** 1개(기존 빌더 중복 DRY 개선).
5. **리뷰 채널 ≠ D-REVIEW**: 선제 평판회복 콘텐츠(긍정유도·템플릿), 개별 응대는 D-REVIEW.

## 구현 (subagent-driven, 4태스크)
- **FastAPI PR#17**: `CONTENT_SCHEMA_DOC`(st_uid/channel/content_drafts[{format,draft,usage_note}]/rationale) + `_SALES_CHANNELS` 레지스트리 + `build_sales_channel_issue(execution, issue_kind)`(build_sales_marketing_issue 교체). routing sales = ANALYST(floor)+RESEARCHER+4채널. dispatch ISSUE_BUILDERS에 채널 kind per-kind 래퍼(`_k=k` late-binding 회피). config 변경 0(ELAYER_SALES_MARKETING_ENABLED 재사용)·ATOMOS_BRAIN/VPS 0.
- **hbs-dashboard PR#12**: spec+plan+ROADMAP.
- **FastAPI PR#19**: dispatch task `time_limit` 900→1800s(E2E서 발견한 6슬롯 초과 픽스).
- 2단계 리뷰 + 최종 교차리뷰(import OK·kind 3중 일관·late-binding 검증). 픽스: C1(import, Task3)·m4(st_uid)·stale 주석.

## 라이브 E2E (실매장 ST-ET-CR-0001, 3회 — 디버깅 가치 큼)
1. **첫 run**: 0 agent_run 스톨. PR#17 배포 직후 Celery worker 사이클 transient(글렌 확인: 인프라 정상).
2. **재시도**: 게이트 GO 정상 기록(worker·VPS·CEO 다 작동), 그러나 **6슬롯 fan-out이 dispatch task 900s time_limit 초과 → 기록 전 hard-kill**. 원인: 게이트(~6분)+슬롯 poll, 그리고 **6슬롯 중 4개가 동일 ATOMOS_MARKETING 에이전트**라 직렬·idle/paused 경합. (spec에 ⚠️로 적어둔 리스크가 실제로 터짐.)
3. **time_limit 900→1800(PR#19) 후 완주**: 게이트 GO→ANALYST·RESEARCHER·MARKETING(POP·프로모션) success→CEO 합성(direct)→`synthesized_report` **4 deliverables + 실 점주 메시지**(5,000원 쿠폰·적립 이벤트). **프로모션 채널이 진짜 카카오톡 쿠폰 문구를 생성**(`[국수나무] 5,000원 할인 쿠폰, 2만원 이상, ~6/30`) = **채널 분리 가치 입증**.

## ⚠️ 라이브서 드러난 신뢰성 갭 (후속 — 머지 기능 자체엔 영향 없음)
- **(a) 동일 에이전트 직렬·경합**: 4채널이 ATOMOS_MARKETING 1개 에이전트 → 2/4만 완료(SNS·리뷰는 미완·기록無 pending, idle/paused 경합+직렬). asyncio.gather가 FastAPI측만 병렬화, Paperclip 에이전트는 단일. → 후속: **슬롯별 Celery task** or **채널별 전용 에이전트**.
- **(b) 슬롯 콘텐츠 캡처 부실**: 에이전트 CONTENT JSON이 `{"status":"done"}`(엉뚱한 코멘트)나 `{"raw":...}`(parse_warn, content_drafts 미파싱)로 저장. 슬롯 경로가 느슨한 `_poll_agent_comment`+extract_json_block 사용. 게이트는 `_poll_ceo_verdict`(순수JSON·최신 valid-schema)로 이미 해결 → 후속: **슬롯 경로에 게이트식 캡처 적용**.
- **time_limit 1800s는 band-aid**: (a) 직렬은 미해결, 근본은 슬롯별 task.

## 교훈
- **E2E가 단위테스트·리뷰가 못 잡는 런타임 한계를 잡는다.** import/unit/최종리뷰 다 통과한 코드가 6슬롯 동일에이전트 fan-out + 900s task_limit에서 깨짐. spec의 ⚠️ 모니터링 메모가 현실화.
- **채널 분리 가치는 실재**(프로모션 채널 실 쿠폰 문구), 단 **다슬롯 동일에이전트 fan-out·콘텐츠 캡처 신뢰성**이 프로덕션 선결.
- 코드는 정상, 막힌 건 운영(time_limit·에이전트 병렬성). 디버깅: 0 agent_run + 게이트는 실패도 기록한다는 사실 → "기록 전 죽음" 추론 → time_limit 확인.

## 상태
채널 분리 라이브·`ELAYER_SALES_MARKETING_ENABLED` ON, time_limit 1800s. 메커니즘·가치 입증, 신뢰성 갭(동일에이전트·캡처)은 후속 슬라이스. 다음 후보: 슬롯 신뢰성(슬롯별 task+게이트식 캡처)·FINANCE/SCM 정식 슬롯·실발송·CEO 교차도메인 분해. ADR 연속 [[global/glen/decisions/2026-06-15-ceo-dynamic-decomposition]].

## 관련

- [[global/glen/decisions/2026-06-15-ceo-dynamic-decomposition]]
- [[global/glen/decisions/2026-06-15-sales-marketing-slot]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-16-marketing-channel-split-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-16-marketing-channel-split.md
