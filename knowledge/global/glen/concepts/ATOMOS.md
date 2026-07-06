---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: ATOMOS
tags: [domain/b2b-saas, domain/food-franchise, status/active, glen-wiki, type/concept]
---
# ATOMOS

## 정의

[[global/glen/entities-projects/HBS-Dashboard]]가 지향하는 외식 프랜차이즈 통합 운영 플랫폼의 코드명 겸 대외 브랜드. **"The Indivisible OS for F&B — 갈라놓을 수 없는 것들의 운영체제."** 기원전 5세기 데모크리토스의 그리스어 ἄτομος("나눌 수 없는 것")에서 따왔으며, 동시에 `Atom · OS` (Operating System)로도 읽힌다. 데이터를 통합하되 사람의 권한을 분리하고, AI 비서를 모두에게 제공하되 각자의 시야를 지킨다.

## 브랜드 어원과 듀얼 메시징

| 표기 | 읽는 법 | 의미 | 활용처 |
|---|---|---|---|
| `Atomos` | 아토모스 | 갈라놓을 수 없는 본질 (그리스 철학) | B2B / 본사·임원·투자자 — 철학적 무게감 |
| `Atom · OS` | 아톰 오에스 | 외식업의 운영체제 | B2C / 점주·매장 — 실용·자동화·시간 절약 |

마스터 슬로건: **"Atomos. The Indivisible OS for F&B. 갈라놓을 수 없는 것들의 운영체제."**

## 4가지 브랜드 신념

1. **본질은 작다 (Essence is small)** — 매장의 진실은 거창한 KPI가 아니라 한 끼의 원가, 한 손님의 동선, 한 번의 거래에 있다.
2. **본질은 사라지지 않는다 (Data never dies)** — 모든 매입·매출·운영 기록은 영원한 자산. Atomos는 매장의 모든 히스토리를 잃지 않게 한다.
3. **새로움은 재조합에서 (Novelty by recombination)** — 콘텐츠·쿠폰·자동화는 모두 이미 가진 데이터의 재조합이다.
4. **사람을 잇는 데이터 (Data that connects people)** — 외식업은 결국 사람으로 돌아간다. 점주·직원·손님·본사를 갈라놓지 않는다.

## 4계층 아키텍처

데이터는 위에서 아래로 흐르고, 학습은 아래에서 위로 다시 쌓인다. 운영하면 운영할수록 시스템이 똑똑해지는 구조.

| 계층 | 이름 | 역할 |
|---|---|---|
| Layer 1 | **API Gateway** | 외부 데이터 수집 — "흩어진 사실을 모은다". POS·배달앱·ERP·물류·SNS·결제·인사·IoT·공공·부동산 |
| Layer 2 | **DATA HUB** | 데이터 축적·정규화 — "사실을 영원히 잃지 않는다". 매출·공급망·코드매핑·결정·과정·작업·관계·학습·자산 사실 |
| Layer 3 | **Agent** | 실제 일을 실행 — "사람이 할 일을 AI가 한다". 콘텐츠·POP·쿠폰·키오스크·비전·자동발주·리뷰응대·정산 |
| Layer 4 | **[[global/glen/concepts/Atomic-Assistant]]** | 점주·본사 옆의 비서 — "결정을 옆에서 돕는다". 매장/본사 운영비서·암묵지·오케스트레이션·위기 감지·학습 |

## 6대 운영 도메인

프랜차이즈 본사가 매일 굴려야 하는 6개 운영 영역. 같은 마스터 데이터 위에 올라가 있어 식자재 단가 한 번 바뀌면 메뉴 원가·매장 손익·브랜드 KPI까지 동시 반영.

| # | 도메인 | 현재 상태 |
|---|---|---|
| 1 | 식자재 발굴 | 인프라 95% / UI 60% / 자동화 70% — 49,311행 공급망 fact 적재 완료 |
| 2 | 본사 전략 ([[global/glen/concepts/Strategy-V2]]) | 인프라 95% / UI 85% / 운영검증 40% — 2026-06-15 정식 가동 |
| 3 | SV 관리 | 인프라 70% / UI 40% — 신규 모듈 |
| 4 | 메뉴 R&D | 인프라 100% / UI 80% — 레시피 SemVer 버전 관리 |
| 5 | 가맹 확장 | 신규 — 2026 Q4 ~ 2027 Q1 |
| 6 | 브랜드 개발 | 신규 — 2027 Q1 ~ Q2 |

## 듀얼 페르소나 — AI 본사 ↔ AI 직원

| Atomos for Independents (AI 본사) | Atomos for Headquarters (AI 직원) |
|---|---|
| 단일 매장 점주에게 "AI가 본사 역할" | 프랜차이즈 본사에게 "AI가 직원·팀 역할" |
| 종합 대시보드 / 매출 달력 / 메뉴 엔지니어링 / 배달 손익 / 시뮬레이터 / 전략 자동화 | 본사 통합 대시보드 / 브랜드 KPI 롤업 / 매장 A/B/C 등급 / 마스터 데이터 통합 |
| "본사 없이도 본사가 있는 것처럼" | "최소 인력으로 다매장을 운영" |

단일 매장이 2호점·3호점으로 성장하는 순간 같은 데이터·같은 인프라 위에서 AI 본사 모드 → AI 직원 모드로 자연 전환된다.

## Pack 기반 모듈형 진화

데이터 소스(POS / 배달 / 회계 / 물류 / SNS / 공공)도, 에이전트(콘텐츠 / 비전 / 자동발주 / 키오스크 / 리뷰응대 / 회계자동화 / 가맹영업)도 모두 Pack 단위로 붙고 뗀다. 새 Pack이 시장에 등장하면 같은 데이터 위에서 즉시 작동.

## 함께 성장하는 시스템 (동지 모델)

같은 Atomos 위의 매장·본사는 라이벌이 아니라 동지. 익명·집계 패턴이 비슷한 환경 매장끼리 공유되어 신규 가입 매장도 첫날부터 베테랑의 노하우를 받는다. 개별 매출·고객·거래 데이터는 절대 공개되지 않고 평균·분포·시나리오 결과만 공유 — 사용자가 늘수록 모든 사용자의 가치가 커지는 데이터 네트워크 효과.

## 핵심 지표 (2026-05 vs 2026-12 목표)

| 항목 | 현재 | 목표 (2026-12) |
|---|---|---|
| 관리 매장 수 | 264개 (자체) | 500+ (3개 본사) |
| 외부 데이터 통합 | 49,311행 (97.3% 매핑) | 실시간 동기화 |
| 식재료 마스터 | 408개 품목 | 브랜드 확장에 따라 자동 증가 |
| 레시피 마스터 | 110개 (2 브랜드) | 5+ 브랜드 확장 |
| LLM 자동화 | 워커 8 + 정기작업 5 | 2026-06-15 정식 가동 |

> **정본**: Manifesto v3 / 소개서 v2.0 (2026-05-16) — 관리 매장 264. Manifesto v2(2026-05 초)의 200, BUSINESS_PLAN(2026-05-11)의 287(운영 199 / 휴점 74 / 기타)은 더 이른 시점·다른 모집단의 수치이며, 본 위키 전체의 자체 매장 수치는 264를 기준으로 한다.

## 작업공정 (88 항목 10 카테고리, 평균 진행률 ~50%)

| 카테고리 | 항목 | 완료 / 진행 / 대기 |
|---|---|---|
| 1. 운영 관제 | 8 | 4 / 4 / 0 |
| 2. 마스터 데이터 | 9 | 6 / 3 / 0 |
| 3. 외부 데이터 통합 | 12 | 5 / 1 / 6 |
| 4. 자율 운영 (전략 자동화 + 에이전트) | 18 | 3 / 15 / 0 |
| 5. 본사 통합 관제 (B2B 코어) | 5 | 0 / 4 / 1 |
| 6. 운영 도메인 6 | 6 | 0 / 4 / 2 |
| 7. Atomic (운영의 비서) | 7 | 0 / 6 / 1 |
| 8. 차세대 모듈 (Next Horizon) | 10 | 0 / 0 / 10 |
| 9. 함께 성장하는 시스템 (동지 모델) | 5 | 0 / 0 / 5 |
| 10. 시장 진입 / 통합 브랜드 플랫폼 | 8 | 0 / 1 / 7 |

자원 확보 우선순위: ① 베타 본사 운영 검증 (영업·CS) → ② 본사 통합 관제 코어 (내부 개발) → ③ 외부 API·H/W 협의 (배달앱·키오스크·비전) → ④ 통합 브랜드 플랫폼 (모바일 팀). 출처: `Atomos_Roadmap.md` / `Atomos_작업공정표.md`.

## 차세대 확장 (Next Horizon)

운영 도메인 6 다음에 올라갈 모듈. 모두 같은 4계층 위에서 동작.

1. **품질·위생 관리** (HACCP, 비전 분석) — 2026 Q4
2. **수요예측·재고 자동발주** — 2026 Q4 ~ 2027 Q1
3. **입지·상권 전략** — 2026 Q4 ~ 2027 Q1
4. **인력·운영 관리** (스케줄링·노무) — 2026 Q4 ~ 2027 Q1
5. **브랜드 실험·학습** (A/B) — 2026 Q4 ~ 2027 Q2
6. **본사 예산·회계 관리** — 2026 Q4 ~ 2027 Q3 *(소개서 v2.0에서 신설)*

## 시장 진입 전략

| STEP | 단계 | 시점 |
|---|---|---|
| 1 | 1차 풀 (이미 우리 본사 물류·POS 인프라 일부 이용 중인 본사·매장)에서 베타 본사 1~2곳 | 2026 Q3 ~ Q4 |
| 2 | 1차 풀 횡전개 + 다본사 운영 (5+ 본사 / 500+ 매장) | 2027 상반기 |
| 3 | 통합 브랜드 플랫폼 (앱) 출시 — 여러 브랜드를 한 앱에서, 공동 멤버십·결제·식자재 협상 | 2027 하반기 ~ |

## 차별화 5+1 가지

1. 운영 도메인 6 통합 — 한국 외식 운영 솔루션 중 유일
2. 5단계 데이터 통합 (레시피 ↔ 본사매입 ↔ 물류매출 ↔ 매장매입 ↔ POS매출)
3. 암묵지 자동 축적 — 운영하는 행위 자체가 곧 노하우 축적
4. AI 본사 ↔ AI 직원 양방향 — 같은 시스템으로 매장 1개 → 200개 성장 단계 전체 커버
5. Pack 기반 모듈형 진화
6. 함께 성장하는 시스템 (동지 모델 — 소개서 v2.0에서 차별화 6번째로 추가)

## 자동화 인프라 — Cron Jobs + LLM Workers

| Cron Job | 빈도 | 역할 |
|---|---|---|
| sales-watch | 매일 06:00 | 매출 급락 자동 감지 → 전략 실행 제안 |
| kpi-snapshot-weekly | 일 23:55 | 주간 KPI 스냅샷 적재 |
| learning-update | 일 23:00 | 시나리오 성공률 가중치 학습 |
| kpi-final-check | 매일 01:00 | 전략 종결 판정 |
| ingredient-mapping | 매일 02:30 | 식재료 매핑 5단계 파이프라인 |

LLM Worker 8개: analyst / analyst-final / coach / copywriter / pop-writer / review-responder / classify-reviews / generate-content. 모두 통합 AI 게이트웨이를 경유 — 공급사 통일·실패 시 자동 우회·비용 추적·Zero Data Retention.

## 적용 예

- [[global/glen/entities-organizations/HBS]] 6 브랜드 287매장의 자체 검증 (dogfooding)
- [[global/glen/entities-organizations/국수나무]], [[global/glen/entities-organizations/청년38국수]] 등 자체 브랜드를 1차 학습장으로
- 베타 본사 1~2곳 도입 (2026 하반기) 후 외부 프랜차이즈로 확장

## 노트

- 마스터 설계서: `ATOMOS_INTEGRATED_DESIGN.md` v1.0 (2026-05-16) — 내부 기술 사양의 단일 진실
- 대외 브랜딩 자료: 소개서 v2.0 / Manifesto v3 (둘 다 2026-05-16) — 외부 파트너 브리핑용. v2 → v3에서 "동지 모델" 섹션이 추가되었고, v3 → 소개서 v2.0에서 차세대 모듈이 5종 → 6종으로 확장(예산·회계 추가).
- 한국어 버전 로드맵 문서(`개발_로드맵_B2C_TO_B2B.md`)는 영문 `ROADMAP_B2C_TO_B2B.md`의 한국어 동등판 — 비교 시 본질 차이 없음.
- 본 볼트에서의 위치: `raw/docs/hbs-dashboard/docs/` (영문 .md 11종) + `binaries-extracted/` (한국어 docx 추출본 7종)

## 관련

- [[global/glen/entities-projects/HBS-Dashboard]]
- [[global/glen/entities-organizations/HBS]]
- [[global/glen/concepts/Atomic-Assistant]]
- [[global/glen/concepts/Hermes-Agent]]
- [[global/glen/concepts/Olympus-Console]]
- [[global/glen/concepts/Strategy-V2]]
- [[global/glen/concepts/Paperclip]]
- [[global/glen/concepts/Permission-Matrix]]
- [[global/glen/decisions/2026-05-17-hermes-as-external-nous-agent]]
- [[global/glen/decisions/2026-06-03-atomic-engine-paperclip-hermes-split]]
- [[global/glen/decisions/2026-06-07-hq-sim-monthly-preaggregation-cache]]

## 출처(원본)

- raw/docs/hbs-dashboard/docs/ATOMOS_INTEGRATED_DESIGN
- raw/docs/hbs-dashboard/docs/binaries-extracted/Atomos_소개서
- raw/docs/hbs-dashboard/docs/binaries-extracted/Atomos_Brand_Document
- raw/docs/hbs-dashboard/docs/binaries-extracted/Atomos_Manifesto_v3
- raw/docs/hbs-dashboard/docs/binaries-extracted/Atomos_Manifesto_v2
- raw/docs/hbs-dashboard/docs/binaries-extracted/Atomos_Roadmap
- raw/docs/hbs-dashboard/docs/binaries-extracted/Atomos_작업공정표
- raw/docs/hbs-dashboard/docs/binaries-extracted/개발_로드맵_B2C_TO_B2B
