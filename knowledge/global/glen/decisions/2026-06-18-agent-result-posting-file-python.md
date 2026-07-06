---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: ATOMOS 슬롯 에이전트 결과 게시 = file + python3 (60-iter 도구루프 근본수리)"
tags: [domain/atomos, domain/backend, status/done, priority/high, glen-wiki, type/decision]
---
# ADR: ATOMOS 슬롯 에이전트 결과 게시 = file + python3 (60-iter 도구루프 근본수리)

## 맥락 (Context)

ATOMOS E층 fan-out 슬롯 에이전트(ANALYST·RESEARCHER·MARKETING·CRM·FINANCE·SCM, deepseek-v4-flash, terminal-only, hermes_local)가 결과를 Paperclip 이슈 코멘트로 게시할 때 **60 tool-iteration 을 소진**하다 실패/raw 캡처되던 고질 증상.

직전 슬라이스(FastAPI#32, [[global/glen/decisions/2026-06-17-console-redesign-2phase]] follow-up)는 **캡처 측**을 고쳤다(extract_json_block strict=False·raw→failed 정직 표기). 잔여 = **에이전트 측 60-iter 실패 자체**.

## 근본원인 (systematic-debugging)

에이전트는 작업(콘텐츠 생성)은 빠르게 끝낸다. 죽는 곳은 **결과 '게시' 단계**다. 범인 = **OUR promptTemplate**(`~/ATOMOS_BRAIN/deploy/payloads/*.json`) step 3:

```
curl -s -X POST ".../issues/{{taskId}}/comments" -d '{"body":"<여기에 결과 JSON 문자열>"}'
```

이 인라인 형식은 에이전트에게 **멀티라인 결과 JSON 을 (1) 문자열로 이중 인코딩 + (2) 셸 이스케이프**를 손으로 하라고 요구한다. 멀티라인 마케팅 카피(따옴표·줄바꿈·중괄호 포함)에선 이게 사실상 불가능 → 에이전트가 /tmp 저장·임시 스크립트·키 하드코딩 등을 시도하며 60 iter 를 태운다. (모델 성능 문제가 **아님** — 경로/도구 문제.)

증거: 에이전트 컨테이너에 `python3 3.13`·`urllib`·heredoc 가용. `{{paperclipApiUrl}}` 게시는 컨테이너 내부 무인증(PAPERCLIP_API_KEY 불요). pre-fix 실행 13db6c80 의 MARKETING `프로모션·재방문` 슬롯이 raw=True/stuck 으로 박제.

## 결정 (Decision)

**6개 fan-out 슬롯 promptTemplate step 3 을 file + python3 게시로 교체** (4단계→3단계):

1. 결과 JSON 을 **따옴표-닫은 heredoc**(`<<'ATOMOS_RESULT_EOF'`, 닫는 표시 column 0)으로 `/tmp/atomos_result.json` 에 그대로 저장 — 셸·이스케이프 불개입.
2. `python3 -c` 한 줄(single-quoted bash arg, 내부 double-quote만)로 `json.dumps({"body": open(file).read()})` → urllib 코멘트 POST + 이슈 done PATCH 를 한 번에. **인코딩·이스케이프 전부 자동**.

**CEO 슬롯은 제외** — 하드닝상 인라인 curl 4단계 + 안티루핑(`python`/`/tmp` 금지)을 유지(짧은 verdict/합성 JSON, direct_llm 경로 주력).

### 핵심 부수결정 — 지시 번들 정합 (어드버서리얼 리뷰 C-major)

슬롯 런타임 지시 번들(슬롯 `SOUL.md` "TOOLS.md 플레이북 외 terminal 명령 금지" + `TOOLS.md` "curl 4단계 playbook")이 새 python 게시와 **정면 모순** → 리터럴한 모델이 "플레이북 외 명령"으로 보고 거부/재루핑 → **고치려던 그 증상 재유발** 위험. 따라서:

- 6 슬롯 `TOOLS.md` + HERMES `SOUL/TOOLS/AGENTS.md` 를 "`/tmp` 결과파일 쓰기·`python3` 게시 = 플레이북 정식 절차"로 정합.
- promptTemplate 자체에도 self-authorization 1줄(belt-and-suspenders).
- 헌장 `docs/ATOMOS_OFFICE_ORG_DESIGN.md` = 슬롯 3단계 / CEO 4단계 분리 명시.

**원칙: 프로덕션 AI의 동작은 task prompt 와 persistent instruction bundle 의 정합으로 결정된다 — 알려진 모순을 남기지 않는다.**

## 배포·검증

- ATOMOS_BRAIN PR #11 머지(main `4ee6662`). FastAPI/hbs 코드 무관(ATOMOS_BRAIN 전용).
- VPS = scp copy `/root/ATOMOS_BRAIN`(**git clone 아님** → scp+ssh). 15파일 scp → scoped instruction 업로드(9파일·백업동반, `upload-instructions.sh` 로직 미러) + 6 `apply-*.sh` PATCH → **라이브검증 6슬롯 promptTemplate 에 python3 ALL_OK**.
- 로컬 round-trip 테스트: 재작성 payload 의 python3 명령 추출 → HTTP stub 에 멀티라인·따옴표·한글·백슬래시 결과 JSON → body 손상없이 round-trip PASS.
- 어드버서리얼 3-리뷰어(명령·캡처·완전성) 워크플로우 통과.
- **E2E**: 9e0964a9 재승인[sales-promo] → 신규 MARKETING `프로모션·재방문` act 슬롯(새 템플릿) → **~120s 완료·raw=False 구조화**(st_uid/channel/rationale/content_drafts)·이슈 **코멘트 1건**(무-루프 입증) **vs 동일슬롯 pre-fix(13db6c80) raw=True/stuck ~15min**.

## 교훈

- 60-iter 의 진짜 원인은 모델 capability 가 아니라 **우리가 준 게시 도구(인라인 curl 이스케이프 지옥)**.
- heredoc 닫는 표시는 반드시 column 0(들여쓰기 시 미닫힘) — 템플릿 예시 들여쓰기가 footgun. flush-left + 경고로 해소.
- 캡처 측(#32 strict=False)과 게시 측(이번)이 **상호보완** — 에이전트가 멀티라인 content_drafts 를 그대로 써도 양쪽이 받쳐줌.
- 어드버서리얼 리뷰가 단독작업이 놓친 "지시 번들 모순"(런타임 거부 위험)을 잡음.

잔여(별도): 동일에이전트 throughput·실 점주 수신자(풀 유저인증)·카톡/SNS 채널.

## 관련

- [[global/glen/decisions/2026-06-17-console-redesign-2phase]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/superpowers/ROADMAP.md
