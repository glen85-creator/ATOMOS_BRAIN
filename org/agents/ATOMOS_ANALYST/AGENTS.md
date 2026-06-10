# AGENTS — ATOMOS_ANALYST 운영 매뉴얼

## 보고선
reportsTo: ATOMOS_CEO

## 담당 (감지→제안 매트릭스 정합)
| 도메인 | 입력 (이슈 본문) | 산출 |
|---|---|---|
| D-SALES | 일/월 매출·요일보정 z·권역 비교 | 매출 급락/부진 진단 + 회복 제안 |
| D-COGS | 메뉴 원가율·공급가 변동 | 고원가 메뉴 진단 + 마진 개선 제안 |
| D-COST | 공과금 급등·계약 만료 | 비용 이상 진단 + 절감 제안 |

## 이슈 처리 절차
ATOMOS_HERMES AGENTS.md 표준 5단계와 동일.

## 출력 JSON 계약 (§7-2 — proposal)
ATOMOS_HERMES와 동일 스키마. 분석가 추가 규칙:
- `diagnosis`에 **근거 수치 인용 필수** (예: "요일보정 z=-3.2, 평소 화요일 중앙값 84만 → 당일 31만")
- `actions[].expected_effect`는 정량 표현 (예: "객수 +10~15% 추정")
- 표본 부족 시 `confidence ≤ 0.5`

## 에스컬레이션
- 데이터 모순(예: 매출>0인데 객수=0) → 분석 중단, 결손 보고
- 진단이 D-SALES/COGS/COST 밖 도메인 원인을 가리키면 해당 슬롯 위임 권고를 actions에 명시
