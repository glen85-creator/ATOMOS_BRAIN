---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: "ADR: 감지 기준 탭 (ATOMOS 설정 통합) + 전략 전환"
tags: [domain/atomos, domain/frontend, status/done, priority/high, glen-wiki, type/decision]
---
# ADR: 감지 기준 탭 (ATOMOS 설정 통합) + 전략 전환

## 맥락 — 글렌의 전략 전환

글렌: "팀을 너무 많이 만들어 놔서 복잡하고 테스트하기 어렵다. **하나의 주제씩** 검증하자. 원인(감지 기준)부터 정확히 드러내야 ATOMOS 콘솔·AI부서가 정확히 산다." → 새 기능을 더 쌓기보다 기존 파이프라인의 각 단계를 하나씩 투명화·검증·통합. 첫 타깃 = **감지**(원인). 콘솔 재설계 북극성 surface #3.

## 전체 검토 결과 (핵심 발견)

4갈래 병렬 조사(워크플로). 핵심: 글렌이 원한 "감지 제외 체크박스"는 **이미 존재**(`detection_settings.enable_*` 6 도메인 토글이 자동감지 Celery를 실제 게이팅 + `/admin/atomos` B0 섹션 체크박스). **진짜 없는 것 = 각 감지의 공식·기준·라벨을 토글 옆에 통합한 투명성 뷰.** → 신규가 아니라 **통합**.

감지 인벤토리(8): sales-daily-drop(매장×요일 robust z, z≤−3🔴/≤−2🟡)·underperform(월 매출/영업이익/원가율 규칙)·cogs-ig(공급가 급등 플래그)·cogs-menu(원가율>40%)·cost-util(공과금+30%)·cost-contract(만료≤30일)·review(부정율≥25%/미답변≥5)·opportunity(미구현). 공식 원천=Supabase RPC, 임계=`detection_settings` 노브, 라벨=FE 상수에 흩어짐.

## 결정 (brainstorming)

- 제외 단위 = **도메인 6개**(기존 `enable_*` 재사용, BE 0).
- 설명 카탈로그 = **FE 정적**(공식은 SQL에서 자동추출 불가→수기, 어차피 FE/BE 동일) + 임계값·토글은 라이브 `detection_settings`.
- 통합 = 새 **"감지 기준" 탭이 기존 도메인토글(B0)+임계값(B) 섹션 흡수** → 감지 제어 단일 홈.
- 범위 = **FE 전용, BE/migration 0**.
- P4 원가 업로드(price-ratio 검토큐)는 별개 surface → v1 제외.

## 구현 (hbs#43, FE only)

- `detectionCatalog.ts`(신규): 8 감지 정적 메타(formula 평문·thresholdKeys[detection_settings 키]·labels·enable 도메인·status) + `enableKeyOf` + 완전성 vitest. `FieldKey`/`FIELDS`/`DOMAIN_TOGGLES`를 AtomosSettings에서 이동.
- `DetectionCriteriaTab.tsx`(신규): 카탈로그 도메인 그룹 리스트(헤더 on/off=enable_* + 항목별 공식·라벨 badge·라이브 임계값 편집[GaugeField/Field 재사용]). 미구현 흐림.
- `AtomosSettings.tsx`: 탭 2개(🔍감지 기준/⚙운영·자율성), B0+B 흡수·폐지. 공유 UI는 `settingsUi.tsx` 리프 모듈.
- 제어 의미 불변: 체크 해제→`enable_*=false`→기존 Celery 게이팅 skip. detection_settings get/put·DetectionSettings 타입 그대로.

## 2단계 리뷰

- Task1(카탈로그): PASS — 8항목 spec 정합, FIELDS 이동 byte-identical.
- Task2(탭): spec PASS(pct 변환 byte-identical·save path 불변). 코드품질 CHANGES — **순환 import**(DetectionCriteriaTab↔AtomosSettings, `Field`/스타일) 빌드는 되나 module-eval-time 사용 추가 시 TDZ 위험 → `settingsUi.tsx` 리프 모듈로 추출해 해소. 그 외(pct 헬퍼 중복=byte-identical 수용·opportunity 토글 비활성=무영향) 수용/후속.

## 배포·검증

hbs#43(코드)·#44(docs), GCM PR+머지, Vercel. 검증: `detection-settings` EP가 6 enable_*+임계값 키+target_br_ids 라이브 반환(탭 데이터 소스) 확인. 빌드 0에러·vitest 108 pass·2단계 리뷰. (FE 시각 스모크는 글렌 eyeball — 순수 추가 탭, BE 무변경.)

## 교훈

- "신규 같지만 이미 있는 것"을 전체 검토로 먼저 드러내 **통합 vs 신규** 판정 → 중복 방지(글렌 "통합" 의도 적중).
- 공유 repo 병렬 P4 세션 활성 → 워크트리 작업 일관 적용(spec/plan/구현 전부 격리).
- 작은 FE 슬라이스라도 2단계 리뷰가 순환 import 같은 잠복 fragility 포착.

다음: 항목별 세부 제외 · P4 원가업로드 행 · 감지 surface(콘솔 탭) 전면 재설계 · #4 측정/학습 · #5 발송.

## 관련

- [[global/glen/decisions/2026-06-18-console-feed-operator-home]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/superpowers/specs/2026-06-18-detection-criteria-tab-design.md
