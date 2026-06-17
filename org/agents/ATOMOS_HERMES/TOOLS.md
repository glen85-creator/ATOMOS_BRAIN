# TOOLS — ATOMOS_HERMES

## 허용 toolsets
`terminal` **만**. (browser/web/memory 등 비활성 — adapter.yaml과 일치해야 함)

## terminal 3단계 플레이북 (이 3단계 외 명령 금지)
어댑터 프롬프트가 제공하는 템플릿 변수(`{{taskId}}`, `{{paperclipApiUrl}}`)와
DEFAULT_PROMPT_TEMPLATE의 명령 형식을 따른다:

1. **이슈 fetch** — `curl -s {{paperclipApiUrl}}/issues/{{taskId}}` → 본문(작업·데이터·출력 스키마) 확인
2. **분석/산출** — 추가 명령 없이 내부 추론으로 수행
3. **결과 게시(코멘트+done)** — 결과 JSON 을 `/tmp/atomos_result.json` 에 저장(따옴표-닫은 heredoc) 후
   `python3` urllib 로 코멘트 POST + 이슈 done PATCH 를 한 번에. 멀티라인 결과의 인라인 이스케이프(이중 인코딩) 회피용 —
   `/tmp` 결과파일 쓰기와 `python3` 게시는 본 플레이북 **정식 절차**다. (CEO 슬롯만 예외적으로 인라인 curl 4단계 유지)

## 금지 명령 (예시 — SOUL 금지조항의 구체화)
- `apt/pip/npm install …`, `wget`, 임의 호스트로의 curl (paperclipApiUrl 외 전부)
- `env`, `printenv`, `cat ~/.hermes/.env` 등 시크릿 노출 명령
- `rm`, `chmod`, `kill`, 백그라운드 프로세스 생성

## 외부 도구(Pack)
현재 없음. Pack 추가는 조직 헌장 §3-3 승격 게이트 + adapter.yaml 갱신을 통해서만.
