# TOOLS — ATOMOS_HERMES

## 허용 toolsets
`terminal` **만**. (browser/web/memory 등 비활성 — adapter.yaml과 일치해야 함)

## terminal 4단계 플레이북 (이 4단계 외 명령 금지)
어댑터 프롬프트가 제공하는 템플릿 변수(`{{taskId}}`, `{{paperclipApiUrl}}`)와
DEFAULT_PROMPT_TEMPLATE의 curl 형식을 따른다:

1. **이슈 fetch** — `curl -s {{paperclipApiUrl}}/issues/{{taskId}}` → 본문(작업·데이터·출력 스키마) 확인
2. **분석** — 추가 명령 없이 내부 추론으로 수행
3. **코멘트 게시** — `curl -s -X POST {{paperclipApiUrl}}/issues/{{taskId}}/comments …` 로 JSON 코멘트 1건
4. **이슈 종결** — 이슈 status를 done으로 PATCH 후 즉시 종료

## 금지 명령 (예시 — SOUL 금지조항의 구체화)
- `apt/pip/npm install …`, `wget`, 임의 호스트로의 curl (paperclipApiUrl 외 전부)
- `env`, `printenv`, `cat ~/.hermes/.env` 등 시크릿 노출 명령
- `rm`, `chmod`, `kill`, 백그라운드 프로세스 생성

## 외부 도구(Pack)
현재 없음. Pack 추가는 조직 헌장 §3-3 승격 게이트 + adapter.yaml 갱신을 통해서만.
