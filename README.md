# ATOMOS_BRAIN

ATOMOS AI 본사(**ATOMOS_OFFICE** = Paperclip 조직)의 **정본 리포(org-as-code)**.

ATOMIC 콘솔(hbs-dashboard)이 감지한 일을 위임받는 AI 본사의 조직 정의 —
에이전트 로스터·모델·페르소나(SOUL)·툴셋(TOOLS)·하트비트(HEARTBEAT)·실행/기록/학습 원리 —
를 코드로 관리하고 VPS(Paperclip)에 배포한다.

## 정본 문서

- **[docs/ATOMOS_OFFICE_ORG_DESIGN.md](docs/ATOMOS_OFFICE_ORG_DESIGN.md)** — 조직 헌장 (SSOT)

## 구조

```
docs/      조직 헌장 (설계 정본)
org/       회사 메타·로스터·에이전트별 정의 번들 (SOUL/AGENTS/TOOLS/HEARTBEAT/adapter)
bridge/    감지→이슈→wakeup→회수→propose 디스패치 브리지        (M3)
patches/   hermes-paperclip-adapter ctx-path 패치 영구화        (M2)
deploy/    리포 → VPS 동기화 스크립트 (Paperclip REST)          (M2)
```

## 관련 리포

- **hbs-dashboard** — ATOMIC 콘솔 (React/Vercel). 설계 이력: `docs/superpowers/`
- **FastAPI** — 엔진 API `/api/atomic/engine/*` (Railway) + 감지·게이트·기록 테이블

## 원칙

1. 조직 정의의 정본은 이 리포. VPS는 배포 타깃 (역방향 수정 금지).
2. 시크릿 값 커밋 금지 — 키 이름 참조만.
3. 변경은 조직 헌장 갱신 → org/ 반영 → deploy 순서.
