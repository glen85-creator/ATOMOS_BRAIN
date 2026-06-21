# Phase 1 이어가기 (다른 세션용 연속 실행 핸드오프)

> 2026-06-21 기준. 이 문서 하나로 다른 세션에서 Phase 1 키스톤을 끝까지 진행한다.
> 상세 절차/코드는 같은 폴더의 `2026-06-21-phase1-hermes-mcp-keystone.md`(계획서) 참조. 메모리: `atomos-phase1-hermes-mcp-status.md`.

## 0. 지금까지 (DONE)
- **코드 완료**: FastAPI 브랜치 `feat/atomos-phase1-keystone` → **PR #53** (https://github.com/glen85-creator/FastAPI/pull/53). 13커밋, 신규파일 위주, **pytest 38 passed**. 적대적 3관점 리뷰 반영 끝.
- ATOMOS_BRAIN(main, 로컬커밋): 설계·계획·이 문서 + `knowledge/{global/grounding-rules.md, dept/sales/anomaly-playbook.md}` + `scripts/seed_atomos_knowledge.py`.
- 마이그레이션 파일: `FastAPI/migrations/007_atomos_phase1_mcp.sql`.
- ⚠️ **건드리지 말 것**: `~/FastAPI`는 `feat/atomos-phase1-hermes-mcp` 브랜치에 체크아웃돼 있고 **미커밋 D-COGS 작업(strategy.py·feed_classify.py + dcogs_*.py)** 이 있다. 코드는 PR 브랜치와 동일하니 검증·실행은 여기서 해도 되지만, **D-COGS 파일은 stage/commit 금지**.

## 1. 진행 순서 (의존성)
**A. MCP 절반 (VPS 없이 — 먼저 입증)** → **B. 배포+VPS 절반** → 키스톤 합격.

---

## A. MCP 절반 — "스코프 지식 over MCP" 실증

### A1. migration 007 적용 (Supabase MCP 있는 세션에서)
`FastAPI/migrations/007_atomos_phase1_mcp.sql` 실행(테이블 `atomos_knowledge`·`atomos_mcp_call_log` + RPC `atomos_knowledge_search`, anon REVOKE).
**확인:**
```sql
select to_regclass('public.atomos_knowledge') is not null
   and to_regclass('public.atomos_mcp_call_log') is not null as tables_ok;
select proname from pg_proc where proname = 'atomos_knowledge_search';  -- 1행
```

### A2. 지식 seed (service key만 필요 — Supabase MCP 불필요)
```bash
cd ~/FastAPI && set -a && source .env && set +a \
  && python ~/ATOMOS_BRAIN/scripts/seed_atomos_knowledge.py
```
기대: `... -> 201`(또는 204) ×2, `seeded 2 docs`.
**확인(SQL 또는 REST):** `select scope,title from atomos_knowledge order by scope;` → `dept:sales`·`global` 2행.

### A3. MCP 풀 스모크 (로컬 엔진, service key만)
스크립트: `~/ATOMOS_BRAIN/scripts/phase1_mcp_smoke.py` (이 머신에 이미 있음; 없으면 아래 "스모크 재생성" 참조).
```bash
cd ~/FastAPI && source venv/bin/activate
export ATOMOS_MCP_TOKEN=smoke-token
export ATOMOS_MCP_SESSION_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))")
set -a && source .env && set +a            # SUPABASE_URL/KEY
( uvicorn main:app --port 8099 --log-level warning & ) ; sleep 6
python ~/ATOMOS_BRAIN/scripts/phase1_mcp_smoke.py            # 같은 셸이라 위 export 상속
pkill -f 'uvicorn main:app' || true
```
**합격:** 출력 끝에 `SMOKE PASS ✅` + `knowledge_search` 결과에 지식 본문 + `call_log`에 `tool=knowledge_search, result_count>0`.
→ 여기까지면 **MCP 경계(스코프 강제·지식 회수)가 실데이터로 입증됨.** Hermes 없이 키스톤 절반 완료.

---

## B. 배포 + VPS 절반 — 풀 e2e 키스톤

### B1. PR #53 머지 → Railway 엔진 자동 배포(`/mcp` 포함)
머지 후 배포 완료 대기.

### B2. Railway env (엔진 서비스 Variables)
- `ATOMOS_MCP_TOKEN` = 강한 랜덤 (엔진↔VPS 공유 Bearer)
- `ATOMOS_MCP_SESSION_SECRET` = 강한 랜덤 (**엔진 전용**; 미설정이면 토큰검증 fail-closed → PoC 안 됨)
- `ATOMOS_MCP_BASE_URL` = `https://<engine-railway-도메인>/mcp/` (**trailing slash 필수**)
- `HERMES_VPS_HOST`·`HERMES_VPS_USER`(hermes)·`HERMES_VPS_SSH_KEY`(PEM 전체)
- (선택) `HERMES_VPS_HOST_KEY` = `ssh-keyscan -H <VPS_HOST>` 출력 1줄(MITM 차단)
**확인:** `curl -s -o /dev/null -w '%{http_code}' -X POST https://<engine>/mcp/ -d '{}'` → **401**. (slash 없는 `/mcp`는 307.)

### B3. VPS self-hosted Hermes 설치·설정 → 계획서 **Task 15** 그대로
요지: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh|bash` → `~/.hermes/.env`(OPENROUTER_API_KEY, `ATOMOS_MCP_URL=https://<engine>/mcp/`, `ATOMOS_MCP_TOKEN`=B2와 동일) → `~/.hermes/config.yaml`(provider openrouter / terminal.backend docker / approvals.mode smart / `agent.disabled_toolsets`=`hermes tools --summary`에서 본 코드·셸 toolset / `mcp_servers.atomos`: url `${ATOMOS_MCP_URL}` + headers `Authorization: Bearer ${ATOMOS_MCP_TOKEN}` + `X-Atomos-Session: ${ATOMOS_SESSION_TOKEN}` + `tools.include: [knowledge_search, data_sales_history]`).
**확인:** `hermes config check` / `hermes mcp test atomos`(도구 2개 노출) / `hermes -z "출력: {\"ping\":\"pong\"}" --toolsets mcp_atomos_knowledge_search,mcp_atomos_data_sales_history`.

### B4. e2e PoC → 계획서 **Task 16**
```bash
# 실 매출 안건 1건 고르기 (Supabase)
#   select execution_id,title,trigger_context->>'st_id' st_id
#   from strategy_executions where trigger_context->>'domain'='sales' order by created_at desc limit 5;
cd ~/FastAPI && source venv/bin/activate && set -a && source .env && set +a \
  && python scripts/phase1_poc.py <execution_id>
```
**합격(4개):** `ok:true` / `mcp_calls.knowledge_search>=1` + call_log scope에 `store:<st_id>`·`dept:sales` / `result.diagnosis`에 evidence 수치 인용 / `result.knowledge_used` 비어있지 않음.
→ **"우리가 Hermes를 통제 구동 가능" = Phase 1 키스톤 합격.**

---

## 절대 잊지 말 것 (gotcha)
- **MCP URL은 항상 `/mcp/`**(trailing slash). `/mcp`는 307 리다이렉트로 인증헤더 유실 위험.
- **`ATOMOS_MCP_TOKEN`은 엔진(Railway)과 VPS `.env` 동일값**이어야 함. `ATOMOS_MCP_SESSION_SECRET`은 **엔진에만**(VPS 불필요 — 엔진이 토큰 발급, Hermes는 헤더로 전달만).
- **`data_sales_history`는 `store_master_v2.pos_st_uid`** 사용(st_uid 아님; `sales_closing_monthly.st_uid`=POS uid). 실DB 매핑 일치.
- 지식검색 백엔드는 Phase1=FTS. **pgvector + git→CI 색인은 Phase2.** 인터페이스 동일.
- D-COGS 미커밋 트리 무오염 유지.

## 스모크 재생성 (다른 머신/리부트로 /tmp 비었을 때)
`~/ATOMOS_BRAIN/scripts/phase1_mcp_smoke.py`가 없으면: 세션토큰 발급 후 `mcp.client.streamable_http.streamablehttp_client(url="http://localhost:8099/mcp/", headers={Authorization: Bearer <ATOMOS_MCP_TOKEN>, X-Atomos-Session: <minted>})` → `ClientSession.initialize()` → `call_tool("knowledge_search", {"query":"매출 급락 대응"})` 후 `atomos_mcp_call_log` 조회. (토큰 mint = `app.mcp_server.session_token.mint_session_token`.)
