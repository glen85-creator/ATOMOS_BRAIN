"""ATOMOS_BRAIN/knowledge/**.md → Supabase atomos_knowledge 적재(멱등: source_path 기준 upsert).

frontmatter(scope, read_roles, title) 파싱. 엔진 venv/Supabase 자격으로 실행.
사용: SUPABASE_URL/SUPABASE_SERVICE_KEY env 설정 후
  python scripts/seed_atomos_knowledge.py
선행: FastAPI/migrations/007_atomos_phase1_mcp.sql 적용(atomos_knowledge 테이블 존재).
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
