# TOOLS — ATOMOS_FINANCE_TEAM

## 허용 toolsets
`terminal` 만 — 3단계 플레이북(이슈 fetch → 비용 진단/손익서 초안 → 결과 게시).
**게시 방법(중요)**: 결과 JSON 을 `/tmp/atomos_result.json` 에 저장(따옴표-닫은 heredoc) 후 `python3` urllib 로 코멘트 POST + 이슈 done PATCH — 어댑터 promptTemplate 명령 그대로. 멀티라인 결과의 인라인 이스케이프 회피용. 이 `/tmp` 결과파일 쓰기·`python3` 게시는 **플레이북 정식 절차**이며 SOUL '플레이북 외 terminal 명령 금지' 대상이 아니다.
금지 목록은 ATOMOS_HERMES TOOLS.md와 동일.

## 외부 발송·회계 시스템 (미승격)
손익서 발송·외부 회계 API 호출 = needs_external (send_gate).
승격 전까지 이슈 본문 데이터만 근거로 진단·초안 산출. 실제 발송은 외부 Pack 단계.
