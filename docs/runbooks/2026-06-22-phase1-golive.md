# Phase 1 (self-hosted Hermes + MCP) Go-Live 런북

> 2026-06-22. **Phase 1은 코드 완료·머지레디** (`feat/atomos-phase1-hermes-mcp` / PR #53 — main +22 커밋, 충돌 0, MCP 서버 7모듈·마이그레이션 007·테스트 8파일, 스텁 0, final-review 종료). 남은 건 전부 **인프라/시크릿/DDL = 운영자(글렌)**. 코드 추가 작업 없음.
> 차단 요인이던 `chore/retire-sales-watch`는 이미 main 병합됨(stale) — 별도 세션 대기 불필요.
> 부모 계획: `docs/superpowers/plans/2026-06-21-phase1-hermes-mcp-keystone.md`.
> 차단 해제 대상: BRAIN v1+v2 3 브랜치(`feat/knowledge-ingest-lint`·`feat/brain-knowledge-layer`·`feat/brain-reference-page`).

## 의존 순서 한눈에
- **Phase A** (VPS 없이 MCP 경계 증명): `007 적용` → `시드` → `로컬 스모크`.
- **Phase B** (풀 e2e 키스톤): `PR#53 병합·배포` → `Railway env` → `VPS` → `e2e PoC`.

라벨: **[운영자]** = 글렌만 가능(인프라/시크릿/DDL) · **[에이전트]** = AI가 지금/즉시 대행 가능.

---

## PHASE A — MCP 절반 (VPS 불필요)

### A1. [운영자] 마이그레이션 007 적용  ← **사슬의 진짜 첫 관문**
Supabase SQL editor(타깃: HBS_POS_DATA_HUB / `nmeiydjbusrtyckrsyai`)에서 `FastAPI/migrations/007_atomos_phase1_mcp.sql` 실행.
생성물: 테이블 `atomos_knowledge`·`atomos_mcp_call_log`, RPC `atomos_knowledge_search(text,text[],text,int)`, anon revoke / service_role grant.

**검증 SQL** (적용 직후):
```sql
select to_regclass('public.atomos_knowledge')   is not null
   and to_regclass('public.atomos_mcp_call_log') is not null as tables_ok;   -- expect: t
select count(*) from pg_proc where proname = 'atomos_knowledge_search';      -- expect: 1
```

**롤백 SQL** (필요 시):
```sql
drop function if exists atomos_knowledge_search(text, text[], text, int);
drop table if exists atomos_mcp_call_log;
drop table if exists atomos_knowledge;
```
⚠️ 이미 BRAIN 008/009을 적용한 뒤라면 의존 객체가 있으니 **역순(009→008→007)** 으로 롤백.

### A2–A3. [에이전트] 시드 + 로컬 스모크 — 자동 러너
007 적용·검증 통과 후 한 번에:
```bash
bash ~/ATOMOS_BRAIN/scripts/phase1_phase_a.sh
```
기대 흐름: `seeded 2 docs` → 로컬 `uvicorn :8099` 기동 → `phase1_mcp_smoke.py`가 ①무인증 401 ②scope 필터 `knowledge_search` 2건 ③`atomos_mcp_call_log` 기록을 출력 → **`SMOKE PASS`**.
= MCP 경계(스코프·권한·감사)가 실데이터로 증명됨 = **Phase A 합격**(Hermes/VPS 없이).
> 러너는 `set -e`지만 스모크의 논리 실패는 종료코드로 안 잡힐 수 있음 — 출력에서 **`SMOKE PASS`** 문자열을 직접 확인할 것.

---

## PHASE B — 배포 + VPS 절반 (풀 e2e 키스톤)

### B1. [운영자 결정 · 에이전트 대행 가능] PR #53 main 병합 → Railway 자동 배포
⚠️ 선행: FastAPI main 워크트리의 **D-COGS 미커밋 변경 처리(커밋/stash)** 후 깨끗한 상태에서.
```bash
cd ~/FastAPI && git checkout main && git pull \
  && git merge --no-ff feat/atomos-phase1-hermes-mcp -m "Merge Phase 1: Hermes VPS + MCP server (#53)" \
  && git push origin main
```
로컬 merge+push로 PR #53 자동 머지표기(GCM 토큰). **"언제 머지"는 운영자 결정** — 에이전트는 명시 지시 시 대행.

### B2. [운영자] Railway env (web + worker 둘 다 설정)
- `ATOMOS_MCP_TOKEN` — 강한 랜덤(공백 금지 = fail-closed)
- `ATOMOS_MCP_SESSION_SECRET` — 강한 랜덤(엔진·MCP 공유 HMAC)
- `ATOMOS_MCP_BASE_URL` — `https://<engine>.up.railway.app/mcp/` (**끝슬래시 필수**; `/mcp`는 307 리다이렉트)
- `HERMES_VPS_HOST` / `HERMES_VPS_PORT` / `HERMES_VPS_USER` / `HERMES_VPS_SSH_KEY` / `HERMES_VPS_HOST_KEY`

### B3. [운영자] Hostinger VPS 프로비저닝
self-hosted Hermes: `hermes` 유저·바이너리 설치·SSH 키페어·`~/.hermes/config.yaml`(Docker 백엔드, `execute_code` 등 위험 toolset OFF, 우리 MCP만: `knowledge_search` + read-only). 연결 스모크 `hermes -z`.

### B4. [에이전트] 풀 e2e PoC
```bash
cd ~/FastAPI && source venv/bin/activate && set -a && source .env && set +a
python scripts/phase1_poc.py <real_sales_execution_id>
```
합격 4/4: `knowledge_search`≥1 · evidence 인용 · 구조화 출력 검증 통과 · `knowledge_used` 비공백. → "우리가 Hermes를 e2e 통제" = **Phase 1 키스톤 완료.**

---

## Phase 1 완료 후 → BRAIN 차단 해제
007 라이브 + Phase 1 병합 후 BRAIN v1/v2 ship:
1. 008 → 009 적용(순서 필수).
2. GH Actions 시크릿(`SUPABASE_URL`/`SUPABASE_SERVICE_KEY`) → knowledge ingest Action 라이브.
3. brain.py·`/admin/brain` 배포 → E2E(글렌=super_admin: 검색·노트뷰·백링크·본문 클릭).
4. hbs 브랜치를 병렬세션의 `App.tsx`/`client.ts`/`permissions.ts` 미커밋 변경과 머지 reconcile.
5. 3 브랜치 병합 후 `git worktree remove ~/ATOMOS_BRAIN-brain ~/FastAPI-brain ~/hbs-dashboard-brain`.

상세: `docs/superpowers/plans/2026-06-22-atomos-brain-knowledge-layer-v1.md`, `…-v2-backlinks.md`.
