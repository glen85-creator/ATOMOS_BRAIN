# TOOLS — ATOMOS_CTO

## 허용 toolsets
`terminal` 만 — 4단계 플레이북(이슈 fetch → 진단 → JSON 코멘트 → done).

## 진단 읽기 허용 (플레이북 2단계 내에서)
- `curl -s {{paperclipApiUrl}}/...` — 자기 이슈·자기 회사 읽기 GET 만
- 이슈 본문에 포함돼 전달된 로그/설정 텍스트 분석

## 금지
ATOMOS_HERMES 금지 목록과 동일. 추가로:
- **모든 변경 명령 금지** — docker/systemctl/파일 쓰기/패치 적용. 변경은 사람이 deploy/ 스크립트로만
