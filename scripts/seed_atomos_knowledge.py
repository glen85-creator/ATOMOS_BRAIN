"""ATOMOS_BRAIN/knowledge/**.md → Supabase atomos_knowledge 적재.
멱등(source_path upsert) + 삭제 reconcile(리포에 없는 source_path 제거).
frontmatter: scope, read_tier, read_roles, tags, title (python-frontmatter).
사용: SUPABASE_URL/SUPABASE_SERVICE_KEY env 설정 후  python scripts/seed_atomos_knowledge.py
선행: FastAPI/migrations/007 + 008 적용.
"""
import glob
import os
import sys

import frontmatter
import requests

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")


def parse_row(path: str, root: str = ROOT) -> dict:
    post = frontmatter.load(path)
    m = post.metadata
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    return {
        "scope": m.get("scope") or "global",
        "read_tier": m.get("read_tier") or "ATOMOS_MASTER",
        "read_roles": list(m.get("read_roles") or []),
        "tags": list(m.get("tags") or []),
        "title": m.get("title") or os.path.basename(path),
        "body": post.content.strip(),
        "source_path": rel,
    }


def _headers(key: str) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def main() -> int:
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    h = _headers(key)
    files = glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True)
    rows = [parse_row(f) for f in files]
    keep = {r["source_path"] for r in rows}

    existing = requests.get(f"{url}/rest/v1/atomos_knowledge?select=source_path",
                            headers=h, timeout=30).json()
    for row in existing:
        sp = row.get("source_path")
        if sp and sp not in keep:
            requests.delete(f"{url}/rest/v1/atomos_knowledge?source_path=eq.{sp}", headers=h, timeout=30)
            print("deleted", sp)

    for row in rows:
        requests.delete(f"{url}/rest/v1/atomos_knowledge?source_path=eq.{row['source_path']}",
                        headers=h, timeout=30)
        r = requests.post(f"{url}/rest/v1/atomos_knowledge",
                          headers={**h, "Prefer": "return=minimal"}, json=row, timeout=30)
        print(row["source_path"], "->", r.status_code)
        if r.status_code >= 300:
            print("  body:", r.text)
    print(f"seeded {len(rows)} docs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
