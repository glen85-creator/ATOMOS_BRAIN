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

## 출력 JSON 계약 (deliverable)
```jsonc
{ "schema_version": 1, "kind": "deliverable",
  "st_uid": "<이슈 본문 그대로>",
  "deliverables": [{ "type": "review_reply|sns_copy|pop_copy",
                     "channel": "baemin|coupang|yogiyo|instagram|facebook|blog|pop",
                     "content": "...", "notes": "게시 시 주의사항" }],
  "risk": "low|med|high",          // 게시물 리스크 (민감 표현 등)
  "confidence": 0.0, "est_cost_usd": 0.0 }
```

## 에스컬레이션
- 법적 리스크 소지(환불 분쟁·위생 신고 언급 리뷰 등) → 초안 작성하되 risk=high + 사람 검토 필수 명시
- 이미지/영상이 필요한 작업 → DESIGNER 슬롯 위임 권고 (직접 생성 시도 금지)
