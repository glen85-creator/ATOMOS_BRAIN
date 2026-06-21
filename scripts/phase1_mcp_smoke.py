"""Phase 1 MCP 절반 풀 스모크 — VPS/Hermes 없이 '스코프 지식 over MCP' 실증.

전제: migrations/007 적용 + seed 완료 + 로컬 엔진(uvicorn main:app --port 8099) 기동 중.
env: ATOMOS_MCP_TOKEN, ATOMOS_MCP_SESSION_SECRET (엔진과 동일), SUPABASE_URL, SUPABASE_SERVICE_KEY.
실행: python ~/ATOMOS_BRAIN/scripts/phase1_mcp_smoke.py
"""
import asyncio
import os
import sys

sys.path.insert(0, "/home/glen_85/FastAPI")

import requests
from app.mcp_server.session_token import mint_session_token
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

URL = "http://localhost:8099/mcp/"
MCP_TOKEN = os.environ["ATOMOS_MCP_TOKEN"]
SECRET = os.environ["ATOMOS_MCP_SESSION_SECRET"]
SUPA = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]


async def main():
    # 안건 스코프 세션토큰(dept:sales/ANALYST) — seed된 global+dept:sales 지식과 매칭
    token = mint_session_token(execution_id="smoke-1", store_id="ST-SMOKE",
                               brand_id="BR-SMOKE", dept="sales", role="ANALYST",
                               ttl_sec=600, secret=SECRET)
    headers = {"Authorization": f"Bearer {MCP_TOKEN}", "X-Atomos-Session": token}

    print("=== 1) 무인증 거부 확인 ===")
    r = requests.post(URL, headers={"content-type": "application/json"}, json={}, timeout=15)
    print("no-auth status:", r.status_code, "(401 기대)")

    print("=== 2) MCP 클라이언트로 knowledge_search 호출 ===")
    async with streamablehttp_client(URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("노출 도구:", [t.name for t in tools.tools])
            res = await session.call_tool("knowledge_search", {"query": "매출 급락 대응"})
            payload = None
            if getattr(res, "structuredContent", None):
                payload = res.structuredContent
            else:
                for c in res.content:
                    if getattr(c, "text", None):
                        payload = c.text
            print("knowledge_search 결과:", payload)

    print("=== 3) MCP 호출 로그 확인(스코프 강제 증거) ===")
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    log = requests.get(f"{SUPA}/rest/v1/atomos_mcp_call_log"
                       f"?select=tool,scope_json,result_count&execution_id=eq.smoke-1",
                       headers=h, timeout=15).json()
    print("call_log:", log)

    ok = bool(log) and any(x.get("tool") == "knowledge_search" and (x.get("result_count") or 0) > 0
                           for x in log)
    print("\n=== SMOKE", "PASS" if ok else "FAIL",
          "— 스코프 지식이 MCP로 회수되고 호출이 스코프와 함께 기록됨 ===")


if __name__ == "__main__":
    asyncio.run(main())
