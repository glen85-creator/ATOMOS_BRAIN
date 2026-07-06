---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: CEO 게이트 v1 — 빌드·E2E 후 flag OFF·하드닝 결정 (2026-06-15)
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# CEO 게이트 v1 — 빌드·E2E 후 flag OFF·하드닝 결정 (2026-06-15)

## 맥락
[[global/glen/decisions/2026-06-12-atomos-execution-loop-and-org-direction|E층 실행루프]]의 다음 메커니즘으로, 승인된 감지를 도메인 슬롯에 fan-out 하기 직전 **ATOMOS_CEO 에이전트가 1홉 게이트 판단(GO/NO_GO/HOLD)** 하는 v1을 구현. 모델은 5라운드 bake-off로 deepseek-v4-flash 선정(강화 프롬프트 하에 약한근거 NO_GO 안정, reasoning 모델은 JSON 트렁케이트). "진짜 CEO 에이전트가 기존 이슈 indirection으로 수행"(헌장 충실, 인라인 함수 아님) 설계.

## 구현 (subagent-driven, 머지됨)
- **FastAPI PR#8** (origin/main `b472f97`): `app/services/elayer_ceo_gate.py`(`build_ceo_gate_issue`+`ceo_gate`, fail-open 전수검증) + `dispatch_execution` resolve_dispatch 직후 1홉(NO_GO/HOLD→`gated:ceo_*` 미전개·GO→기존 슬롯블록 무변경) + 호출부 방어 try. `ELAYER_CEO_GATE_ENABLED` **기본 OFF**.
- **ATOMOS_BRAIN PR#5** (`73bcef8`): CEO `apply-ceo.sh` 활성화(hermes_local·deepseek-v4-flash·budget 500·promptTemplate·status paused 출하; roster active) + AGENTS 게이트 계약.

## E2E 결과 (prod seed→approve→정리)
모델 **판별은 정확**: 강함(z=-2.6)→GO·약함(z=-0.3)→NO_GO·중복(동일 dedup_key)→NO_GO(**세션 메모리로 중복 탐지 — 의외 작동**). NO_GO 슬롯 차단·fail-open 무크래시 확인.
**그러나 에이전틱 배포 신뢰성 갭 2건 발견:**
1. **캡처 과대관용** — `_poll_agent_comment`(슬롯과 공유)가 "{" 포함 첫 코멘트를 채택 → 마크다운 요약/툴루프 부산물의 임베드 json을 캡처 → 강한근거 거짓 NO_GO(clean 68/76tok vs 오염 378/516tok).
2. **에이전트 루핑** — CEO(deepseek + **terminal 툴셋**, 에이전틱)가 가끔 판정 대신 **60회 터미널-툴 루프** → adapter_failed→blocked, verdict 못 냄. **bake-off는 *직접 호출*이라 이 갭을 못 드러냄 — 에이전틱 래퍼가 차이.** 강한근거 2/2 거짓 NO_GO.
실패 방향=안전측(거짓 NO_GO=정당 감지 자동화 누락, 해로운 발송/실행 아님).

## 결정
1. **`ELAYER_CEO_GATE_ENABLED` OFF** (Railway). 검증된 직접 디스패치로 복귀. always-on 게이트로는 신뢰성 미흡.
2. **하드닝 슬라이스 (다음)** — ①FastAPI 게이트 전용 캡처: 순수 JSON 코멘트만(본문 `{` 시작·이슈 done 후 최신 valid verdict, 마크다운/툴루프 배제) ②CEO 게이트 에이전트 경량화: terminal 툴셋 제거·max-iter 축소·"오직 verdict JSON" 단발 판정자.
3. **vehicle 재설계는 보류** — 에이전트 indirection vs 직접 LLM 호출(FastAPI에 이미 Anthropic haiku 키 존재) 트레이드오프 제시했으나 글렌이 현 방식 보강 선택(헌장 충실 유지).

## 교훈
- **bake-off(직접 LLM 호출)의 깔끔한 결과가 에이전틱 배포로 그대로 전이되지 않는다.** 에이전트 런타임(toolset·iteration loop)이 단발 판정을 불안정하게 만든다. 게이트처럼 "빠른 단일 판단"이 필요한 곳엔 도구 없는 경량 단발 모드가 맞다.
- E2E가 단위/통합 테스트가 못 잡는 배포 신뢰성 갭을 드러냄(과대관용 캡처·에이전트 루핑) — 라이브 seed E2E의 가치.

## 후속 — 하드닝 완료·튜닝·ON (2026-06-15 같은 날)
글렌이 OFF가 아닌 ON 유지를 택해(아까 안 껐음) 하드닝 후 바로 재검증.
- **하드닝(FastAPI#9·ATOMOS#6)**: `_poll_ceo_verdict`(순수JSON 캡처)·`_statistical_fallback`(|z|≥2→GO, NaN/inf 가드)·ceo_gate 재시도 루프(성공경로 record 실패해도 verdict 유지)·**persistSession=false**(블리드 차단)·안티루핑 프롬프트. subagent-driven(태스크별 2단계 리뷰+최종 교차리뷰)로 구현.
- **재-E2E가 튜닝 이슈 추가 발견**: 120s 타임아웃이 CEO 에이전트 실측지연(~3-4분)보다 짧아 **거의 항상 통계 폴백**(CEO verdict 폐기, 비용낭비). → **튜닝(#10): TIMEOUT 120→300s·RETRIES 1→0**. config.py 기본값=적용값(Railway 명시 env 없음).
- **재검증 결과**: 블리드 회귀 해결(동시 강함→GO·약함→NO_GO 정확) · CEO clean verdict **캡처 success**(단일/선행) · 잔여 엣지=동시버스트 2번째는 폴백(정답). 게이트 ON으로 라이브.
- **튜닝 교훈 확정**: bake-off(직접호출)는 에이전틱 런타임 지연·툴루프를 못 드러냄 → 라이브 E2E로 타임아웃을 실측지연에 맞춤.

## 상태
CEO 게이트 **ON·라이브**(deepseek, persistSession=false, resting paused, 디스패처가 idle↔paused). 게이트당 지연 최대 ~5분(async Celery 수용). 보드에 E2E 게이트/슬롯 이슈 잔류(mutation 403→UI 정리). 다음 후보: 동시버스트 폴백 개선·중복 결정론화·다도메인 확장·HOLD 휴먼큐.

## 관련

- [[global/glen/decisions/2026-06-12-atomos-execution-loop-and-org-direction]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-15-elayer-ceo-gate-design.md
- hbs-dashboard:docs/superpowers/specs/2026-06-15-ceo-gate-model-bakeoff.md
- hbs-dashboard:docs/superpowers/plans/2026-06-15-elayer-ceo-gate.md
