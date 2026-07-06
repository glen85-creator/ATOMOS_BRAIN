---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "sales fan-out에 MARKETING 슬롯 추가 — 진짜 \"5산출물\" (2026-06-15)"
tags: [domain/atomos, project/hbs-dashboard, status/active, glen-wiki, type/decision]
---
# sales fan-out에 MARKETING 슬롯 추가 — 진짜 "5산출물" (2026-06-15)

## 맥락
E층 sales 도메인 fan-out은 ANALYST(내부 진단)+RESEARCHER(외부요인) 2슬롯이었다. ROADMAP 목표는 "ANALYST·RESEARCHER·**MARKETING**(SNS·POP·리뷰응대) 다중슬롯 → 5산출물 → 점주 전달". 합성기(CEO 2차)가 이미 N슬롯 무관하게 동작하므로([[global/glen/decisions/2026-06-15-5output-synthesis-delivery]]), MARKETING 슬롯만 추가하면 "5산출물"이 자연 달성된다.

## 결정 (브레인스토밍)
1. **산출물 shape = RESEARCHER 미러(A안).** MARKETING이 매출 회복 마케팅 대응안 1제안을 기존 `PROPOSAL_SCHEMA_DOC`로 산출(SNS·POP·프로모션·리뷰관리·재방문을 actions[]에). 마케팅 전용 스키마(B안)·채널별 다중슬롯(C안)은 YAGNI로 보류.
2. **플래그 게이트** `ELAYER_SALES_MARKETING_ENABLED`(기본 ON) — 3슬롯은 Paperclip 부하↑라 즉시 끌 킬스위치.
3. **ATOMOS_BRAIN/VPS 변경 없음** — MARKETING 에이전트 promptTemplate이 이미 task-agnostic(이슈 본문 스키마를 그대로 따름, review·sales 공용)이고 `ATOMOS_MARKETING_AGENT_ID/MODEL`이 이미 config에 존재(review 도메인 사용 중)이며 active.

## 구현 (subagent-driven, 5태스크, 순수 FastAPI)
- **FastAPI PR#14**: ①config `ELAYER_SALES_MARKETING_ENABLED` ②`elayer_routing.py` — 제네릭 `_Spec.enabled_getter: Optional[Callable]=None`(None=상시ON, 기존슬롯 무영향) + `resolve_dispatch` 한줄 가드 + sales 3번째 `_Spec`(ATOMOS_MARKETING, issue_kind=`sales-marketing`) ③`atomos_bridge.py` `build_sales_marketing_issue`(`build_sales_research_issue` 미러, 지시만 마케팅 대응, PROPOSAL_SCHEMA_DOC 재사용) ④`elayer_dispatch.py` import + `ISSUE_BUILDERS["sales-marketing"]` ⑤FEATURES.md §11(E층 fan-out 문서화).
- **hbs-dashboard PR#10**: spec+plan+ROADMAP. **ATOMOS_BRAIN PR#8**: roster MARKETING domain `review→review·sales` 미러.
- 태스크별 spec+code-quality 2단계 리뷰 + 최종 교차리뷰(READY TO MERGE).

## 라이브 E2E (실매장 ST-ET-CR-0001 국수나무 노량진점)
approve → **"단계 3건 전개"** → 게이트 GO(에이전트 happy-path) → **3슬롯 전부 success**(ANALYST·RESEARCHER·**MARKETING** 전부 openrouter/deepseek) → CEO 합성(deepseek 직접폴백) → `synthesized_report` **3 deliverables**:
- diagnosis(ANALYST): 내부 운영 진단
- external_survey(RESEARCHER): 외부요인 5가설
- **marketing_response(MARKETING): 광고 재개·SNS 긴급 홍보·매장 POP·부정 리뷰 응대·기존 고객 쿠폰 5단계, 예상비용 ~$45**

**"진짜 5산출물" 목표 달성 입증.** (서버측 실행이라 앱 종료 중에도 완주.) seed·워크트리 정리 완료.

## 교훈
- **task-agnostic 에이전트 = 슬롯 확장 비용 0.** MARKETING이 이미 이슈 본문 스키마를 따르도록 설계돼(CEO promptTemplate 일반화와 동일 철학) review→sales 확장에 VPS/에이전트 변경이 전혀 없었다. 슬롯 추가가 순수 라우팅+빌더 등록으로 환원됨.
- **코드리뷰 I1(슬롯 공유 dedup_key→억제 우려) = 비이슈로 검증.** `_dispatch_one_slot` idempotency는 step_name(슬롯별 유일) 단위·슬롯별 distinct 이슈 생성, dedup_key는 본문 정보용일 뿐. RESEARCHER가 이미 동일 dedup_key로 ANALYST와 공존해온 게 결정적 증거. [dk:] 억제 가드는 `run_bridge_cycle`(자동감지 경로)에만 존재, approve→fan-out 경로엔 없음. → 리뷰 우려를 코드로 추적·반증.
- **3슬롯 비용**: 승인당 에이전트 3 + 게이트 + 합성 → 부하·합성 직접폴백 빈도↑·dispatch time_limit(900s) 압박. 플래그로 2슬롯 복귀 가능.

## 상태
sales 3슬롯 fan-out 라이브·`ELAYER_SALES_MARKETING_ENABLED` ON. E층 "5산출물" 목표 달성. 다음: MARKETING 채널별 분리(SNS·POP·리뷰 다중슬롯)·실발송(needs_external, 보안 선결)·FINANCE/SCM 정식 슬롯·CEO 동적 분해. ADR 연속 [[global/glen/decisions/2026-06-15-ceo-direct-llm-fallback]].

## 관련

- [[global/glen/decisions/2026-06-15-5output-synthesis-delivery]]
- [[global/glen/decisions/2026-06-15-ceo-direct-llm-fallback]]
- [[global/glen/entities-projects/HBS-Dashboard]]

## 출처(원본)

- hbs-dashboard:docs/superpowers/specs/2026-06-15-sales-marketing-slot-design.md
- hbs-dashboard:docs/superpowers/plans/2026-06-15-sales-marketing-slot.md
