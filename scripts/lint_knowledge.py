"""knowledge/**.md frontmatter 검증. ERROR 있으면 종료코드 1(ingest 차단), WARN은 0.
사용: python scripts/lint_knowledge.py [knowledge_dir]
"""
import glob
import os
import re
import sys
from dataclasses import dataclass

import frontmatter

try:  # 패키지(import scripts.lint_knowledge / pytest)·직접실행(python scripts/lint_knowledge.py) 양립
    from scripts.links import extract_links, resolve_target
except ImportError:  # 직접실행 시 scripts/가 sys.path[0]라 패키지 경로 미해소
    from links import extract_links, resolve_target

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
    read_roles = doc.get("read_roles")
    if isinstance(read_roles, str):
        out.append(Finding("ERROR", "read_roles는 리스트여야 함 (예: [ANALYST])"))
    else:
        for r in (read_roles or []):
            if r not in ROLE_REGISTRY:
                out.append(Finding("WARN", f"미등록 read_role: {r!r} (레지스트리={sorted(ROLE_REGISTRY)})"))
    return out


def _lint_links(docs: list) -> int:
    """docs=[(rel, doc)] 크로스파일 검사 → missing-link/orphan WARN 출력. WARN만이라 0 반환."""
    known = {d["source_path"] for _, d in docs}
    inbound = {p: 0 for p in known}
    outbound = {p: 0 for p in known}
    for rel, d in docs:
        fp = d["source_path"]
        for to_ref, _label in extract_links(d.get("body") or ""):
            tp = resolve_target(to_ref, known)
            if tp is None:
                print(f"WARN: {rel}: 미해소 링크 [[{to_ref}]]")
            else:
                outbound[fp] = outbound.get(fp, 0) + 1
                inbound[tp] = inbound.get(tp, 0) + 1
    for rel, d in docs:
        fp = d["source_path"]
        if inbound.get(fp, 0) == 0 and outbound.get(fp, 0) == 0:
            print(f"WARN: {rel}: orphan (인·아웃 링크 0)")
    return 0


def main(argv: list) -> int:
    root = argv[1] if len(argv) > 1 else ROOT
    files = glob.glob(os.path.join(root, "**", "*.md"), recursive=True)
    errors = 0
    docs = []
    for f in files:
        rel = os.path.relpath(f, root).replace(os.sep, "/")
        try:
            doc = parse_doc(f)
        except Exception as e:
            print(f"ERROR: {rel}: frontmatter 파싱 실패: {e}")
            errors += 1
            continue
        docs.append((rel, doc))
        for finding in lint_doc(doc):
            print(f"{finding.level}: {rel}: {finding.message}")
            if finding.level == "ERROR":
                errors += 1
    _lint_links(docs)
    print(f"lint: {len(files)} files, {errors} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
