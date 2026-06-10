# TOOLS — ATOMOS_ANALYST

## 허용 toolsets
`terminal` 만 — 4단계 플레이북(이슈 fetch → 분석 → JSON 코멘트 → done).
금지 목록은 ATOMOS_HERMES TOOLS.md와 동일.

## 분석 도구 규약
- 계산은 내부 추론으로. 외부 데이터 조회 금지 (이슈 본문 데이터가 전부)
- `sales_analyze`·`menu_cost_analyze`·`cost_anomaly_analyze` 등 도구 레지스트리 항목은
  이슈 본문이 해당 데이터를 동봉하는 형태로 제공됨 (직접 DB 접근 없음)
