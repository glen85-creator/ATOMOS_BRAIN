---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 슬롯 신뢰성 (캡처 강화 + 동일에이전트 순차 fan-out) — 2026-06-16
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# 슬롯 신뢰성 (캡처 강화 + 동일에이전트 순차 fan-out) — 2026-06-16

## 맥락
MARKETING 채널 분리 E2E가 두 갭을 드러냄: (a) 동일 MARKETING 에이전트의 4채널이 `asyncio.gather` 동시 디스패치 시 `set_agent_status(idle/paused)` 경합으로 2/4만 완료; (b) 슬롯 콘텐츠 캡처가 느슨한 `_poll_agent_comment`+`extract_json_block`라 `{"status":"done"}` 마커를 오캡처하거나 `{"raw":...}`로 저장(content_drafts 미파싱). 게이트는 `_poll_ceo_verdict`(순수JSON·최신 valid)로 이미 해결.

## 결정 (브레인스토밍)
**스코프 = (b) 게이트식 캡처 + (a') 동일에이전트 순차 fan-out.** 풀 per-slot Celery task(+synth join)·채널별 전용 에이전트는 범위 밖(YAGNI; per-slot task는 동일에이전트 직렬을 안 풀고 join 대공사만 추가). 캡처 검증자는 제네릭(비-trivial JSON dict).

## 구현 (subagent-driven, 4태스크)
- **FastAPI PR#20**: `_poll_slot_output(pc, issue_id, since)`(atomos_bridge, `_poll_ceo_verdict` 미러)+`_is_trivial_marker`(`_TRIVIAL_KEYS={status,done,ok,ack}`); `_dispatch_one_slot` 캡처를 `parsed,raw=_poll_slot_output(...)`로 교체(둘 다 None=타임아웃·parsed dict=구조화·raw=parse_warn); `_group_slots_by_agent`+`_dispatch_agent_group`로 `dispatch_execution`이 agent_uuid별 그룹(다른 에이전트 병렬·같은 에이전트 순차).
- **hbs-dashboard PR#16**: spec+plan+ROADMAP.
- 2단계+최종 교차리뷰. 코드리뷰 픽스: I-1(`_TRIVIAL_KEYS`서 result/message 제외 — 실페이로드 오폐기 방지)·dead Exception 가드 제거·createdAt 가정 주석.

## 라이브 검증 (decompose OFF 강제 6슬롯)
CEO 동적분해가 정상 운영(ON)에선 마케팅 채널을 계속 가지치기해 4채널이 안 떠서, `ELAYER_CEO_DECOMPOSE_ENABLED=false`(임시)로 전체 6슬롯 강제 디스패치:
- **(b) 캡처 입증**: **POP 슬롯이 구조화 `content_drafts` 3개**(`channel=sales-pop`·`is_raw=false`) — 실제 테이블텐트 카드("🌞여름특가! 냉국수 2인 주문 시 →1인 서비스 증정"). 채널분리 E2E서 `{"status":"done"}`로 유실됐던 바로 그 슬롯.
- **(a') race-fix 입증**: SNS→POP가 **순차 실행**(~6분 간격, 경합 없이 clean) — 전 채널분리 E2E의 2/4 경합 드롭아웃이 사라짐.

## ⚠️ 라이브서 드러난 NEW 천장 (별개·후속)
동일 MARKETING 에이전트 4채널 **직렬**(채널당 ~6분=~24분)+게이트가 **1800s dispatch task_limit 초과** → 리뷰·프로모션이 kill 전 미디스패치. race는 풀렸으나 **단일 에이전트 직렬 throughput**이 한계. **단, 이건 decompose OFF(강제 6슬롯)서만 발생** — 프로덕션(decompose ON)은 CEO가 ~1-2채널로 가지치기해 1800s 내 충족. 강제 전채널 throughput은 후속(per-slot Celery task or 채널별 전용 에이전트 or time_limit↑).

## 교훈
- **agentic 비결정이 검증을 계속 우회**: 게이트가 timeout→fallback, CEO가 채널 pruning 등으로 테스트 대상(4채널 fan-out)이 라이브서 안 터짐 → decompose OFF로 강제해야 검증 가능. 비결정 vehicle E2E의 반복 패턴.
- **race ≠ throughput**: 순차 디스패치는 race(경합 드롭아웃)를 푼다(검증됨). 하지만 단일 에이전트 직렬은 throughput 천장이 별도(채널 수×처리시간 vs task_limit). 진짜 병렬은 채널별 에이전트 필요.
- **decompose가 프로덕션 부하 안전판**: CEO 가지치기가 슬롯수를 통제 → 정상 운영은 천장에 안 닿음. ON 유지가 부하 관점서도 옳음.

## 상태
슬롯 신뢰성 라이브·머지. (b)캡처·(a')race-fix 입증. decompose는 검증용 OFF→**ON 복원 요청**. 강제 전채널 throughput은 후속. ADR 연속 [[global/glen/decisions/2026-06-16-marketing-channel-split]].

## 관련

- [[global/glen/decisions/2026-06-16-marketing-channel-split]]
- [[global/glen/decisions/2026-06-15-ceo-gate-v1-flag-off-harden]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-16-slot-reliability-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-16-slot-reliability.md
