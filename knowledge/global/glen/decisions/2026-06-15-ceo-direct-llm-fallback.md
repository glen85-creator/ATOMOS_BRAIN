---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: CEO 직접-LLM 폴백 (하이브리드) — 에이전트 신뢰성 보강 (2026-06-15)
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# CEO 직접-LLM 폴백 (하이브리드) — 에이전트 신뢰성 보강 (2026-06-15)

## 맥락
E층 CEO(게이트·합성)는 Paperclip 에이전트(deepseek-v4-flash via OpenRouter)가 이슈 왕복으로 판단한다. 그러나 에이전트는 spawn+멀티스텝 curl로 **~3-4분** 걸리고 terminal 툴로 가끔 60-iter 루프→타임아웃. 기존 폴백은 타임아웃 시 곧장 **통계(게이트)/번들(합성)** 같은 결정론 폴백으로 떨어져 **CEO의 실제 판단을 폐기**했다. bake-off(직접 LLM 호출 2-5s)는 빨랐지만, 그 신뢰성이 에이전틱 배포로 전이되지 않는다는 게 게이트 튜닝에서 드러난 핵심 교훈([[global/glen/decisions/2026-06-15-ceo-gate-v1-flag-off-harden]]).

## 결정 (브레인스토밍)
**하이브리드: 에이전트를 1차로 유지(헌장 충실)하되, 타임아웃 시 결정론 폴백 전에 LLM을 직접 호출해 CEO의 진짜 verdict/리포트를 캡처.** 폴백 계층이 2단→3단으로 깊어짐:
- **에이전트(1차)** → **deepseek 직접호출(2차)** → **통계/번들(최후, 결정론)**

vehicle 전면 직접호출 전환은 보류(에이전트=charter의 1차 실행 주체). 폴백 경로만 LLM 직접.

## Provider 결정 (글렌 캐치)
처음엔 FastAPI에 이미 있던 `ANTHROPIC_API_KEY`로 **claude-haiku 직접호출**로 구현했다. 글렌이 *"잠깐 ATOMOS에서 직접 ANTHROPIC api로 호출한다고?"* 로 캐치 — 2nd provider/model(anthropic/haiku)이 deepseek/OpenRouter 단일 아키텍처를 우회하는 문제. **결정 = deepseek 일관성**: `direct_llm_json`을 OpenRouter/deepseek로 스왑하고 **`OPENROUTER_API_KEY`를 Railway(FastAPI+Celery 워커)에 추가**. 키 없으면 direct no-op→통계/번들로 안전 강등.

## 구현 (subagent-driven, 4태스크, 머지·배포)
- **FastAPI PR#12**: `app/services/elayer_llm.py` `direct_llm_json(prompt_body, is_valid, max_tokens)` — `extract_json_block`+validator 통과 시 dict·아니면 None(never-raise). `ceo_gate`(재시도 루프 후 통계 전)·`synthesize_execution`(poll 후 번들 전)에 직접 폴백 블록 삽입, `_fallback="direct"` 마킹·성공경로 `record_agent_run` guard 래핑(C1 교훈 재적용). `ELAYER_DIRECT_LLM_FALLBACK_ENABLED`·`ATOMOS_DIRECT_FALLBACK_MODEL`.
- **FastAPI PR#13**: `direct_llm_json` provider 스왑(anthropic/haiku → OpenRouter `/chat/completions`/deepseek-v4-flash). 리뷰: shape exact·never-raise·records provider=openrouter·anthropic 잔재 0.
- 태스크별 spec+code-quality 2단계 리뷰 + 최종 교차리뷰.

## 라이브 E2E (실매장 ST-ET-CR-0001 국수나무 노량진점)
1차로 haiku 버전 E2E가 **메커니즘 선검증**(게이트 에이전트 타임아웃→직접호출이 실제 GO 캡처, provider=anthropic). OpenRouter 스왑+키 추가 후 재-E2E:
- approve → **게이트 에이전트 happy-path**(clean GO, attempt=1, paperclip) → 슬롯 2(ANALYST+RESEARCHER, openrouter) → **합성 에이전트 타임아웃 → deepseek 직접 폴백 발화**.
- agent_run: `platform=openrouter`·`llm_provider=openrouter`·`llm_model=deepseek-v4-flash`·`note="direct synth (poll timeout)"`.
- `synthesized_report._fallback="direct"` + **실제 deepseek 작성 한국어 점주 리포트**(번들 아님): exec_summary(65.6% 급락 분석)·store_message·prioritized_actions 5·deliverables 2.
- **하이브리드 end-to-end 입증.** seed 정리 완료.

## 교훈
- **agentic vehicle의 신뢰성 비용은 실측에서만 드러난다.** bake-off(직접호출)는 vehicle의 루프/경로개선/컨텐션 비용을 못 보여줬다. 직접-LLM 폴백이 그 갭을 메우면서도 에이전트를 1차로 유지(헌장).
- **provider 일관성 > 편의.** 가용한 키(anthropic)로 빠르게 짜는 것보다, 조직 아키텍처(deepseek/OpenRouter 단일)에 맞추는 게 옳다 — 글렌의 캐치.
- **C1 재적용**: 성공경로 `record_agent_run`을 guard 래핑(DB 블립이 캡처한 verdict/report를 폐기하지 않게).

## 상태
하이브리드 폴백 라이브·`ELAYER_DIRECT_LLM_FALLBACK_ENABLED` ON. E층 CEO 신뢰성 보강 완료. 다음: MARKETING 슬롯 확장(진짜 5산출물)·실제 발송(needs_external, 보안 선결)·CEO 동적 분해. ADR 연속 [[global/glen/decisions/2026-06-15-5output-synthesis-delivery]].

## 관련

- [[global/glen/decisions/2026-06-15-ceo-gate-v1-flag-off-harden]]
- [[global/glen/decisions/2026-06-15-5output-synthesis-delivery]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-15-ceo-direct-llm-fallback-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-15-ceo-direct-llm-fallback.md
