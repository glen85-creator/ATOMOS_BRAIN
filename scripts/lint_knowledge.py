"""knowledge/**.md frontmatter 검증. ERROR 있으면 종료코드 1(ingest 차단), WARN은 0.
사용: python scripts/lint_knowledge.py [knowledge_dir]
"""
import glob
import os
import re
import sys
from dataclasses import dataclass

import frontmatter

VALID_TIERS = {"STORE_OWNER", "HQ_STAFF", "HQ_EXEC", "ATOMOS_MASTER"}
ROLE_REGISTRY = {"ANALYST"}   # 도메인 활성화 시 1개씩 추가. legacy 로스터 비차용.
SCOPE_RE = re.compile(r"^(global|brand:[^\s]+|dept:[^\s]+|store:[^\s]+)$")
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")


@dataclass
class Finding:
    level: str   # "ERROR" | "WARN"
    message: str


def parse_doc(path: str) -> dict:
    post = frontmatter.load(path)
    m = post.metadata
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    return {"scope": m.get("scope"), "read_tier": m.get("read_tier"),
            "read_roles": m.get("read_roles"), "title": m.get("title"),
            "tags": m.get("tags") or [], "source_path": rel, "body": post.content}


def lint_doc(doc: dict) -> list:
    out = []
    scope = doc.get("scope")
    if not scope:
        out.append(Finding("ERROR", "scope 누락"))
    elif not SCOPE_RE.match(str(scope)):
        out.append(Finding("ERROR", f"scope 구문 위반: {scope!r}"))
    if not doc.get("title"):
        out.append(Finding("ERROR", "title 누락"))
    tier = doc.get("read_tier")
    if tier is None:
        out.append(Finding("WARN", "read_tier 누락 → ATOMOS_MASTER 기본(사람 노출 0). 의도 확인."))
    elif tier not in VALID_TIERS:
        out.append(Finding("ERROR", f"read_tier enum 밖: {tier!r}"))
    for r in (doc.get("read_roles") or []):
        if r not in ROLE_REGISTRY:
            out.append(Finding("WARN", f"미등록 read_role: {r!r} (레지스트리={sorted(ROLE_REGISTRY)})"))
    return out


def main(argv: list) -> int:
    root = argv[1] if len(argv) > 1 else ROOT
    files = glob.glob(os.path.join(root, "**", "*.md"), recursive=True)
    errors = 0
    for f in files:
        for finding in lint_doc(parse_doc(f)):
            rel = os.path.relpath(f, root).replace(os.sep, "/")
            print(f"{finding.level}: {rel}: {finding.message}")
            if finding.level == "ERROR":
                errors += 1
    print(f"lint: {len(files)} files, {errors} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
