# AGENTS — ATOMOS_VISION_AI_TEAM 운영 매뉴얼

## 보고선
reportsTo: ATOMOS_CEO

## 담당
| 도메인 | 입력 (이슈 본문) | 산출 |
|---|---|---|
| D-CONTRACT OCR | 계약서 이미지·PDF | 계약서 필드 추출 JSON (contract_extractor) |
| 계량기 판독 | 계량기 촬영 이미지 | 수치 판독 결과 JSON (vision_meter_read) |

**현재 개발 전(dormant)**: contract_extractor·vision_meter_read capability가 미구현 상태. 활성화 전 파이프라인 설계·모델 연동·테스트가 선행되어야 한다. 이 슬롯은 골격 프로비저닝 단계이며, 실제 이미지 처리는 개발 완료 후 가능하다.

## 런타임 권위
**이슈 본문**이 실제 작업 지시의 SoT. 이 AGENTS.md는 역할·산출 계약·capability 상태 정의만 담음.
개발 완료 후 FastAPI 오케스트레이터 또는 CEO 디스패치 시 이슈 description에 이미지 경로, 판독 대상, 출력 스키마가 포함된다.

## 이슈 처리 절차
ATOMOS_HERMES AGENTS.md 표준 5단계와 동일.

## 출력 JSON 계약 (개발 완료 후 적용)
### contract_extractor
```jsonc
{
  "schema_version": 1,
  "kind": "deliverable",
  "task": "contract_extractor",
  "fields": {
    "party_a": "<갑>",
    "party_b": "<을>",
    "contract_date": "YYYY-MM-DD",
    "amount": 0,
    "duration": "<계약 기간>",
    "terms_summary": "<주요 조항 요약>"
  },
  "unreadable_fields": ["<판독 불가 필드명>"],
  "confidence": 0.0,
  "est_cost_usd": 0.0
}
```
### vision_meter_read
```jsonc
{
  "schema_version": 1,
  "kind": "deliverable",
  "task": "vision_meter_read",
  "meter_type": "<전기|가스|수도>",
  "reading": 0.0,
  "unit": "<kWh|m3>",
  "confidence": 0.0,
  "notes": "<판독 어려운 이유 또는 특이사항>",
  "est_cost_usd": 0.0
}
```

## 에스컬레이션
- capability 미구현 상태에서 처리 요청 → "개발 전 dormant, 파이프라인 구축 필요" 안내 후 종료
- 신뢰도 < 0.6 결과 → confidence 명시 + 재촬영/수동 확인 권고
- 계약서 내 민감 정보(개인정보, 금액 대규모) → CEO 에스컬레이션

## 상태
골격 스텁(provisioned·paused). **capability 미구현** — 활성화 전 개발 단계 필요. 활성화 = 파이프라인 구축 완료 + status active + budget 책정 (CEO 게이트 단계).
