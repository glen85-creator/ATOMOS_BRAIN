"""ATOMOS_BRAIN/knowledge/**.md → Supabase atomos_knowledge 적재.
멱등(source_path upsert) + 삭제 reconcile(리포에 없는 source_path 제거).
frontmatter: scope, read_tier, read_roles, tags, title (python-frontmatter).
사용: SUPABASE_URL/SUPABASE_SERVICE_KEY env 설정 후  python scripts/seed_atomos_knowledge.py
선행: FastAPI/migrations/007 + 008 적용.
"""
import glob
import os
import sys
import urllib.parse

import frontmatter
import requests

try:  # 패키지(import scripts.seed_atomos_knowledge)·직접실행(python scripts/seed_atomos_knowledge.py) 양립
    from scripts.links import build_link_rows
except ImportError:  # 직접실행 시 scripts/가 sys.path[0]라 패키지 경로 미해소
    from links import build_link_rows

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

    # reconcile GET은 atomos_knowledge가 PostgREST 기본 행 상한 미만이라고 가정(현 규모 OK; 커지면 페이지네이션).
    resp = requests.get(f"{url}/rest/v1/atomos_knowledge?select=source_path",
                        headers=h, timeout=30)
    resp.raise_for_status()
    existing = resp.json()
    if not isinstance(existing, list):
        raise RuntimeError(f"unexpected reconcile response: {existing!r}")
    for row in existing:
        sp = row.get("source_path")
        if sp and sp not in keep:
            requests.delete(
                f"{url}/rest/v1/atomos_knowledge?source_path=eq.{urllib.parse.quote(sp, safe='')}",
                headers=h, timeout=30)
            print("deleted", sp)

    for row in rows:
        requests.delete(
            f"{url}/rest/v1/atomos_knowledge?source_path=eq.{urllib.parse.quote(row['source_path'], safe='')}",
            headers=h, timeout=30)
        r = requests.post(f"{url}/rest/v1/atomos_knowledge",
                          headers={**h, "Prefer": "return=minimal"}, json=row, timeout=30)
        print(row["source_path"], "->", r.status_code)
        if r.status_code >= 300:
            print("  body:", r.text)
    print(f"seeded {len(rows)} docs")

    # ── 링크테이블 재구축(atomos_knowledge_links) ──
    link_rows = build_link_rows(rows)
    # 0) reconcile GET 먼저 — 실패 시 어떤 삭제도 하기 전에 중단(파괴 전 실패)
    lresp = requests.get(f"{url}/rest/v1/atomos_knowledge_links?select=from_path",
                         headers=h, timeout=30)
    lresp.raise_for_status()
    existing_links = lresp.json()
    if not isinstance(existing_links, list):
        raise RuntimeError(f"unexpected links response: {existing_links!r}")
    # 1) 삭제된 노트의 링크 제거(stale)
    for row in existing_links:
        fp = row.get("from_path")
        if fp and fp not in keep:
            requests.delete(
                f"{url}/rest/v1/atomos_knowledge_links?from_path=eq.{urllib.parse.quote(fp, safe='')}",
                headers=h, timeout=30)
    # 2) 현재 노트들의 기존 링크 삭제(per-from_path)
    for r in rows:
        fp = urllib.parse.quote(r["source_path"], safe="")
        requests.delete(f"{url}/rest/v1/atomos_knowledge_links?from_path=eq.{fp}",
                        headers=h, timeout=30)
    # 3) 현재 링크 삽입
    for lr in link_rows:
        rr = requests.post(f"{url}/rest/v1/atomos_knowledge_links",
                           headers={**h, "Prefer": "return=minimal"}, json=lr, timeout=30)
        if rr.status_code >= 300:
            print("  link insert:", lr["from_path"], "->", rr.status_code, rr.text)
    print(f"linked {len(link_rows)} edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
