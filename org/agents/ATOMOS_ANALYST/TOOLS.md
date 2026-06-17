# TOOLS — ATOMOS_ANALYST

## 허용 toolsets
`terminal` 만 — 3단계 플레이북(이슈 fetch → 분석 → 결과 게시).
**게시 방법(중요)**: 결과 JSON 을 `/tmp/atomos_result.json` 에 저장(따옴표-닫은 heredoc) 후 `python3` urllib 로 코멘트 POST + 이슈 done PATCH — 어댑터 promptTemplate 명령 그대로. 멀티라인 결과의 인라인 이스케이프 회피용. 이 `/tmp` 결과파일 쓰기·`python3` 게시는 **플레이북 정식 절차**이며 SOUL '플레이북 외 terminal 명령 금지' 대상이 아니다.
금지 목록은 ATOMOS_HERMES TOOLS.md와 동일.

## 분석 도구 규약
- 계산은 내부 추론으로. 외부 데이터 조회 금지 (이슈 본문 데이터가 전부)
- `sales_analyze`·`menu_cost_analyze`·`cost_anomaly_analyze` 등 도구 레지스트리 항목은
  이슈 본문이 해당 데이터를 동봉하는 형태로 제공됨 (직접 DB 접근 없음)
