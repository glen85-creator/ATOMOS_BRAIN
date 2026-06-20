# Phase 1 (키스톤) — self-hosted Hermes VPS + 우리 MCP 서버 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매출 안건 1건이 우리 MCP 서버로 스코프 지식을 받아 self-hosted Hermes에서 분석 → 구조화 출력 회수까지 e2e로 돌려 "우리가 Hermes를 통제 구동 가능"을 입증한다.

**Architecture:** 엔진(FastAPI/Railway)이 안건별 단명(短命) 스코프 세션 토큰을 발급하고 VPS의 self-hosted Hermes를 SSH로 비대화 트리거한다. Hermes는 우리 MCP 서버(엔진에 마운트, `/mcp`)의 read-only 도구(`knowledge_search`·`data_sales_history`)만 화이트리스트로 사용하며, 스코프/권한은 MCP 서버가 세션 헤더로 강제(에이전트 우회 불가)한다. 출력은 단일 JSON으로 회수하여 lite 검증 게이트로 통과/재시도/실패-표면화한다.

**Tech Stack:** Python 3.12 · FastAPI · MCP Python SDK(FastMCP, streamable-HTTP) · Supabase(PostgreSQL, FTS) · paramiko(SSH) · self-hosted Hermes(Nous Research, Docker backend) · OpenRouter(모델 제공자) · pytest/pytest-asyncio.

---

## 설계 출처 / 범위 메모

- 정본 설계: `ATOMOS_BRAIN/docs/superpowers/specs/2026-06-20-pipeline-redesign-design.md` (특히 §4 Hermes 계약, §4b 우리 MCP 서버, §5 지식 wiki, §10 Phase 1).
- **이 계획은 §10 Phase 1(키스톤)만 다룬다.** Phase 2~4(매출 수직 슬라이스 전체·검증게이트 풀버전·실행 레지스트리·측정·보고게이트·디커미션·도메인 확장)는 후속.
- **의도적 Phase-1 단순화(설계와 정합):**
  - 지식 검색은 `knowledge_search(query, ctx)` **인터페이스를 고정**하되, Phase 1 백엔드는 **scope-필터 + Postgres FTS**(seeded `atomos_knowledge` 테이블)로 구현한다. **pgvector 시맨틱 랭킹 + git→CI 색인 파이프라인(§5)은 Phase 2**에서 같은 인터페이스 뒤로 교체한다. (키스톤 리스크는 "Hermes 통제"이지 랭킹 알고리즘이 아니므로 우선 경계를 입증.)
  - MCP 도구는 §4b의 두 계열 대표 1개씩만: 지식(`knowledge_search`) + read-only 데이터(`data_sales_history`). `context.weather`/`context.trade_area`(§3c 프로바이더 프레임워크 의존)는 Phase 2.
  - 실행(쓰기) 도구는 없음(모델 A: Hermes=분석+읽기전용). 실행 안전도구 레지스트리(§3d)는 Phase 2.

## 구현 후 리뷰 반영 변경 (2026-06-21, 적대적 3관점 리뷰)

코드 Task 0·2–13 구현 완료 후 보안/통합/스펙 리뷰에서 나온 실이슈를 반영함(브랜치 `feat/atomos-phase1-hermes-mcp`, 38 테스트 통과). operator 단계 수행 전 숙지:
- **(critical) blank HMAC secret fail-closed**: `ATOMOS_MCP_SESSION_SECRET` 미설정이면 mint/verify가 거부(=스코프 위조 불가). → Railway env에 **반드시 강한 값** 설정(미설정 시 PoC 동작 안 함).
- **(critical) `data_sales_history`는 `store_master_v2.pos_st_uid`로 해소**(st_uid 아님). `sales_closing_monthly.st_uid` = POS uid = `pos_st_uid`(`atomos_bridge._map_st_uid` 동일). → Task 1 컬럼 확인은 `pos_st_uid`로 갈음됨.
- **(important) MCP URL은 trailing slash `/mcp/`** 필수 — `/mcp`는 FastAPI가 `307→/mcp/` 리다이렉트(인증 헤더 유실 위험). 아래 모든 URL은 `/mcp/`로 기재됨.
- **(important) SSH host-key 핀**: `HERMES_VPS_HOST_KEY`(known_hosts 1줄, `ssh-keyscan -H <host>`로 획득) 설정 시 RejectPolicy로 MITM 차단. 미설정이면 AutoAdd+경고.
- **(중요) DDL은 in-repo 마이그레이션화**: `FastAPI/migrations/007_atomos_phase1_mcp.sql`(테이블 2 + RPC, anon REVOKE). Task 5 Step 3의 SQL을 이 파일로 적용.
- **(완료) Task 5 코드 산출물 생성됨**: `ATOMOS_BRAIN/knowledge/{global/grounding-rules.md, dept/sales/anomaly-playbook.md}` + `scripts/seed_atomos_knowledge.py`. (Supabase 테이블 생성 후 seed 실행만 남음.)
- 부가 강화: Bearer 상수시간 비교(`hmac.compare_digest`), `extract_json` 다중펜스 견고화, 도구표면 drift 회귀 테스트.

## 사전 조건 / 접근 (operator 실행 — 승인 필요)

다음은 코드가 아니라 외부 자원 접근이며, **운영자(글렌)가 직접 실행**한다(과거 VPS SSH·prod DDL은 명시 승인 전 차단됨):

1. **VPS SSH 접근**: Hostinger VPS에 sudo 가능한 셸. Hermes 전용 리눅스 유저 `hermes` 생성 예정.
2. **Supabase DDL 권한**: `atomos_knowledge`·`atomos_mcp_call_log` 테이블 + `atomos_knowledge_search` RPC 생성(SQL editor 또는 MCP). [[supabase-secdef-rpc-anon-grant]] 규칙 준수(anon REVOKE).
3. **OpenRouter API 키**: Hermes 모델 제공자용(VPS `~/.hermes/.env`).
4. **Railway 환경변수**: 엔진 서비스에 MCP/VPS 관련 신규 settings 등록(Task 12 목록).

## 테스트 실행 환경 메모 (WSL)

리포·venv는 WSL Ubuntu에 있다([[fastapi-runs-in-wsl]]). 모든 `pytest`/`python` 명령은 WSL 셸에서 실행한다. 리포 루트는 `~/FastAPI`(= `/home/glen_85/FastAPI`).

- 표준형(이 문서의 모든 Run 명령): `cd ~/FastAPI && source venv/bin/activate && <명령>`
- Windows 측에서 호출 시: `wsl.exe bash -lc "cd ~/FastAPI && source venv/bin/activate && <명령>"`

각 Task의 `Run:`은 WSL 셸 기준 명령으로 적는다.

---

## 파일 구조 (생성/수정)

**FastAPI 리포 (`~/FastAPI`):**
- Create `app/mcp_server/__init__.py` — 패키지 초기화.
- Create `app/mcp_server/session_token.py` — 스코프 세션 토큰 mint/verify(HMAC).
- Create `app/mcp_server/context.py` — 현재 세션 스코프 contextvar + 스코프 빌더.
- Create `app/mcp_server/auth.py` — ASGI 미들웨어(Bearer 검증 + 세션 헤더→contextvar).
- Create `app/mcp_server/tools.py` — `knowledge_search`·`data_sales_history` 구현(Supabase read-only).
- Create `app/mcp_server/call_log.py` — MCP 호출 로깅(`atomos_mcp_call_log`).
- Create `app/mcp_server/server.py` — FastMCP 인스턴스 + 도구 등록 + ASGI 앱(`mcp_asgi`).
- Modify `main.py` — lifespan 배선 + `/mcp` 마운트.
- Modify `app/core/config.py` — MCP/VPS settings 추가.
- Create `app/services/analysis_gate.py` — 분석 출력 스키마 검증(lite 게이트).
- Create `app/services/hermes_prompt.py` — 안건→ANALYST 역할 프롬프트 빌더.
- Create `app/services/hermes_runner.py` — SSH 트리거 + JSON 추출 + 재시도.
- Create `app/services/atomos_phase1_poc.py` — PoC 오케스트레이션(`run_poc`).
- Create `scripts/phase1_poc.py` — PoC 실행 스크립트(운영자/CLI).
- Modify `requirements.txt` — `mcp`, `paramiko` 추가.
- Create `requirements-dev.txt` — `pytest`, `pytest-asyncio`.
- Create `tests/` (신규 디렉터리) + 각 테스트 파일.

**ATOMOS_BRAIN 리포 (`~/ATOMOS_BRAIN`):**
- Create `knowledge/dept/sales/anomaly-playbook.md` — D-SALES 참조지식(real).
- Create `knowledge/global/grounding-rules.md` — 분석 그라운딩 규칙(real).
- Create `scripts/seed_atomos_knowledge.py` — markdown→`atomos_knowledge` 적재.

**VPS (`hermes` 유저 홈):**
- Create `~/.hermes/config.yaml` — Hermes 설정.
- Create `~/.hermes/.env` — OpenRouter 키 + MCP URL/토큰.

---

## Task 0: 의존성 + 테스트 스캐폴드

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: requirements.txt에 런타임 의존성 추가**

`requirements.txt` 맨 아래에 추가:

```text
# ATOMOS Phase 1 — MCP 서버 + Hermes 트리거
mcp>=1.2.0
paramiko>=3.4.0
```

- [ ] **Step 2: requirements-dev.txt 생성**

```text
-r requirements.txt
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 3: tests 패키지 + conftest 생성**

`tests/__init__.py` (빈 파일):

```python
```

`tests/conftest.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 단위 테스트가 settings import만으로 죽지 않도록 최소 더미 env (실 호출 없음)
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
os.environ.setdefault("ATOMOS_MCP_TOKEN", "test-mcp-token")
os.environ.setdefault("ATOMOS_MCP_SESSION_SECRET", "test-session-secret")
```

- [ ] **Step 4: 의존성 설치**

Run: `cd ~/FastAPI && source venv/bin/activate && pip install -r requirements-dev.txt`
Expected: `mcp`, `paramiko`, `pytest`, `pytest-asyncio` 설치 성공(이미 있으면 "already satisfied").

- [ ] **Step 5: pytest 동작 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/ -q`
Expected: `no tests ran`(에러 없이 0 collected) — 스캐폴드 정상.

- [ ] **Step 6: Commit**

```bash
cd ~/FastAPI && git add requirements.txt requirements-dev.txt tests/__init__.py tests/conftest.py
git commit -m "chore(atomos): phase1 test scaffold + mcp/paramiko deps"
```

---

## Task 1: 매출 테이블 스키마 확인 (discovery)

Phase-1 `data_sales_history`가 `sales_closing_monthly`(st_uid 키)를 읽고, 안건의 `st_id`를 `store_master_v2`로 `st_uid`로 해소한다. 코딩 전에 컬럼을 실측한다.

**Files:**
- Create: `scripts/phase1_check_schema.py`

- [ ] **Step 1: 확인 스크립트 작성**

`scripts/phase1_check_schema.py`:

```python
"""Phase1: data_sales_history가 의존하는 컬럼 실측. 읽기 전용."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.supabase import get_supabase_sync

c = get_supabase_sync()

sm = c.table("store_master_v2").select("st_id,st_uid,store_name,br_id").limit(1).execute()
print("store_master_v2 sample:", sm.data)

scm = c.table("sales_closing_monthly").select("*").limit(1).execute()
print("sales_closing_monthly columns:", list((scm.data or [{}])[0].keys()) if scm.data else "EMPTY")
print("sales_closing_monthly sample:", scm.data)
```

- [ ] **Step 2: 실행하여 컬럼 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && python scripts/phase1_check_schema.py`
Expected: `store_master_v2`에 `st_id`·`st_uid`·`store_name`·`br_id`가 존재하고, `sales_closing_monthly`에 `ym`·`st_uid`·`rev`·`cnt`가 존재함을 출력으로 확인.

만약 `store_master_v2`에 `st_uid`가 없으면(예외 케이스): 출력에서 st_id↔st_uid 매핑 테이블/컬럼을 찾아 Task 6 Step 3의 해소 쿼리 테이블명을 그 값으로 바꾼다(그 외 로직 동일).

- [ ] **Step 3: Commit**

```bash
cd ~/FastAPI && git add scripts/phase1_check_schema.py
git commit -m "chore(atomos): phase1 sales schema discovery script"
```

---

## Task 2: 스코프 세션 토큰 (HMAC mint/verify)

엔진이 안건별로 `{execution_id, store_id, brand_id, dept, role, exp}`를 서명 발급하고, MCP 서버가 검증·복호한다. 에이전트는 이 토큰을 보지 못하며 스코프를 조작할 수 없다.

**Files:**
- Create: `app/mcp_server/__init__.py`
- Create: `app/mcp_server/session_token.py`
- Test: `tests/test_session_token.py`

- [ ] **Step 1: 패키지 init 생성**

`app/mcp_server/__init__.py` (빈 파일):

```python
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/test_session_token.py`:

```python
import time
import pytest

from app.mcp_server.session_token import (
    mint_session_token,
    verify_session_token,
    SessionTokenError,
)

SECRET = "unit-secret"


def test_roundtrip_returns_payload():
    tok = mint_session_token(
        execution_id="exec-1", store_id="ST-1", brand_id="BR-1",
        dept="sales", role="ANALYST", ttl_sec=60, secret=SECRET,
    )
    payload = verify_session_token(tok, secret=SECRET)
    assert payload["execution_id"] == "exec-1"
    assert payload["store_id"] == "ST-1"
    assert payload["brand_id"] == "BR-1"
    assert payload["dept"] == "sales"
    assert payload["role"] == "ANALYST"


def test_tampered_signature_rejected():
    tok = mint_session_token(
        execution_id="exec-1", store_id="ST-1", brand_id="BR-1",
        dept="sales", role="ANALYST", ttl_sec=60, secret=SECRET,
    )
    body, _, sig = tok.partition(".")
    tampered = body + "." + ("0" * len(sig))
    with pytest.raises(SessionTokenError):
        verify_session_token(tampered, secret=SECRET)


def test_wrong_secret_rejected():
    tok = mint_session_token(
        execution_id="e", store_id="s", brand_id="b",
        dept="sales", role="ANALYST", ttl_sec=60, secret=SECRET,
    )
    with pytest.raises(SessionTokenError):
        verify_session_token(tok, secret="other")


def test_expired_rejected():
    tok = mint_session_token(
        execution_id="e", store_id="s", brand_id="b",
        dept="sales", role="ANALYST", ttl_sec=-1, secret=SECRET,
    )
    with pytest.raises(SessionTokenError):
        verify_session_token(tok, secret=SECRET)
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_session_token.py -q`
Expected: FAIL — `ModuleNotFoundError: app.mcp_server.session_token`.

- [ ] **Step 4: 구현 작성**

`app/mcp_server/session_token.py`:

```python
"""스코프 세션 토큰 — 엔진이 발급, MCP 서버가 검증. 형식: b64url(payload).b64url(hmac).

페이로드는 안건별 스코프/권한을 담는다. 에이전트는 토큰을 보지 못하므로(엔진→Hermes env→MCP 헤더)
스코프 위변조가 불가능하다.
"""
import base64
import hashlib
import hmac
import json
import time


class SessionTokenError(Exception):
    pass


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(body: str, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256)
    return _b64u_encode(mac.digest())


def mint_session_token(*, execution_id: str, store_id: str, brand_id: str,
                       dept: str, role: str, ttl_sec: int, secret: str) -> str:
    payload = {
        "execution_id": execution_id,
        "store_id": store_id,
        "brand_id": brand_id,
        "dept": dept,
        "role": role,
        "exp": int(time.time()) + int(ttl_sec),
    }
    body = _b64u_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return body + "." + _sign(body, secret)


def verify_session_token(token: str, *, secret: str) -> dict:
    try:
        body, sep, sig = token.partition(".")
        if not sep or not body or not sig:
            raise SessionTokenError("malformed token")
        expected = _sign(body, secret)
        if not hmac.compare_digest(sig, expected):
            raise SessionTokenError("bad signature")
        payload = json.loads(_b64u_decode(body))
    except SessionTokenError:
        raise
    except Exception as e:  # decode/json 실패
        raise SessionTokenError(f"decode error: {e}") from e
    if int(payload.get("exp", 0)) < int(time.time()):
        raise SessionTokenError("expired")
    return payload
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_session_token.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
cd ~/FastAPI && git add app/mcp_server/__init__.py app/mcp_server/session_token.py tests/test_session_token.py
git commit -m "feat(atomos-mcp): scoped session token mint/verify (hmac)"
```

---

## Task 3: 세션 contextvar + 스코프 빌더

검증된 세션 페이로드를 요청 스코프로 보관하고, 허용 지식 스코프 리스트를 산출한다.

**Files:**
- Create: `app/mcp_server/context.py`
- Test: `tests/test_scope_builder.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_scope_builder.py`:

```python
from app.mcp_server.context import build_allowed_scopes


def test_includes_all_scope_levels():
    session = {"store_id": "ST-9", "brand_id": "BR-2", "dept": "sales", "role": "ANALYST"}
    scopes = build_allowed_scopes(session)
    assert "global" in scopes
    assert "dept:sales" in scopes
    assert "brand:BR-2" in scopes
    assert "store:ST-9" in scopes


def test_omits_missing_levels():
    session = {"store_id": "", "brand_id": None, "dept": "sales", "role": "ANALYST"}
    scopes = build_allowed_scopes(session)
    assert "global" in scopes
    assert "dept:sales" in scopes
    assert all(not s.startswith("brand:") for s in scopes)
    assert all(not s.startswith("store:") for s in scopes)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_scope_builder.py -q`
Expected: FAIL — `ModuleNotFoundError: app.mcp_server.context`.

- [ ] **Step 3: 구현 작성**

`app/mcp_server/context.py`:

```python
"""요청 단위 세션 스코프 보관 + 허용 지식 스코프 산출."""
from contextvars import ContextVar

# 검증된 세션 페이로드(dict) 또는 None. auth 미들웨어가 set, 도구가 get.
current_session: ContextVar[dict | None] = ContextVar("current_session", default=None)


def build_allowed_scopes(session: dict) -> list[str]:
    """세션 스코프 → knowledge_search가 허용할 scope 문자열 리스트."""
    scopes = ["global"]
    dept = (session.get("dept") or "").strip()
    brand = (session.get("brand_id") or "").strip() if session.get("brand_id") else ""
    store = (session.get("store_id") or "").strip() if session.get("store_id") else ""
    if dept:
        scopes.append(f"dept:{dept}")
    if brand:
        scopes.append(f"brand:{brand}")
    if store:
        scopes.append(f"store:{store}")
    return scopes
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_scope_builder.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/FastAPI && git add app/mcp_server/context.py tests/test_scope_builder.py
git commit -m "feat(atomos-mcp): session contextvar + allowed-scope builder"
```

---

## Task 4: config settings 추가

**Files:**
- Modify: `app/core/config.py`

- [ ] **Step 1: Settings에 Phase-1 필드 추가**

`app/core/config.py`의 `class Settings`에서 `model_config = SettingsConfigDict(...)` **바로 위**에 추가:

```python
    # ── ATOMOS Phase 1: self-hosted Hermes + MCP 서버 ──────
    # MCP 서버(엔진 마운트 /mcp)
    ATOMOS_MCP_TOKEN: str = ""            # 서버-서버 Bearer (Hermes→MCP 정적 인증). 빈값이면 모든 호출 401.
    ATOMOS_MCP_SESSION_SECRET: str = ""   # 세션 토큰 HMAC 시크릿 (엔진·MCP 공유)
    ATOMOS_MCP_BASE_URL: str = ""         # 예: https://<engine>.up.railway.app/mcp/ (trailing slash 필수; /mcp는 307→/mcp/)
    ATOMOS_MCP_SESSION_TTL_SEC: int = 600 # 세션 토큰 수명
    # VPS Hermes (SSH 트리거)
    HERMES_VPS_HOST: str = ""
    HERMES_VPS_PORT: int = 22
    HERMES_VPS_USER: str = "hermes"
    HERMES_VPS_SSH_KEY: str = ""          # private key PEM (멀티라인). 빈값이면 트리거 비활성.
    HERMES_BIN: str = "hermes"            # VPS 내 hermes 실행 경로(.bashrc PATH 가정)
    HERMES_MODEL: str = "anthropic/claude-sonnet-4.6"  # 참조용(실 모델은 VPS config.yaml)
    HERMES_TRIGGER_TIMEOUT_SEC: int = 300
    HERMES_MAX_RETRIES: int = 2           # 출력 검증 실패 시 재시도 횟수
```

- [ ] **Step 2: import 검증**

Run: `cd ~/FastAPI && source venv/bin/activate && python -c "from app.core.config import settings; print(settings.ATOMOS_MCP_SESSION_TTL_SEC, settings.HERMES_MAX_RETRIES)"`
Expected: `600 2`

- [ ] **Step 3: Commit**

```bash
cd ~/FastAPI && git add app/core/config.py
git commit -m "feat(atomos): phase1 MCP/Hermes settings"
```

---

## Task 5: 지식 소스 markdown + Supabase 테이블/RPC + seed

`knowledge_search`가 읽을 실데이터를 준비한다. 소스는 `ATOMOS_BRAIN/knowledge/`(폴더=스코프), 색인은 Supabase `atomos_knowledge`(FTS).

**Files:**
- Create: `~/ATOMOS_BRAIN/knowledge/global/grounding-rules.md`
- Create: `~/ATOMOS_BRAIN/knowledge/dept/sales/anomaly-playbook.md`
- Create: `~/ATOMOS_BRAIN/scripts/seed_atomos_knowledge.py`
- (operator) Supabase DDL

- [ ] **Step 1: 글로벌 그라운딩 지식 작성**

`~/ATOMOS_BRAIN/knowledge/global/grounding-rules.md`:

```markdown
---
scope: global
read_roles: [ANALYST]
title: 분석 그라운딩 규칙
---

# 분석 그라운딩 규칙

- 제공된 evidence 수치와 도구로 조회한 데이터만 근거로 사용한다. 외부 추정·일반론으로 수치를 만들지 않는다.
- 모든 결론은 인용한 수치(z, dod_delta_pct, mom_delta_pct, gross, mu 등)와 연결한다.
- 외부 요인(휴무·날씨·행사) 가능성이 있으면 단정 대신 "확인 필요"로 표시한다.
- 제안 액션은 반드시 실행 가능한 안전도구 태그(tool_tag) 중 하나에 매핑한다.
```

- [ ] **Step 2: 매출 부서 플레이북 작성**

`~/ATOMOS_BRAIN/knowledge/dept/sales/anomaly-playbook.md`:

```markdown
---
scope: dept:sales
read_roles: [ANALYST]
title: 매출 급락 대응 플레이북 (D-SALES)
---

# 매출 급락 대응 플레이북

## 감지 의미
- z는 같은 요일 대비 robust 표준화 점수. z ≤ -3 = critical, -2 ≥ z > -3 = warning.
- dod_delta_pct = 전일 대비, mom_delta_pct = 전월 동기 대비 변화율(분수).

## 초동 점검 순서
1. 운영 아티팩트 배제: gross=0(휴무/미수집), 수집 결함일 여부.
2. 외부 요인: 우천·한파·인근 행사·공휴일.
3. 내부 요인: 운영 차질, 메뉴 품절, 인력.

## 권고 패턴
- 외부 요인 우세: 관망 + 점주 알림(notify), 데이터 확인(flag_data_issue).
- 내부 요인 의심: 담당 배정(create_task) + 의사결정 기록(record_decision).
- 마케팅 캠페인 필요: handoff_marketing.
```

- [ ] **Step 3: (operator) Supabase 테이블 + RPC 생성**

Supabase SQL editor에서 실행(또는 MCP DDL). [[supabase-secdef-rpc-anon-grant]]에 따라 anon 권한 차단:

```sql
create table if not exists atomos_knowledge (
  id uuid primary key default gen_random_uuid(),
  scope text not null,
  read_roles text[] not null default array['ANALYST'],
  title text not null,
  body text not null,
  source_path text,
  ts tsvector generated always as
    (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(body,''))) stored,
  created_at timestamptz not null default now()
);
create index if not exists atomos_knowledge_ts_idx on atomos_knowledge using gin(ts);
create index if not exists atomos_knowledge_scope_idx on atomos_knowledge(scope);

create table if not exists atomos_mcp_call_log (
  id uuid primary key default gen_random_uuid(),
  ts timestamptz not null default now(),
  execution_id text,
  tool text not null,
  scope_json jsonb,
  query text,
  result_count int
);

create or replace function atomos_knowledge_search(
  p_query text, p_scopes text[], p_role text, p_limit int default 5
) returns table(id uuid, scope text, title text, body text, source_path text, rank real)
language sql stable as $$
  select k.id, k.scope, k.title, k.body, k.source_path,
         ts_rank(k.ts, plainto_tsquery('simple', p_query)) as rank
  from atomos_knowledge k
  where k.scope = any(p_scopes)
    and p_role = any(k.read_roles)
    and (coalesce(p_query,'') = '' or k.ts @@ plainto_tsquery('simple', p_query))
  order by rank desc, k.created_at desc
  limit greatest(p_limit, 1);
$$;

revoke all on function atomos_knowledge_search(text, text[], text, int) from anon;
grant execute on function atomos_knowledge_search(text, text[], text, int) to service_role;
```

검증: `select * from atomos_knowledge_search('급락', array['global','dept:sales'], 'ANALYST', 5);` → (seed 전이므로) 0 rows, 에러 없음.

- [ ] **Step 4: seed 스크립트 작성**

`~/ATOMOS_BRAIN/scripts/seed_atomos_knowledge.py`:

```python
"""ATOMOS_BRAIN/knowledge/**.md → Supabase atomos_knowledge 적재(멱등: source_path 기준 upsert).

frontmatter(scope, read_roles, title) 파싱. 엔진 venv/Supabase 자격으로 실행.
사용: SUPABASE_URL/SUPABASE_SERVICE_KEY env 설정 후
  python scripts/seed_atomos_knowledge.py
"""
import glob
import os
import re

import requests

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")


def parse(path: str) -> dict:
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    meta_block, body = (m.group(1), m.group(2)) if m else ("", raw)
    meta = {}
    for line in meta_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    scope = meta.get("scope") or "global"
    roles_raw = meta.get("read_roles", "[ANALYST]").strip("[]")
    roles = [r.strip() for r in roles_raw.split(",") if r.strip()] or ["ANALYST"]
    title = meta.get("title") or os.path.basename(path)
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    return {"scope": scope, "read_roles": roles, "title": title,
            "body": body.strip(), "source_path": rel}


def main():
    files = glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True)
    rows = [parse(f) for f in files]
    for row in rows:
        # 멱등: 같은 source_path 삭제 후 삽입
        requests.delete(f"{URL}/rest/v1/atomos_knowledge?source_path=eq.{row['source_path']}",
                        headers=H, timeout=30)
        r = requests.post(f"{URL}/rest/v1/atomos_knowledge",
                          headers={**H, "Prefer": "return=minimal"}, json=row, timeout=30)
        print(row["source_path"], "->", r.status_code)
    print(f"seeded {len(rows)} docs")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: seed 실행 + 검증**

Run: `cd ~/FastAPI && source venv/bin/activate && set -a && source .env && set +a && python ~/ATOMOS_BRAIN/scripts/seed_atomos_knowledge.py`
Expected: 각 `.md`가 `-> 201`(또는 204), `seeded 2 docs`.

검증(Supabase): `select scope,title from atomos_knowledge order by scope;` → `dept:sales`·`global` 2행.

- [ ] **Step 6: Commit (양쪽 리포)**

```bash
cd ~/ATOMOS_BRAIN && git add knowledge/ scripts/seed_atomos_knowledge.py
git commit -m "feat(knowledge): phase1 D-SALES seed (grounding + anomaly playbook)"
```

---

## Task 6: MCP 도구 구현 (`knowledge_search`·`data_sales_history`)

스코프는 contextvar(검증된 세션)에서만 가져온다. 도구 인자로 스코프를 받지 않는다(에이전트 우회 차단).

**Files:**
- Create: `app/mcp_server/tools.py`
- Test: `tests/test_mcp_tools.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_mcp_tools.py`:

```python
import pytest

from app.mcp_server import tools
from app.mcp_server.context import current_session


class FakeResp:
    def __init__(self, data):
        self.data = data


class FakeRPC:
    def __init__(self, store, captured):
        self._store = store
        self._captured = captured

    def execute(self):
        return FakeResp(self._store)


class FakeQuery:
    def __init__(self, rows, captured):
        self._rows = rows
        self._captured = captured

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._captured.setdefault("eq", []).append((col, val))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def execute(self):
        return FakeResp(self._rows)


class FakeClient:
    def __init__(self, rpc_rows=None, tables=None, captured=None):
        self._rpc_rows = rpc_rows or []
        self._tables = tables or {}
        self.captured = captured if captured is not None else {}

    def rpc(self, name, params):
        self.captured["rpc"] = (name, params)
        return FakeRPC(self._rpc_rows, self.captured)

    def table(self, name):
        self.captured.setdefault("tables", []).append(name)
        return FakeQuery(self._tables.get(name, []), self.captured)


def test_knowledge_search_passes_scoped_args(monkeypatch):
    captured = {}
    fake = FakeClient(rpc_rows=[{"id": "1", "scope": "dept:sales", "title": "T",
                                 "body": "B", "source_path": "p", "rank": 0.5}],
                      captured=captured)
    monkeypatch.setattr(tools, "_client", lambda: fake)
    monkeypatch.setattr(tools, "_log_call", lambda **k: None)
    token = current_session.set({"execution_id": "e", "store_id": "ST-1",
                                 "brand_id": "BR-1", "dept": "sales", "role": "ANALYST"})
    try:
        out = tools._knowledge_search_impl("급락 원인")
    finally:
        current_session.reset(token)
    name, params = captured["rpc"]
    assert name == "atomos_knowledge_search"
    assert params["p_role"] == "ANALYST"
    assert set(["global", "dept:sales", "brand:BR-1", "store:ST-1"]).issubset(set(params["p_scopes"]))
    assert out["results"][0]["title"] == "T"
    assert out["count"] == 1


def test_tools_reject_without_session(monkeypatch):
    monkeypatch.setattr(tools, "_client", lambda: FakeClient())
    monkeypatch.setattr(tools, "_log_call", lambda **k: None)
    token = current_session.set(None)
    try:
        with pytest.raises(PermissionError):
            tools._knowledge_search_impl("q")
        with pytest.raises(PermissionError):
            tools._data_sales_history_impl(6)
    finally:
        current_session.reset(token)


def test_data_sales_history_resolves_st_uid(monkeypatch):
    captured = {}
    fake = FakeClient(
        tables={
            "store_master_v2": [{"st_uid": "U-9", "store_name": "테스트점"}],
            "sales_closing_monthly": [{"ym": "2026-05", "rev": 1000, "cnt": 50}],
        },
        captured=captured,
    )
    monkeypatch.setattr(tools, "_client", lambda: fake)
    monkeypatch.setattr(tools, "_log_call", lambda **k: None)
    token = current_session.set({"execution_id": "e", "store_id": "ST-9",
                                 "brand_id": "BR-1", "dept": "sales", "role": "ANALYST"})
    try:
        out = tools._data_sales_history_impl(6)
    finally:
        current_session.reset(token)
    assert out["st_uid"] == "U-9"
    assert out["months"][0]["ym"] == "2026-05"
    assert ("st_id", "ST-9") in captured.get("eq", [])
    assert ("st_uid", "U-9") in captured.get("eq", [])
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_mcp_tools.py -q`
Expected: FAIL — `ModuleNotFoundError: app.mcp_server.tools`.

- [ ] **Step 3: 구현 작성**

`app/mcp_server/tools.py`:

```python
"""MCP read-only 도구 구현(순수 함수). 스코프는 contextvar(검증된 세션)에서만 취득.

FastMCP 도구는 server.py에서 이 _impl 들을 감싼다. 여기서는 테스트 가능한 순수 로직만.
"""
from app.core.supabase import get_supabase_sync
from app.mcp_server.context import current_session, build_allowed_scopes
from app.mcp_server.call_log import log_call as _log_call_impl


def _client():
    return get_supabase_sync()


def _log_call(**kwargs):
    _log_call_impl(**kwargs)


def _require_session() -> dict:
    s = current_session.get()
    if not s:
        raise PermissionError("no scoped session — MCP call rejected")
    return s


def _knowledge_search_impl(query: str, limit: int = 5) -> dict:
    s = _require_session()
    scopes = build_allowed_scopes(s)
    role = s.get("role") or "ANALYST"
    res = _client().rpc("atomos_knowledge_search", {
        "p_query": query or "",
        "p_scopes": scopes,
        "p_role": role,
        "p_limit": int(limit),
    }).execute()
    rows = res.data or []
    results = [{"title": r.get("title"), "scope": r.get("scope"),
                "body": r.get("body"), "source_path": r.get("source_path")}
               for r in rows]
    _log_call(execution_id=s.get("execution_id"), tool="knowledge_search",
              scope_json={"scopes": scopes, "role": role}, query=query,
              result_count=len(results))
    return {"count": len(results), "results": results}


def _data_sales_history_impl(months: int = 6) -> dict:
    s = _require_session()
    st_id = s.get("store_id")
    if not st_id:
        raise PermissionError("session has no store scope")
    c = _client()
    sm = c.table("store_master_v2").select("st_uid,store_name").eq("st_id", st_id).limit(1).execute()
    smrow = (sm.data or [{}])[0] if sm.data else {}
    st_uid = smrow.get("st_uid")
    result = {"st_id": st_id, "st_uid": st_uid,
              "store_name": smrow.get("store_name"), "months": []}
    if st_uid:
        scm = (c.table("sales_closing_monthly")
               .select("ym,rev,cnt").eq("st_uid", st_uid)
               .order("ym", desc=True).limit(int(months)).execute())
        result["months"] = scm.data or []
    _log_call(execution_id=s.get("execution_id"), tool="data_sales_history",
              scope_json={"store_id": st_id, "st_uid": st_uid}, query=f"months={months}",
              result_count=len(result["months"]))
    return result
```

> 주: Task 1에서 `store_master_v2`에 `st_uid`가 없던 경우, Step 3의 `store_master_v2` 쿼리를 그때 찾은 매핑 테이블/컬럼으로 바꾼다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_mcp_tools.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/FastAPI && git add app/mcp_server/tools.py tests/test_mcp_tools.py
git commit -m "feat(atomos-mcp): knowledge_search + data_sales_history (scope-enforced)"
```

---

## Task 7: MCP 호출 로깅

PoC 합격 증거(=Hermes가 스코프 지식을 실제로 pull) 확보용. `atomos_mcp_call_log`에 1행/호출.

**Files:**
- Create: `app/mcp_server/call_log.py`
- Test: `tests/test_call_log.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_call_log.py`:

```python
from app.mcp_server import call_log


class FakeInsert:
    def __init__(self, sink):
        self._sink = sink

    def insert(self, row):
        self._sink.append(row)
        return self

    def execute(self):
        return type("R", (), {"data": None})()


class FakeClient:
    def __init__(self, sink):
        self._sink = sink

    def table(self, name):
        assert name == "atomos_mcp_call_log"
        return FakeInsert(self._sink)


def test_log_call_inserts_row(monkeypatch):
    sink = []
    monkeypatch.setattr(call_log, "get_supabase_sync", lambda: FakeClient(sink))
    call_log.log_call(execution_id="e1", tool="knowledge_search",
                      scope_json={"a": 1}, query="q", result_count=3)
    assert len(sink) == 1
    assert sink[0]["execution_id"] == "e1"
    assert sink[0]["tool"] == "knowledge_search"
    assert sink[0]["result_count"] == 3


def test_log_call_never_raises(monkeypatch):
    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(call_log, "get_supabase_sync", boom)
    # 로깅 실패가 도구 호출을 깨면 안 됨
    call_log.log_call(execution_id="e", tool="t", scope_json={}, query="", result_count=0)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_call_log.py -q`
Expected: FAIL — `ModuleNotFoundError: app.mcp_server.call_log`.

- [ ] **Step 3: 구현 작성**

`app/mcp_server/call_log.py`:

```python
"""MCP 호출 감사 로그. best-effort(로깅 실패가 도구 호출을 깨지 않음)."""
import logging

from app.core.supabase import get_supabase_sync

logger = logging.getLogger("atomos.mcp.call_log")


def log_call(*, execution_id, tool, scope_json, query, result_count):
    try:
        get_supabase_sync().table("atomos_mcp_call_log").insert({
            "execution_id": execution_id,
            "tool": tool,
            "scope_json": scope_json,
            "query": query,
            "result_count": result_count,
        }).execute()
    except Exception as e:
        logger.warning("mcp call_log insert failed: %s", e)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_call_log.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/FastAPI && git add app/mcp_server/call_log.py tests/test_call_log.py
git commit -m "feat(atomos-mcp): best-effort call logging"
```

---

## Task 8: 인증/스코프 ASGI 미들웨어

`/mcp` 요청에서 `Authorization: Bearer`(정적) 검증 + `X-Atomos-Session`(세션 토큰) 복호 → contextvar set.

**Files:**
- Create: `app/mcp_server/auth.py`
- Test: `tests/test_auth_middleware.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_auth_middleware.py`:

```python
import pytest

from app.mcp_server.auth import ScopeAuthMiddleware
from app.mcp_server.context import current_session
from app.mcp_server.session_token import mint_session_token

SECRET = "mw-secret"
TOKEN = "static-bearer"


class CaptureApp:
    """contextvar 상태를 캡처하는 내부 ASGI 앱."""
    def __init__(self):
        self.seen_session = "UNSET"

    async def __call__(self, scope, receive, send):
        self.seen_session = current_session.get()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


def _scope(headers: list[tuple[bytes, bytes]]):
    return {"type": "http", "method": "POST", "path": "/mcp", "headers": headers}


async def _drain(app, scope):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        sent.append(msg)

    await app(scope, receive, send)
    return sent


@pytest.mark.asyncio
async def test_missing_bearer_returns_401(monkeypatch):
    inner = CaptureApp()
    mw = ScopeAuthMiddleware(inner, static_token=TOKEN, secret=SECRET)
    sent = await _drain(mw, _scope([]))
    assert sent[0]["status"] == 401
    assert inner.seen_session == "UNSET"  # 내부 앱 미호출


@pytest.mark.asyncio
async def test_valid_bearer_and_session_sets_scope(monkeypatch):
    tok = mint_session_token(execution_id="e", store_id="ST-1", brand_id="BR-1",
                             dept="sales", role="ANALYST", ttl_sec=60, secret=SECRET)
    inner = CaptureApp()
    mw = ScopeAuthMiddleware(inner, static_token=TOKEN, secret=SECRET)
    headers = [(b"authorization", f"Bearer {TOKEN}".encode()),
               (b"x-atomos-session", tok.encode())]
    sent = await _drain(mw, _scope(headers))
    assert sent[0]["status"] == 200
    assert inner.seen_session["store_id"] == "ST-1"


@pytest.mark.asyncio
async def test_valid_bearer_bad_session_returns_401():
    inner = CaptureApp()
    mw = ScopeAuthMiddleware(inner, static_token=TOKEN, secret=SECRET)
    headers = [(b"authorization", f"Bearer {TOKEN}".encode()),
               (b"x-atomos-session", b"garbage.token")]
    sent = await _drain(mw, _scope(headers))
    assert sent[0]["status"] == 401
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_auth_middleware.py -q`
Expected: FAIL — `ModuleNotFoundError: app.mcp_server.auth`.

- [ ] **Step 3: 구현 작성**

`app/mcp_server/auth.py`:

```python
"""MCP 경계 인증 미들웨어(순수 ASGI).

1) Authorization: Bearer == static_token (서버-서버). 불일치/누락 → 401.
2) X-Atomos-Session 있으면 verify → current_session set. 검증 실패 → 401.
   (세션 없으면 None set; 도구가 PermissionError로 거부.)
"""
import json

from app.mcp_server.context import current_session
from app.mcp_server.session_token import verify_session_token, SessionTokenError


class ScopeAuthMiddleware:
    def __init__(self, app, *, static_token: str, secret: str):
        self.app = app
        self.static_token = static_token
        self.secret = secret

    async def _reject(self, send, detail: str):
        body = json.dumps({"error": detail}).encode()
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        if not self.static_token or auth != f"Bearer {self.static_token}":
            await self._reject(send, "unauthorized")
            return
        session = None
        raw = headers.get("x-atomos-session")
        if raw:
            try:
                session = verify_session_token(raw, secret=self.secret)
            except SessionTokenError:
                await self._reject(send, "invalid session token")
                return
        ctx_token = current_session.set(session)
        try:
            await self.app(scope, receive, send)
        finally:
            current_session.reset(ctx_token)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_auth_middleware.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/FastAPI && git add app/mcp_server/auth.py tests/test_auth_middleware.py
git commit -m "feat(atomos-mcp): bearer + session-scope ASGI middleware"
```

---

## Task 9: FastMCP 서버 조립 + 엔진 마운트

도구를 FastMCP에 등록하고 인증 미들웨어로 감싼 ASGI 앱을 만들어 엔진(`main.py`)의 `/mcp`에 마운트한다.

**Files:**
- Create: `app/mcp_server/server.py`
- Modify: `main.py`
- Test: `tests/test_mcp_server_app.py`

- [ ] **Step 1: 서버 모듈 작성**

`app/mcp_server/server.py`:

```python
"""FastMCP 서버(streamable-HTTP) + 인증 미들웨어. 엔진 main.py가 /mcp에 마운트.

streamable_http_path="/" 로 두어 inner 가 루트에서 서빙 → 부모 app.mount("/mcp", ...) 와
합쳐 최종 경로가 정확히 /mcp 가 되도록 한다(기본값 "/mcp" 면 /mcp/mcp 로 중복됨).
"""
from mcp.server.fastmcp import FastMCP

from app.core.config import settings
from app.mcp_server.auth import ScopeAuthMiddleware
from app.mcp_server.tools import _knowledge_search_impl, _data_sales_history_impl

mcp = FastMCP("atomos", json_response=True, stateless_http=True, streamable_http_path="/")


@mcp.tool()
def knowledge_search(query: str, limit: int = 5) -> dict:
    """매장/부서/브랜드/글로벌 스코프 지식을 검색한다(현재 안건 스코프로 자동 제한).

    query: 자연어 검색어. limit: 최대 결과 수.
    """
    return _knowledge_search_impl(query, limit)


@mcp.tool()
def data_sales_history(months: int = 6) -> dict:
    """현재 안건 매장의 최근 월별 매출(rev)·객수(cnt) 추세(읽기 전용)."""
    return _data_sales_history_impl(months)


# 인증 미들웨어로 감싼 streamable-HTTP ASGI 앱. (session 수명은 main.py lifespan에서 mcp.session_manager.run())
mcp_asgi = ScopeAuthMiddleware(
    mcp.streamable_http_app(),
    static_token=settings.ATOMOS_MCP_TOKEN,
    secret=settings.ATOMOS_MCP_SESSION_SECRET,
)
```

- [ ] **Step 2: main.py에 lifespan + 마운트 배선**

`main.py`의 `app = FastAPI(...)` 정의를 lifespan 포함으로 교체한다. 먼저 import 블록 끝(현 line 19 `from app.api.routes import atomic_engine` 다음)에 추가:

```python
from contextlib import asynccontextmanager
from app.mcp_server.server import mcp, mcp_asgi
```

그리고 `app = FastAPI(` 호출 직전에 lifespan 정의 추가:

```python
@asynccontextmanager
async def lifespan(_app):
    # FastMCP streamable-http 세션 매니저를 부모 앱 수명에 편입(공식 패턴)
    async with mcp.session_manager.run():
        yield
```

그리고 `app = FastAPI(` 의 인자에 `lifespan=lifespan` 추가:

```python
app = FastAPI(
    title="HBS 운영 대시보드 API",
    description="HBS 가맹점 운영 대시보드 백엔드 API. 매출 집계, 메뉴 엔지니어링, 배달 손익 진단, 원가 마스터 관리 기능을 제공합니다.",
    version="2.0.0",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)
```

마지막으로 라우터 등록부 끝(현 `app.include_router(atomic_engine.router)` 다음)에 마운트 추가:

```python
# ATOMOS Phase 1 — 우리 MCP 서버(스코프·권한 강제). Hermes(VPS)가 원격 연결.
app.mount("/mcp", mcp_asgi)
```

- [ ] **Step 3: 앱 부팅 + 인증 거부 통합 테스트 작성**

`tests/test_mcp_server_app.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_app_boots_and_mcp_requires_auth():
    # main.py가 import되고 lifespan/마운트가 깨지지 않는지 + /mcp 인증 게이트
    import main
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 헬스(기존)
        r = await ac.get("/health")
        assert r.status_code == 200
        # /mcp 무인증 → 401
        r2 = await ac.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                           headers={"content-type": "application/json"})
        assert r2.status_code == 401
```

- [ ] **Step 4: 테스트 실행**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_mcp_server_app.py -q`
Expected: PASS (1 passed). 앱이 부팅되고 `/mcp`가 무인증 401을 반환.

> 이 테스트는 인증 게이트(401)와 헬스(200)만 본다. httpx ASGITransport는 lifespan을 띄우지 않으므로 MCP 세션 매니저 미가동 상태인데, 401은 미들웨어가 본체 도달 전에 반환하므로 무관하다. 전체 MCP 핸드셰이크는 uvicorn 기동(Step 5) 또는 배포(Task 14)에서 검증한다.
> 만약 설치된 mcp 버전에서 `FastMCP(..., streamable_http_path=...)` 또는 `mcp.session_manager` API가 다르면: `python -c "from mcp.server.fastmcp import FastMCP; m=FastMCP('x', stateless_http=True); a=m.streamable_http_app(); print(hasattr(m,'session_manager'))"`로 확인 후, 그 버전의 lifespan 기동 방식으로 Step 2의 `async with` 라인만 교체한다(경로 설정은 생성자 kwarg 또는 `m.settings.streamable_http_path`).

- [ ] **Step 5: 로컬 수동 스모크(선택, 권장)**

Run: `cd ~/FastAPI && source venv/bin/activate && uvicorn main:app --port 8099 &` 후
`curl -s -X POST localhost:8099/mcp -H 'content-type: application/json' -d '{}'`
Expected: HTTP 401 JSON `{"error":"unauthorized"}`. 확인 후 `kill %1`.

- [ ] **Step 6: Commit**

```bash
cd ~/FastAPI && git add app/mcp_server/server.py main.py tests/test_mcp_server_app.py
git commit -m "feat(atomos-mcp): FastMCP server mounted at /mcp with auth"
```

---

## Task 10: 분석 출력 검증 게이트 (lite)

쓰레기/환각/비그라운딩 출력을 거부한다(오늘의 "test" 발송 사고 방지, §3a 축소판).

**Files:**
- Create: `app/services/analysis_gate.py`
- Test: `tests/test_analysis_gate.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_analysis_gate.py`:

```python
from app.services.analysis_gate import validate_analysis, evidence_numbers

AGENDA = {
    "title": "[자동감지] 매출 급락 대응: 강남점",
    "trigger_context": {"st_id": "ST-1", "evidence": {
        "z": -3.4, "dod_delta_pct": -0.42, "mom_delta_pct": -0.18,
        "gross": 850000, "mu": 1460000}},
}

GOOD = {
    "diagnosis": "강남점 일매출이 같은 요일 대비 z=-3.4로 critical 급락. gross 850000은 평소 mu 1460000 대비 약 42% 낮음.",
    "evidence_cited": ["z=-3.4", "gross=850000", "mu=1460000"],
    "knowledge_used": ["매출 급락 대응 플레이북 (D-SALES)"],
    "proposed_actions": [
        {"title": "점주 알림", "what": "급락 통지", "how": "메신저", "owner": "ANALYST",
         "eta": "즉시", "tool_tag": "notify", "expected_effect": "초동 확인 단축"},
    ],
    "confidence": 0.72,
    "risk": "데이터 결함 가능성 잔존",
}


def test_evidence_numbers_extracts_values():
    nums = evidence_numbers(AGENDA)
    assert "-3.4" in nums
    assert "850000" in nums


def test_good_output_passes():
    ok, reasons = validate_analysis(GOOD, AGENDA)
    assert ok, reasons


def test_trivial_diagnosis_rejected():
    bad = dict(GOOD, diagnosis="test")
    ok, reasons = validate_analysis(bad, AGENDA)
    assert not ok
    assert any("diagnosis" in r for r in reasons)


def test_missing_knowledge_used_rejected():
    bad = dict(GOOD, knowledge_used=[])
    ok, reasons = validate_analysis(bad, AGENDA)
    assert not ok
    assert any("knowledge" in r for r in reasons)


def test_ungrounded_output_rejected():
    bad = dict(GOOD, diagnosis="매출이 좀 떨어진 것 같습니다 전반적으로",
               evidence_cited=["대충 감소"])
    ok, reasons = validate_analysis(bad, AGENDA)
    assert not ok
    assert any("grounding" in r for r in reasons)


def test_bad_tool_tag_rejected():
    bad = dict(GOOD, proposed_actions=[dict(GOOD["proposed_actions"][0], tool_tag="delete_store")])
    ok, reasons = validate_analysis(bad, AGENDA)
    assert not ok
    assert any("tool_tag" in r for r in reasons)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_analysis_gate.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.analysis_gate`.

- [ ] **Step 3: 구현 작성**

`app/services/analysis_gate.py`:

```python
"""분석 출력 lite 검증 게이트(Phase 1).

체크: 스키마 유효 · diagnosis substance · grounding(evidence 수치 인용) ·
knowledge_used 비어있지 않음 · 액션 tool_tag 허용목록. (Phase 2에서 풀 게이트로 확장.)
"""
ALLOWED_TOOL_TAGS = {"notify", "create_task", "record_decision",
                     "handoff_marketing", "flag_data_issue"}
ACTION_KEYS = {"title", "what", "how", "owner", "eta", "tool_tag", "expected_effect"}


def evidence_numbers(agenda: dict) -> set[str]:
    """안건 evidence의 수치 값을 문자열 집합으로(그라운딩 대조용)."""
    ev = ((agenda.get("trigger_context") or {}).get("evidence") or {})
    out: set[str] = set()
    for v in ev.values():
        if isinstance(v, (int, float)):
            out.add(str(v))
            out.add(str(round(float(v), 2)))
    return {s for s in out if s not in ("", "None")}


def validate_analysis(obj: dict, agenda: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not isinstance(obj, dict):
        return False, ["schema: not an object"]

    diagnosis = obj.get("diagnosis")
    if not isinstance(diagnosis, str) or len(diagnosis.strip()) < 20:
        reasons.append("diagnosis: missing or too short (substance)")

    ev_cited = obj.get("evidence_cited")
    if not isinstance(ev_cited, list) or not ev_cited:
        reasons.append("schema: evidence_cited must be non-empty list")

    know = obj.get("knowledge_used")
    if not isinstance(know, list) or not know:
        reasons.append("knowledge: knowledge_used empty (no scoped knowledge pulled)")

    actions = obj.get("proposed_actions")
    if not isinstance(actions, list) or not actions:
        reasons.append("schema: proposed_actions must be non-empty list")
    else:
        for i, a in enumerate(actions):
            if not isinstance(a, dict) or not ACTION_KEYS.issubset(a.keys()):
                reasons.append(f"schema: action[{i}] missing required keys")
                continue
            if a.get("tool_tag") not in ALLOWED_TOOL_TAGS:
                reasons.append(f"tool_tag: action[{i}] '{a.get('tool_tag')}' not allowed")

    conf = obj.get("confidence")
    if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
        reasons.append("schema: confidence must be 0..1")

    # grounding: 출력 본문에 evidence 수치가 최소 1개 인용됐는가
    nums = evidence_numbers(agenda)
    if nums:
        hay = " ".join([str(diagnosis or "")] + [str(x) for x in (ev_cited or [])])
        if not any(n in hay for n in nums):
            reasons.append("grounding: no evidence number cited in output")

    return (len(reasons) == 0), reasons
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_analysis_gate.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/FastAPI && git add app/services/analysis_gate.py tests/test_analysis_gate.py
git commit -m "feat(atomos): lite analysis validation gate (substance/grounding/tooltag)"
```

---

## Task 11: ANALYST 역할 프롬프트 빌더

안건→프롬프트. 페르소나 + evidence(명시 수치) + MCP 도구 사용 지시 + 그라운딩 + 엄격 JSON 출력 스키마.

**Files:**
- Create: `app/services/hermes_prompt.py`
- Test: `tests/test_hermes_prompt.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_hermes_prompt.py`:

```python
from app.services.hermes_prompt import build_analysis_prompt

AGENDA = {
    "title": "[자동감지] 매출 급락 대응: 강남점",
    "trigger_context": {"st_id": "ST-1", "check_date": "2026-06-19", "evidence": {
        "z": -3.4, "dod_delta_pct": -0.42, "mom_delta_pct": -0.18,
        "gross": 850000, "mu": 1460000}},
}


def test_prompt_includes_evidence_and_tools():
    p = build_analysis_prompt(AGENDA)
    assert "-3.4" in p          # z 수치 노출
    assert "850000" in p        # gross
    assert "knowledge_search" in p
    assert "data_sales_history" in p
    assert "JSON" in p


def test_prompt_lists_allowed_tool_tags():
    p = build_analysis_prompt(AGENDA)
    for tag in ["notify", "create_task", "record_decision", "handoff_marketing", "flag_data_issue"]:
        assert tag in p


def test_prompt_demands_grounding():
    p = build_analysis_prompt(AGENDA)
    assert "knowledge_used" in p
    assert "evidence_cited" in p
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_hermes_prompt.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.hermes_prompt`.

- [ ] **Step 3: 구현 작성**

`app/services/hermes_prompt.py`:

```python
"""안건 → ANALYST 역할 프롬프트(Phase 1). 지식은 에이전트가 MCP로 직접 pull(주입 아님)."""
import json

from app.services.analysis_gate import ALLOWED_TOOL_TAGS

_SCHEMA = {
    "diagnosis": "string (>=20 chars, 수치 근거 포함)",
    "evidence_cited": ["string (인용한 evidence 수치, 예: 'z=-3.4')"],
    "knowledge_used": ["string (knowledge_search로 받은 지식의 title)"],
    "proposed_actions": [{
        "title": "string", "what": "string", "how": "string",
        "owner": "string", "eta": "string",
        "tool_tag": "one of " + "|".join(sorted(ALLOWED_TOOL_TAGS)),
        "expected_effect": "string",
    }],
    "confidence": "number 0..1 (수치/표본 근거로 산출, 하드코딩 금지)",
    "risk": "string",
}


def build_analysis_prompt(agenda: dict) -> str:
    tc = agenda.get("trigger_context") or {}
    ev = tc.get("evidence") or {}
    ev_lines = "\n".join(f"  - {k} = {v}" for k, v in ev.items() if v is not None)
    schema = json.dumps(_SCHEMA, ensure_ascii=False, indent=2)
    return f"""당신은 HBS 본사의 매출 분석가(ANALYST)입니다. 한 매장의 매출 급락 안건을 진단하고 안전한 대응 액션을 제안합니다.

[안건]
제목: {agenda.get('title')}
매장 st_id: {tc.get('st_id')}
기준일: {tc.get('check_date')}
감지 evidence (분수 단위, 표기 시 ×100 = %):
{ev_lines}

[작업 절차 — 반드시 도구를 먼저 사용]
1. knowledge_search 도구로 이 매장/매출 부서 관련 지식을 검색하라(예: "매출 급락 대응", "그라운딩"). 스코프는 자동 제한된다.
2. data_sales_history 도구로 이 매장의 최근 월 매출 추세를 확인하라.
3. 위 evidence + 받은 지식 + 추세만 근거로 진단하라. 외부 추정으로 수치를 만들지 마라(그라운딩).
4. 각 제안 액션은 반드시 허용된 tool_tag 중 하나에 매핑하라: {', '.join(sorted(ALLOWED_TOOL_TAGS))}.

[출력 — 매우 중요]
- 오직 아래 스키마에 맞는 단일 JSON 객체 하나만 출력하라. 설명 문장·코드펜스(```)·서론/결론 금지.
- evidence_cited에는 실제 인용한 evidence 수치를 넣어라(예: "z=-3.4").
- knowledge_used에는 knowledge_search로 실제 받은 지식의 title을 넣어라(없으면 분석 불가로 간주).

스키마:
{schema}
"""
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_hermes_prompt.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/FastAPI && git add app/services/hermes_prompt.py tests/test_hermes_prompt.py
git commit -m "feat(atomos): ANALYST analysis prompt builder"
```

---

## Task 12: Hermes 러너 (SSH 트리거 + JSON 추출 + 재시도)

엔진→VPS Hermes SSH 비대화 실행, 출력에서 JSON 추출, 검증 실패 시 재시도, 최종 실패는 표면화.

**Files:**
- Create: `app/services/hermes_runner.py`
- Test: `tests/test_hermes_runner.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_hermes_runner.py`:

```python
import pytest

from app.services import hermes_runner
from app.services.hermes_runner import extract_json, run_hermes_analysis, AnalysisFailed

AGENDA = {
    "execution_id": "exec-9",
    "title": "[자동감지] 매출 급락 대응: 강남점",
    "br_uid": "BR-1",
    "trigger_context": {"st_id": "ST-1", "domain": "sales", "check_date": "2026-06-19",
                        "evidence": {"z": -3.4, "dod_delta_pct": -0.42, "mom_delta_pct": -0.18,
                                     "gross": 850000, "mu": 1460000}},
}

VALID_JSON = """```json
{"diagnosis":"강남점 z=-3.4 critical 급락, gross 850000 vs mu 1460000 약 42% 하회.",
 "evidence_cited":["z=-3.4","gross=850000"],
 "knowledge_used":["매출 급락 대응 플레이북 (D-SALES)"],
 "proposed_actions":[{"title":"점주 알림","what":"급락 통지","how":"메신저","owner":"ANALYST","eta":"즉시","tool_tag":"notify","expected_effect":"초동 확인 단축"}],
 "confidence":0.72,"risk":"데이터 결함 가능성"}
```"""


def test_extract_json_strips_fences():
    obj = extract_json(VALID_JSON)
    assert obj["confidence"] == 0.72


def test_extract_json_plain_object():
    obj = extract_json('prefix {"a": 1} suffix')
    assert obj["a"] == 1


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_run_success_first_try(monkeypatch):
    calls = []

    def fake_ssh(prompt, session_token):
        calls.append(prompt)
        return VALID_JSON

    monkeypatch.setattr(hermes_runner, "_ssh_run_hermes", fake_ssh)
    monkeypatch.setattr(hermes_runner, "_mint_token_for", lambda agenda: "tok")
    result = run_hermes_analysis(AGENDA)
    assert result["confidence"] == 0.72
    assert len(calls) == 1


def test_run_retries_then_fails(monkeypatch):
    calls = []

    def fake_ssh(prompt, session_token):
        calls.append(prompt)
        return "garbage"  # 항상 무효

    monkeypatch.setattr(hermes_runner, "_ssh_run_hermes", fake_ssh)
    monkeypatch.setattr(hermes_runner, "_mint_token_for", lambda agenda: "tok")
    monkeypatch.setattr(hermes_runner.settings, "HERMES_MAX_RETRIES", 2)
    with pytest.raises(AnalysisFailed):
        run_hermes_analysis(AGENDA)
    assert len(calls) == 3  # 최초 1 + 재시도 2


def test_run_retry_recovers(monkeypatch):
    seq = ["garbage", VALID_JSON]

    def fake_ssh(prompt, session_token):
        return seq.pop(0)

    monkeypatch.setattr(hermes_runner, "_ssh_run_hermes", fake_ssh)
    monkeypatch.setattr(hermes_runner, "_mint_token_for", lambda agenda: "tok")
    monkeypatch.setattr(hermes_runner.settings, "HERMES_MAX_RETRIES", 2)
    result = run_hermes_analysis(AGENDA)
    assert result["knowledge_used"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_hermes_runner.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.hermes_runner`.

- [ ] **Step 3: 구현 작성**

`app/services/hermes_runner.py`:

```python
"""엔진 → VPS self-hosted Hermes 트리거(SSH 비대화) + 구조화 출력 회수.

흐름: 안건 스코프 세션 토큰 발급 → 프롬프트 빌드 → SSH로 `hermes -z` 실행
     → stdout에서 단일 JSON 추출 → lite 게이트 검증 → 실패면 corrective 재시도
     → 끝내 실패면 AnalysisFailed(=사람에게 "분석 실패" 표면화).
"""
import base64
import json
import logging

from app.core.config import settings
from app.services.analysis_gate import validate_analysis
from app.services.hermes_prompt import build_analysis_prompt
from app.mcp_server.session_token import mint_session_token

logger = logging.getLogger("atomos.hermes_runner")

# Hermes config.yaml include 와 일치(서버명=atomos). -z 트리거에서 도구 화이트리스트.
_TOOLSETS = "mcp_atomos_knowledge_search,mcp_atomos_data_sales_history"


class AnalysisFailed(Exception):
    def __init__(self, reasons, last_output):
        super().__init__("; ".join(reasons) if reasons else "analysis failed")
        self.reasons = reasons
        self.last_output = last_output


def extract_json(text: str) -> dict:
    """모델 출력에서 단일 JSON 객체 추출(코드펜스/잡텍스트 허용)."""
    if not text:
        raise ValueError("empty output")
    t = text.strip()
    if "```" in t:  # 코드펜스 제거
        parts = t.split("```")
        for part in parts:
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                t = p
                break
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object found")
    return json.loads(t[start:end + 1])


def _mint_token_for(agenda: dict) -> str:
    tc = agenda.get("trigger_context") or {}
    return mint_session_token(
        execution_id=str(agenda.get("execution_id") or ""),
        store_id=str(tc.get("st_id") or ""),
        brand_id=str(agenda.get("br_uid") or ""),
        dept="sales",
        role="ANALYST",
        ttl_sec=settings.ATOMOS_MCP_SESSION_TTL_SEC,
        secret=settings.ATOMOS_MCP_SESSION_SECRET,
    )


def _ssh_run_hermes(prompt: str, session_token: str) -> str:
    """paramiko로 VPS 접속, ATOMOS_SESSION_TOKEN env + hermes -z 실행, stdout 반환.

    프롬프트는 base64로 전달(따옴표/개행 인젝션 회피). 세션 토큰은 config.yaml ${VAR} 치환→MCP 헤더로 전달.
    """
    import paramiko

    b64 = base64.b64encode(prompt.encode("utf-8")).decode("ascii")
    remote = (
        f'export ATOMOS_SESSION_TOKEN="{session_token}"; '
        f'P=$(echo "{b64}" | base64 -d); '
        f'{settings.HERMES_BIN} -z "$P" --toolsets {_TOOLSETS}'
    )
    key = paramiko.RSAKey.from_private_key(__import__("io").StringIO(settings.HERMES_VPS_SSH_KEY))
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(hostname=settings.HERMES_VPS_HOST, port=settings.HERMES_VPS_PORT,
                    username=settings.HERMES_VPS_USER, pkey=key,
                    timeout=30, banner_timeout=30, auth_timeout=30)
        stdin, stdout, stderr = cli.exec_command(f'bash -lc \'{remote}\'',
                                                 timeout=settings.HERMES_TRIGGER_TIMEOUT_SEC)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        if err.strip():
            logger.warning("hermes stderr: %s", err[:500])
        return out
    finally:
        cli.close()


def run_hermes_analysis(agenda: dict) -> dict:
    token = _mint_token_for(agenda)
    base_prompt = build_analysis_prompt(agenda)
    prompt = base_prompt
    last_reasons, last_out = ["no attempt"], ""
    attempts = 1 + max(0, int(settings.HERMES_MAX_RETRIES))
    for i in range(attempts):
        last_out = _ssh_run_hermes(prompt, token)
        try:
            obj = extract_json(last_out)
        except ValueError as e:
            last_reasons = [f"json: {e}"]
            prompt = base_prompt + f"\n\n[재시도] 직전 출력이 유효한 JSON이 아니었다({e}). 스키마에 맞는 단일 JSON만 출력하라."
            continue
        ok, reasons = validate_analysis(obj, agenda)
        if ok:
            logger.info("hermes analysis ok (attempt %d) exec=%s", i + 1, agenda.get("execution_id"))
            return obj
        last_reasons = reasons
        prompt = base_prompt + "\n\n[재시도] 직전 출력이 검증 실패: " + "; ".join(reasons) + ". 수정해 단일 JSON만 출력하라."
    raise AnalysisFailed(last_reasons, last_out)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_hermes_runner.py -q`
Expected: PASS (6 passed). (SSH는 monkeypatch로 대체 — 실 네트워크 불필요.)

- [ ] **Step 5: Commit**

```bash
cd ~/FastAPI && git add app/services/hermes_runner.py tests/test_hermes_runner.py
git commit -m "feat(atomos): hermes SSH runner + json extract + validation retry"
```

---

## Task 13: PoC 오케스트레이션 + 실행 스크립트

안건 1건을 Supabase에서 읽어 러너에 넣고, 결과/실패를 기록·출력한다.

**Files:**
- Create: `app/services/atomos_phase1_poc.py`
- Create: `scripts/phase1_poc.py`
- Test: `tests/test_phase1_poc.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_phase1_poc.py`:

```python
import pytest

from app.services import atomos_phase1_poc as poc

AGENDA = {
    "execution_id": "exec-9", "title": "[자동감지] 매출 급락 대응: 강남점", "br_uid": "BR-1",
    "trigger_context": {"st_id": "ST-1", "domain": "sales", "check_date": "2026-06-19",
                        "evidence": {"z": -3.4, "gross": 850000, "mu": 1460000}},
}
RESULT = {"diagnosis": "x" * 30, "evidence_cited": ["z=-3.4"],
          "knowledge_used": ["플레이북"], "proposed_actions": [], "confidence": 0.7}


def test_run_poc_success(monkeypatch):
    monkeypatch.setattr(poc, "_fetch_agenda", lambda eid: AGENDA)
    monkeypatch.setattr(poc, "run_hermes_analysis", lambda agenda: RESULT)
    logged = {}
    monkeypatch.setattr(poc, "_count_mcp_calls", lambda eid: {"knowledge_search": 1, "data_sales_history": 1})
    out = poc.run_poc("exec-9")
    assert out["ok"] is True
    assert out["mcp_calls"]["knowledge_search"] == 1
    assert out["result"]["confidence"] == 0.7


def test_run_poc_analysis_failed(monkeypatch):
    from app.services.hermes_runner import AnalysisFailed
    monkeypatch.setattr(poc, "_fetch_agenda", lambda eid: AGENDA)

    def boom(agenda):
        raise AnalysisFailed(["grounding: no evidence"], "garbage")

    monkeypatch.setattr(poc, "run_hermes_analysis", boom)
    monkeypatch.setattr(poc, "_count_mcp_calls", lambda eid: {})
    out = poc.run_poc("exec-9")
    assert out["ok"] is False
    assert "grounding" in " ".join(out["reasons"])


def test_run_poc_missing_agenda(monkeypatch):
    monkeypatch.setattr(poc, "_fetch_agenda", lambda eid: None)
    out = poc.run_poc("nope")
    assert out["ok"] is False
    assert "not found" in " ".join(out["reasons"])
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_phase1_poc.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.atomos_phase1_poc`.

- [ ] **Step 3: 구현 작성**

`app/services/atomos_phase1_poc.py`:

```python
"""Phase 1 PoC 오케스트레이션: 안건 1건 → Hermes 분석 → 구조화 출력 + MCP 호출 증거."""
import logging

from app.core.supabase import get_supabase_sync
from app.services.hermes_runner import run_hermes_analysis, AnalysisFailed

logger = logging.getLogger("atomos.phase1_poc")


def _fetch_agenda(execution_id: str) -> dict | None:
    c = get_supabase_sync()
    r = (c.table("strategy_executions")
         .select("execution_id,title,br_uid,trigger_context")
         .eq("execution_id", execution_id).limit(1).execute())
    return (r.data or [None])[0]


def _count_mcp_calls(execution_id: str) -> dict:
    c = get_supabase_sync()
    r = (c.table("atomos_mcp_call_log")
         .select("tool").eq("execution_id", execution_id).execute())
    out: dict = {}
    for row in (r.data or []):
        out[row["tool"]] = out.get(row["tool"], 0) + 1
    return out


def run_poc(execution_id: str) -> dict:
    agenda = _fetch_agenda(execution_id)
    if not agenda:
        return {"ok": False, "reasons": [f"agenda not found: {execution_id}"]}
    try:
        result = run_hermes_analysis(agenda)
    except AnalysisFailed as e:
        logger.warning("PoC analysis failed exec=%s: %s", execution_id, e.reasons)
        return {"ok": False, "reasons": e.reasons,
                "last_output": (e.last_output or "")[:1000],
                "mcp_calls": _count_mcp_calls(execution_id)}
    mcp_calls = _count_mcp_calls(execution_id)
    return {"ok": True, "result": result, "mcp_calls": mcp_calls,
            "knowledge_pulled": mcp_calls.get("knowledge_search", 0) > 0}
```

- [ ] **Step 4: 실행 스크립트 작성**

`scripts/phase1_poc.py`:

```python
"""Phase 1 PoC 실행: 매출 안건 1건 e2e.
사용: python scripts/phase1_poc.py <execution_id>
     (env: SUPABASE_*, ATOMOS_MCP_*, HERMES_VPS_* 필요)
"""
import json
import sys

sys.path.insert(0, ".")
from app.services.atomos_phase1_poc import run_poc

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/phase1_poc.py <execution_id>")
        sys.exit(2)
    out = run_poc(sys.argv[1])
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out.get("ok") else 1)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/test_phase1_poc.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: 전체 단위 테스트 회귀**

Run: `cd ~/FastAPI && source venv/bin/activate && pytest tests/ -q`
Expected: PASS (전 테스트 통과).

- [ ] **Step 7: Commit**

```bash
cd ~/FastAPI && git add app/services/atomos_phase1_poc.py scripts/phase1_poc.py tests/test_phase1_poc.py
git commit -m "feat(atomos): phase1 PoC orchestration + runner script"
```

---

## Task 14: 엔진 배포 + Railway 환경변수

MCP 서버는 엔진에 마운트되어 같이 배포된다(VPS에서 도달 가능). 신규 settings를 Railway에 등록.

**Files:** (배포/설정 — 코드 변경 없음)

- [ ] **Step 1: 시크릿 생성**

Run(로컬):
```bash
python -c "import secrets; print('ATOMOS_MCP_TOKEN=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('ATOMOS_MCP_SESSION_SECRET=' + secrets.token_urlsafe(32))"
```
Expected: 두 개의 랜덤 토큰. 안전 보관(VPS·Railway 양쪽에서 사용).

- [ ] **Step 2: (operator) Railway 엔진 서비스에 env 등록**

다음 변수를 Railway 엔진 서비스 Variables에 추가:
- `ATOMOS_MCP_TOKEN` = (Step 1 값)
- `ATOMOS_MCP_SESSION_SECRET` = (Step 1 값)
- `ATOMOS_MCP_BASE_URL` = `https://<엔진-railway-도메인>/mcp/` (trailing slash 필수)
- `ATOMOS_MCP_SESSION_SECRET` = (Step 1 값 — **미설정 금지**; blank이면 토큰 검증 fail-closed)
- (선택) `HERMES_VPS_HOST_KEY` = `ssh-keyscan -H <VPS_HOST>` 출력 1줄(host-key 핀; 미설정 시 AutoAdd)
- `HERMES_VPS_HOST` = VPS IP/호스트
- `HERMES_VPS_USER` = `hermes`
- `HERMES_VPS_SSH_KEY` = (Task 15에서 생성할 private key PEM 전체)
- (선택) `HERMES_MODEL`, `HERMES_TRIGGER_TIMEOUT_SEC`

> `HERMES_VPS_SSH_KEY`는 Task 15 Step 2 이후에 채운다(키 생성 후).

- [ ] **Step 3: 배포 후 마운트 도달 확인**

Run: `curl -s -o /dev/null -w "%{http_code}" -X POST https://<엔진-railway-도메인>/mcp/ -H 'content-type: application/json' -d '{}'`
Expected: `401` (마운트 정상 + 인증 게이트 동작). trailing slash 없는 `/mcp`는 `307`(→`/mcp/`); `404`면 마운트/배포 실패 → 로그 확인.

- [ ] **Step 4: Bearer 통과 시 다른 응답 확인**

Run:
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST https://<엔진-railway-도메인>/mcp/ \
  -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
  -H "authorization: Bearer <ATOMOS_MCP_TOKEN>" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```
Expected: `401`이 **아닌** 응답(200 또는 MCP 세션 관련 4xx). Bearer가 통과해 MCP 본체에 도달함을 의미.

---

## Task 15: VPS self-hosted Hermes 설치 + 설정 (operator 실행)

> 이 Task는 VPS 셸에서 운영자가 실행한다(SSH·시스템 설정 — 승인 필요). 각 Step은 명령 + 기대 출력.

- [ ] **Step 1: 전용 유저 + Hermes 설치**

VPS에서:
```bash
sudo adduser --disabled-password --gecos "" hermes
sudo su - hermes
git --version            # 없으면: sudo apt-get install -y git
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
hermes doctor
```
Expected: `hermes doctor`가 Python 3.11/Node/ripgrep 등 의존성 OK를 보고. 바이너리: `~/.local/bin/hermes`.

- [ ] **Step 2: 엔진→VPS SSH 키 등록**

로컬(엔진 운영자 머신)에서 전용 키 생성:
```bash
ssh-keygen -t rsa -b 4096 -m PEM -f ./atomos_hermes_key -N "" -C "atomos-engine"
```
공개키를 VPS `hermes` 유저에 등록:
```bash
# VPS에서 (hermes 유저)
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "<atomos_hermes_key.pub 내용>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```
private key(`atomos_hermes_key` 파일 전체 PEM)를 Railway `HERMES_VPS_SSH_KEY`에 등록(Task 14 Step 2).

검증(로컬): `ssh -i ./atomos_hermes_key hermes@<VPS_HOST> "echo ok && hermes --version"`
Expected: `ok` + Hermes 버전 출력.

- [ ] **Step 3: 모델 제공자 + 비밀 설정**

VPS `~/.hermes/.env` 작성:
```bash
cat > ~/.hermes/.env <<'EOF'
OPENROUTER_API_KEY=sk-or-...실제키...
ATOMOS_MCP_URL=https://<엔진-railway-도메인>/mcp/
ATOMOS_MCP_TOKEN=<Task14 Step1 ATOMOS_MCP_TOKEN>
EOF
chmod 600 ~/.hermes/.env
```

- [ ] **Step 4: config.yaml 작성**

먼저 사용 가능한 toolset 이름 확인:
```bash
hermes tools --summary
```
출력에서 코드/셸/파일쓰기/웹 실행 계열 toolset 이름을 기록한다(예: code execution, shell, files, web 등). PoC는 MCP 도구만 필요하므로 **내장 실행 toolset을 모두 비활성**한다.

`~/.hermes/config.yaml` 작성(아래 `disabled_toolsets`는 위 출력에서 확인한 실제 이름으로 채움):
```yaml
model:
  provider: openrouter
  default: anthropic/claude-sonnet-4.6
  context_length: 200000

terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
  container_memory: 5120
  container_disk: 51200
  timeout: 180

approvals:
  mode: smart
  timeout: 60
  cron_mode: deny

agent:
  max_turns: 30
  disabled_toolsets:
    - <code-exec toolset 이름>     # hermes tools --summary 에서 확인한 실제 이름들
    - <shell toolset 이름>
    - <files-write toolset 이름>

mcp_servers:
  atomos:
    url: "${ATOMOS_MCP_URL}"
    headers:
      Authorization: "Bearer ${ATOMOS_MCP_TOKEN}"
      X-Atomos-Session: "${ATOMOS_SESSION_TOKEN}"
    tools:
      include: [knowledge_search, data_sales_history]
```

검증:
```bash
hermes config check
```
Expected: 누락 옵션 경고 없음(또는 무해한 기본값 안내만).

- [ ] **Step 5: Docker 백엔드 동작 확인**

```bash
docker --version || sudo apt-get install -y docker.io
sudo usermod -aG docker hermes    # 재로그인 필요
docker run --rm hello-world
```
Expected: Docker 정상(컨테이너 격리 = 보안 경계).

- [ ] **Step 6: MCP 연결 확인**

```bash
ATOMOS_SESSION_TOKEN="$(python3 - <<'PY'
# 로컬 테스트용 임시 세션 토큰(엔진의 mint와 동일 HMAC). secret/scope는 검증용.
import base64,hashlib,hmac,json,time,os
secret=os.environ.get("ATOMOS_MCP_SESSION_SECRET","")  # 운영자가 export 후 실행
p={"execution_id":"smoke","store_id":"<실매장 st_id>","brand_id":"<실 br_id>","dept":"sales","role":"ANALYST","exp":int(time.time())+600}
b=base64.urlsafe_b64encode(json.dumps(p,separators=(',',':')).encode()).rstrip(b'=').decode()
sig=base64.urlsafe_b64encode(hmac.new(secret.encode(),b.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
print(b+'.'+sig)
PY
)" hermes mcp test atomos
```
Expected: `atomos` 서버 연결 성공 + 도구 `knowledge_search`·`data_sales_history` 노출 확인. (실패 시 URL/토큰/방화벽 점검.)

> 주: 위 스모크에서 `ATOMOS_MCP_SESSION_SECRET`를 잠깐 export해야 한다. 정식 트리거에서는 엔진이 토큰을 발급하므로 VPS에 secret을 두지 않는다 — 스모크 후 셸 history/env에서 제거한다.

- [ ] **Step 7: 비대화 -z 스모크**

```bash
hermes -z "반드시 정확히 다음 JSON만 출력하라: {\"ping\":\"pong\"}" --toolsets mcp_atomos_knowledge_search,mcp_atomos_data_sales_history
```
Expected: stdout에 `{"ping":"pong"}`(또는 그에 준하는 단일 JSON). 배너/스피너 없음.

---

## Task 16: e2e PoC 합격 검증 (operator 실행)

> 실 매출 안건 1건으로 전체 파이프라인을 돌려 §10 Phase 1 합격선을 입증한다.

- [ ] **Step 1: 실 매출 안건 1건 선정**

Supabase에서 매출 도메인 안건 1건의 `execution_id` 확보:
```sql
select execution_id, title, trigger_context->>'st_id' as st_id, trigger_context->'evidence' as evidence
from strategy_executions
where trigger_context->>'domain' = 'sales'
order by created_at desc limit 5;
```
하나 고른다(st_id가 `store_master_v2`에 존재하고 `sales_closing_monthly`에 데이터가 있는 매장 권장).

- [ ] **Step 2: PoC 실행**

엔진 환경(Railway 셸 또는 동일 env를 가진 WSL)에서:
Run: `cd ~/FastAPI && source venv/bin/activate && set -a && source .env && set +a && python scripts/phase1_poc.py <execution_id>`
Expected: `{"ok": true, ...}` JSON 출력. exit code 0.

- [ ] **Step 3: 합격 기준 검증 (4개 모두)**

출력과 DB로 다음을 확인:

1. **스코프 지식 수신**: `out.mcp_calls.knowledge_search >= 1` 이고
   `select scope_json from atomos_mcp_call_log where execution_id='<id>' and tool='knowledge_search';`
   의 `scopes`에 해당 안건의 `store:<st_id>`/`dept:sales`가 포함.
2. **분석 수행**: `out.result.diagnosis` 가 안건 evidence 수치를 인용(예: z 값 포함).
3. **구조화 출력 회수**: `out.result` 가 lite 게이트 통과(스키마·tool_tag·confidence 유효) — `ok:true`가 이를 의미.
4. **그라운딩**: `out.result.knowledge_used` 비어있지 않고 `evidence_cited`에 실제 수치 포함.

Expected: 4개 모두 충족 → **"우리가 Hermes를 통제 구동 가능" 입증(Phase 1 키스톤 합격).**

- [ ] **Step 4: 실패 경로 확인(검증 게이트 작동)**

`hermes_prompt`에서 일시적으로 그라운딩 지시를 약화시키거나, 잘못된 모델로 1회 돌려 `ok:false` + `reasons`가 표면화되는지 확인(쓰레기 통과 금지 입증). 확인 후 원복.
Expected: 무효 출력 시 `{"ok": false, "reasons": [...]}` + exit code 1. (오늘의 "test" 발송류가 차단됨.)

- [ ] **Step 5: 설계 문서 체크리스트 갱신**

`ATOMOS_BRAIN/docs/superpowers/specs/2026-06-20-pipeline-redesign-design.md` §11에 Phase 1 완료를 반영하고, glen_work ADR(`2026-06-20-atomos-pipeline-redesign.md`)의 "미결: self-hosted Hermes PoC"를 해소로 갱신.

```bash
cd ~/ATOMOS_BRAIN && git add docs/superpowers/specs/2026-06-20-pipeline-redesign-design.md
git commit -m "docs(atomos): phase1 hermes/MCP keystone PoC 합격 기록"
```

---

## 합격선 (Phase 1 keystone) 요약

매출 안건 1건이 → 엔진이 스코프 세션 토큰 발급 → VPS Hermes를 SSH 비대화 트리거 → Hermes가 **우리 MCP**(`knowledge_search`·`data_sales_history`, 화이트리스트 외 도구 없음)로 스코프 지식·데이터 pull → 분석 → 단일 JSON 구조화 출력 회수 → lite 게이트 통과. MCP 호출 로그가 스코프 강제를 증명. **= 우리가 Hermes를 100% 통제 구동.**

## Phase 2 진입 전제(이 계획 산출물 위에)

- 지식 검색 백엔드를 pgvector 시맨틱 + git→CI 색인(§5)으로 교체(인터페이스 유지).
- §3a 풀 검증 게이트·§3b 4레이어 evidence 검증·§3c 컨텍스트 프로바이더(weather/trade_area)·§3d 실행 안전도구 레지스트리·§3e 측정·§3f 보고 신뢰게이트.
- 콘솔 승인 UI 연동 + 매출 도메인 수직 슬라이스 e2e.
