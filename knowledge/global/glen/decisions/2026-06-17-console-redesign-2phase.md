---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "콘솔 재설계 #1 — 2-페이즈 생명주기 (이해→제안→실행) — 2026-06-17"
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# 콘솔 재설계 #1 — 2-페이즈 생명주기 (이해→제안→실행) — 2026-06-17

## 맥락
직전 트리아지-먼저 작업([[global/glen/decisions/2026-06-17-elayer-triage-flow]]) 후, 글렌이 콘솔을 더 테스트하며 **더 깊은 결함**을 발견: 매출급락 1건 승인 시 단계 탭에 7슬롯(진단·조사·SNS·POP·프로모션·리뷰·고객유지)이 **한꺼번에 나열**. 원인 = 7슬롯이 **이해(진단/조사)와 실행(마케팅/CRM)을 한 배치에 섞어 1-shot 병렬 팬아웃**. 그래서 *진단 끝나기도 전에* 실행안(홍보물 등)이 떠 있음. 글렌 멘탈모델: 먼저 이해(진단)→CEO가 그걸 보고 "이런 실행 필요" 제안→승인→실행. 즉 UI가 아니라 **실행 모델** 문제.

## 결정 (브레인스토밍)
- **콘솔 전체 재설계** 필요(탭 하나 패치로 못 고침) — 단 **5 surface로 분해**(통짜 spec 거부): #1 실행 생명주기 코어·#2 피드/상황실·#3 감지·#4 측정/회고/학습·#5 발송/채널. **북극성 헌장**: 콘솔=AI 본사(CEO)와 운영자의 협업 인터페이스, 생명주기 내러티브 중심, 기계장치(슬롯/스텝/탭) 강등. #1부터 순차.
- **실행 모델 = B. 2-페이즈**(이해→제안→실행). 완전 순차(C, 매 액션 승인)는 느림·고터치 기각; 1-shot(A)이 현 문제.
- 관문 **2개**: ① 실행 제안(진단 후), ② 보고 발송. 1-페이즈 도메인(리뷰·비용·원가, act 단일)은 관문① 건너뜀.
- 트리아지 자산(`ceo_plan`·`selected_kinds`·`apply_decomposition`·"승인=플랜" 원칙) 계승, **플랜 출처만** "빠른 z-score 트리아지"→"진짜 진단 기반 CEO 제안".

## 구현 (subagent-driven, 7 코드태스크 + 컨트롤러)
- **migration** `strategy_executions.phase`(detect|diagnose|propose|execute|report|sent, nullable).
- **슬롯 phase 태깅** (elayer_routing `_Spec/SlotTarget.phase`): sales ANALYST·RESEARCHER=diagnose, MARKETING4·CRM=act. `filter_plan_by_phase`·`has_diagnose_slots`.
- **`dispatch_execution(phase=)`**: diagnose=전체 진단·next `elayer_propose`; act=selected_kinds 필터·next `elayer_synthesize`; **None=레거시 게이트 경로(하위호환)**. Celery `elayer_diagnose`/`elayer_execute`.
- **`elayer_propose`(신규)**: 페이즈1 진단 산출→CEO가 `ceo_plan{diagnosis_summary, items[{strategy,issue_kind,title,why}], no_action, selected_kinds}` 제안. synthesis 인프라(이슈→폴→direct→번들) 미러·never-raise. items issue_kind를 act 후보로 한정(LLM 오출력 방어). source 분기별 추적(agent/direct/bundle).
- **diagnose EP**(triage EP 재정의, lazy-on-open): 제안 캐시 반환 | 진단 step 전개+enqueue | 1-페이즈 one_phase.
- **승인=act 실행**: `ApproveIn.selected_kinds`, act step 오프셋 전개(진단 step 뒤), phase=execute, `elayer_execute`. **0-선택 가드**(act엔 floor 없어 `apply_decomposition([])`가 전체 폴백→no-op). 진단중 승인 **409 가드**. synthesize→phase=report, send→sent.
- **hbs phase 기반 단일 화면**: `ExecutionDetailModal`이 **실행 row.phase**로 분기(diagnose/propose/execute/report/sent), 관문①제안카드(전략별 묶음·선택 체크박스·no_action)·②보고, **단계 탭 폐기**, 구 건(phase null)→레거시 5탭 폴백. ⚠️핵심 버그수정: phase를 diagnose콜 반환값서 소싱하면 items 있는 한 항상 propose 반환→execute/report/sent가 관문①에 갇힘 → **row.phase 소싱, diagnose콜은 null/detect 트리거 전용**.
- per-task 2단계 리뷰 + 최종 opus 통합리뷰(7 교차검증). 통합리뷰 BLOCKED 2건 수정: (a) 1-페이즈 "전체보기" 빈 모달→직접승인 뷰, (b) 진단중 인라인 승인 레이스→비활성+409 서버가드.

## 라이브 E2E (아주대점 sales, phase null)
diagnose→**2 진단스텝 완주**(워커 신규 태스크 등록 확인)→propose(`ceo_plan.items`, CEO 에이전틱 ~300s 타임아웃→**bundle** 5제안)→**승인 2/5 선택**(프로모션+CRM)→execute 2 act슬롯 완주·**orphaned pending 0**(핵심: 미선택 3슬롯은 step 미생성→고아 없음)→report(**direct 실합성**·4 deliverables+점주메시지). 추가: **409 진단중-승인 가드**·**1-페이즈**(cost-contract→one_phase·0스텝)·**레거시 백로그**(phase null 34건 무충돌) 입증. migration apply→PR#30/#38 머지→Railway 웹+워커 재배포(신규 태스크).

## 교훈
- **실사용이 결함 깊이를 드러냄**: 트리아지(승인 시점 이동)로도 못 고친 "진단·실행 혼재"는 실행 모델 문제였음. UI 패치가 아니라 페이즈 분리가 정답.
- **큰 재설계는 분해**: "콘솔 전체"를 통짜로 가면 진흙탕 → 5 surface + 북극성 헌장으로 쪼개 #1부터. 매주 눈에 보이는 것 + 학습 반영.
- **phase 소스 함정**: lazy 트리거 EP의 반환값을 화면 상태로 쓰면 안 됨(트리거는 캐시 단축경로가 있어 실제 phase와 다름) → DB row가 SoT. opus 통합리뷰가 잡음.
- **act엔 floor 없음**: diagnose만 floor(ANALYST) → act phase의 `apply_decomposition([])`는 전체 폴백 → 0-선택 가드 필수.
- **재사용 극대화**: resolve_dispatch·apply_decomposition·selected_kinds·슬롯빌더·_poll_slot_output·reconcile·synthesize·게이트·direct_llm·send 전부 재사용; 신규는 phase 분리+elayer_propose+상태 화면뿐.

## 상태
콘솔 재설계 #1 라이브·머지·E2E 입증. ATOMOS 콘솔이 "기계장치(슬롯/탭)" 항해에서 "CEO 대화/생명주기 내러티브"로 전환 시작. 다음=콘솔 surface #2 피드/상황실(내 승인 대기 그룹핑)→#3 감지→#4 측정/회고/학습→#5 발송/채널. ⚠️튜닝 follow-up: propose CEO가 흔히 bundle 폴백(에이전틱 타임아웃+큰 프롬프트로 direct도 None) → CEO 제안 품질, 곁버그 PAPERCLIP_API_KEY 마스킹과 함께.

## 관련

- [[global/glen/decisions/2026-06-17-elayer-triage-flow]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-17-console-redesign-northstar.md
- hbs-dashboard:docs/superpowers/specs/2026-06-17-elayer-2phase-lifecycle-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-17-elayer-2phase-lifecycle.md
