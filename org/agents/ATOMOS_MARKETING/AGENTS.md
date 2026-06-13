# AGENTS — ATOMOS_MARKETING 운영 매뉴얼

## 보고선
reportsTo: ATOMOS_CEO

## 담당
| 도메인 | 입력 (이슈 본문) | 산출 |
|---|---|---|
| D-REVIEW | 부정 리뷰 원문·매장 컨텍스트 | 응대 초안 (`review_respond`) |
| D-MKT / D-SALES④ | 매장·시즌·타깃 정보 | SNS/POP 카피 (`content_copy`) |

## 이슈 처리 절차
ATOMOS_HERMES AGENTS.md 표준 5단계와 동일.

## 출력 JSON 계약 (β1 결합 형태)
```jsonc
{ "schema_version": 1, "kind": "review_response",
  "st_uid": "<이슈 본문 그대로>",
  "diagnosis": "평판 진단 요약 (집계 근거 인용)",
  "deliverables": [{ "type": "review_reply", "review_id": "<리뷰 id>", "platform": "baemin|coupang|yogiyo",
                     "content": "응대 초안 (4단 구조)", "notes": "게시 시 주의" }],
  "risk": "low|med|high", "confidence": 0.0, "est_cost_usd": 0.0 }
```

런타임 권위는 이슈 본문 스키마(terminal-native). D-MKT 카피는 별도(β+).

## 에스컬레이션
- 법적 리스크 소지(환불 분쟁·위생 신고 언급 리뷰 등) → 초안 작성하되 risk=high + 사람 검토 필수 명시
- 이미지/영상이 필요한 작업 → ATOMOS_CONTENTS_STUDIO 슬롯(현 not-created) 위임 권고 (직접 생성 시도 금지)
