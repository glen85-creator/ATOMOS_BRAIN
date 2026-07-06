---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: ATOMIC 엔진 = Paperclip(조직 껍데기) + Hermes(슬롯 두뇌), 거버넌스 분할"
tags: [domain/hbs-dashboard, domain/ai, domain/agent-runtime, domain/architecture, status/accepted, glen-wiki, type/decision]
---
# ADR: ATOMIC 엔진 = Paperclip(조직 껍데기) + Hermes(슬롯 두뇌), 거버넌스 분할

## 컨텍스트

ATOMIC v1.1(2026-05-17)은 [[global/glen/concepts/Paperclip]] 조직도를 폐기하고 [[global/glen/concepts/Hermes-Agent]] Skill로 대체한다고 박제했다. 2026-06-03 글렌은 오픈소스 멀티에이전트 오케스트레이터 Paperclip(MIT, Node+PG, 셀프호스팅, 회사→프로젝트→이슈+예산+approval gate+config롤백+감사+비용추적 내장)을 **다시 채택하되 실행자가 아닌 "조직 껍데기"**로, 각 에이전트 슬롯의 두뇌를 raw 모델 대신 Hermes(HTTP 에이전트로 등록)로 채우는 **중첩구조**로 전환했다.

DB 실측(Task#2)에서 `autonomy_policy`↔`strategy_executions`/`cost` 직접 FK 없음·RLS 정책 0개(게이트는 이미 100% 앱 로직)·3-hard-guard 중 `cost_ceiling`만 Paperclip 예산에 매핑 가능하고 `risk_ceiling`/`confidence_floor`는 HBS 도메인 의미축이라 Paperclip 등가물 없음을 확증.

## 결정

**거버넌스를 분할(Split) 채택.**

- **앱 = Admission Gate**: Hermes 제안에 risk/confidence 태깅 → 앱이 `autonomy_policy`로 결정론 판정(risk≤ceiling AND confidence≥floor) → 통과분만 Paperclip 디스패치. `decision_type`·`is_auto` 전부 앱 소유, `autonomy_policy` = 입장게이트 SoT.
- **Paperclip = Execution Governance**: `cost_ceiling`→에이전트 월예산 실행시점 강제·승인·감사·tool-call·provider/model 비용·config/agent 롤백.
- 앱(FastAPI `/api/strategy/*`)은 `strategyExecApi` 13메서드 형태를 100% 보존하는 **BFF facade**로 두고 소스 오브 트루스만 뒤에서 교체. `strategy_executions`를 스파인으로 유지(1 execution↔1 Paperclip 이슈, `paperclip_project_id`/`issue_id` 재활용). 롤백은 2-파트(Paperclip revert + 앱 보상[`before_data` 역적용+외부발송 정정])를 facade가 단일 트랜잭션처럼 조율.

## 결과

콘솔 계약(`strategyExecApi`)·FE 무변경으로 엔진 백엔드를 교체 가능, 비용·예산·텔레메트리 중복제거 이득.

**미결/리스크**: ①`cost_ceiling`(scope/category numeric)↔Paperclip(agent/월) 배분 변환규칙 미결 ②`autonomy_policy` RLS 정책 0개 보안구멍이 입장게이트 SoT가 되며 우선순위 상향(scope 기반 admin-only write RLS 선결) ③카카오 알림톡 취소 불가→롤백 외부발송 보상은 정정발송 대체 검토 ④`agent_run.platform` enum `claude|other`→`hermes`/`paperclip` 추가 필요. C-PoC(Hermes 1개=Paperclip 슬롯, copywriter→SNS 풀사이클, 계약 0변경)는 Hostinger 세팅 후 착수. `ATOMIC_ASSISTANT_DESIGN` v1.1·`ATOMOS_TARGET_DEFINITION §7`·`STRATEGY_HUB_V2_DESIGN §3-2`의 "Paperclip=폐기/실행자" 기술이 본 ADR과 stale → 후속 정합성 갱신 필요. 단 S0 terminal-native 디스패치로 실제 Paperclip 경유 제안은 별도 실증됨(exec bb759785).

## 대안 검토

- **순수 A (Paperclip이 게이트 소유)**: risk/confidence가 HBS 도메인 의미축이라 Paperclip 등가물 없음 → 기각.
- **순수 B (앱이 비용·감사 재구현)**: Paperclip 내장 거버넌스를 버리고 중복 구현 → 기각.

## 참고

- 2026-06-08-hbs-atomic-console-engine-impl (구현 요약)
- 선행 결정 [[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent]] (v1.1 — 본 ADR이 부분 번복)

## 관련

- [[global/glen/concepts/Paperclip]]
- [[global/glen/concepts/Hermes-Agent]]
- [[global/glen/concepts/Atomic-Assistant]]
- [[global/glen/concepts/Strategy-V2]]
- [[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/superpowers/plans/2026-06-03-atomic-engine-paperclip-hermes-adr.md
- raw/docs/hbs-dashboard/memory/atomic-engine-paperclip-hermes.md
- raw/docs/hbs-dashboard/memory/atomos-product-vision.md
