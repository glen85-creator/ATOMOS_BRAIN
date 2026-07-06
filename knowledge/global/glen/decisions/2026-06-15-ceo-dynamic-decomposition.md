---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: CEO 동적 분해 (도메인 후보 가지치기 + floor) — 게이트 ③담당자 분배 (2026-06-15)
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# CEO 동적 분해 (도메인 후보 가지치기 + floor) — 게이트 ③담당자 분배 (2026-06-15)

## 맥락
E층 게이트(GO/NO_GO/HOLD)의 마지막 미구현 역할 = ③담당자 분배. 기존 `resolve_dispatch(domain)`은 정적 `_DOMAIN_SLOTS` 맵으로 도메인→슬롯을 고정 라우팅(sales=ANALYST+RESEARCHER+MARKETING 항상 3개). CEO가 사안에 맞게 가동 슬롯을 고르게 해 fan-out을 맞춤화(비용·부하↓)하고 "지능적 분배"를 더한다.

## 결정 (브레인스토밍)
1. **CEO 자유도 = 도메인 후보 내 가지치기(A안).** 교차도메인(B)·CEO 자유 task작성(C)은 YAGNI 보류 — 빌더/스키마 계약 유지(리스크 0).
2. **floor 1차 슬롯 보장.** 도메인 1차 슬롯(sales→ANALYST 진단)은 CEO 무관 항상 가동. CEO는 증강 슬롯만 선택/가지치기. 기본 진단 보장 + 헌장 승격순서(ANALYST 먼저)와 일치.
3. **게이트 왕복 재사용.** verdict `{decision}`→`{decision, slots}` 확장(추가 호출/지연/비용 0).
4. **graceful degradation.** 선택 누락/비배열·게이트 폴백·플래그 OFF → 정적 전체 플랜.

## 구현 (subagent-driven, 6태스크, 순수 FastAPI)
- **FastAPI PR#15**: ①config `ELAYER_CEO_DECOMPOSE_ENABLED`(기본ON) ②`elayer_routing.py` — `_Spec/SlotTarget.floor`(기본 False, sales ANALYST만 True) + `apply_decomposition(plan, selected_kinds)` 순수함수(list→floor+(선택∩후보)·빈=floor만·비list→전체·`if not kept` 가드) ③`elayer_ceo_gate.py` — `GATE_DECOMPOSE_SCHEMA_DOC` + `build_ceo_gate_issue`가 다중슬롯+증강후보 있을 때만 분해섹션+slots 스키마(`_poll_ceo_verdict`/`ceo_gate` 무변경 — parsed dict 통째 반환이라 slots 자동 전파) ④`elayer_dispatch.py` — GO 후 `apply_decomposition(plan, verdict.get("slots"))`(게이트블록 내, verdict 스코프) ⑤FEATURES §11.
- **hbs-dashboard PR#11**: spec+plan+ROADMAP.
- 식별자 = **issue_kind**(도메인 내 유일·빌더 키 일치). CEO 선택은 후보 교집합 필터(없는 슬롯 발명 불가).
- 태스크별 spec+code-quality 2단계 리뷰 + 최종 교차리뷰.

## 최종 교차리뷰가 잡은 버그 (CHANGES NEEDED → 픽스)
`apply_decomposition`이 `set(selected_kinds)` 호출 — CEO(LLM)가 `slots`를 `[{"kind":"x"}]` 같은 **unhashable 원소**로 출력 시 `TypeError`. 그 호출부가 `ceo_gate` try/except **밖**이라 `dispatch_execution`을 탈출 → **fan-out 전체가 죽음**(fail-open 계약 위반). 픽스: ①`sel = {k for k in selected_kinds if isinstance(k,str)}`(문자열만) ②dispatch 호출부 try/except 가드(분해 실패→전체 플랜). 회귀 테스트 `[{"kind":...}]`→floor만 추가. **에이전트 신뢰성 비용은 실측에서만 드러난다**는 교훈의 또 다른 예 — LLM 오출력 방어가 필수.

## 라이브 E2E (실매장 ST-ET-CR-0001, z=-3.05)
approve→3 step 전개→게이트 **direct gate=GO**(CEO 에이전트 타임아웃→deepseek 직접 폴백)→ANALYST(floor)+RESEARCHER+MARKETING 전부 success→CEO 합성(direct)→`synthesized_report` 3 deliverables(ANALYST·RESEARCHER·MARKETING). **검증: 분해 와이어링이 경로를 안 깨고, floor 항상 가동, 안전 폴백(전체 플랜), 합성 정상.** ⚠️이 run은 실제 *pruning*은 안 함(전부 가동) — 게이트가 직접-LLM 폴백으로 떨어졌고(에이전트 상시 타임아웃) 가지치기는 비결정(CEO가 증강 불필요로 판단해야 발동). **실제 pruning 로직은 단위테스트로 완전 검증**(subset→prune·빈→floor만·None/비list→전체·unhashable 안전·floor 절대 드롭X). 즉 통합·안전폴백=라이브, 가지치기=단위테스트.

## 교훈
- **task-agnostic 인프라 재사용의 복리.** CEO promptTemplate·verdict passthrough가 이미 task-agnostic이라 게이트 코드는 `build_ceo_gate_issue`만 손댐(검증/폴백 무변경). 슬롯 추가(MARKETING)에 이어 분해도 라우팅+게이트본문 변경으로 환원.
- **graceful degradation 설계가 LLM 비결정성을 흡수.** 게이트가 거의 항상 폴백으로 떨어져도 floor+전체플랜 폴백이 하한 보장 → 분해는 "되면 좋은" best-effort.
- **가지친 슬롯 step_log는 approve때 생성됐다 pending 잔류**(미디스패치) — 합성 무시·무해, skipped 마킹은 후속.

## 상태
CEO 동적 분해 라이브·`ELAYER_CEO_DECOMPOSE_ENABLED` ON. 게이트 3역할(보안·가부·분배) 완비. 다음: 교차도메인 선택(B)·CEO 자유 task작성(C)·MARKETING 채널확장·실발송(needs_external, 보안 선결)·FINANCE/SCM 정식 슬롯. ADR 연속 [[global/glen/decisions/2026-06-15-sales-marketing-slot]].

## 관련

- [[global/glen/decisions/2026-06-15-sales-marketing-slot]]
- [[global/glen/decisions/2026-06-15-ceo-gate-v1-flag-off-harden]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-15-ceo-dynamic-decomposition-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-15-ceo-dynamic-decomposition.md
