# ATOMOS BRAIN v2 백링크 (Slice 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 노트 본문의 `[[wikilink]]`를 추출·색인해, 권한 범위 내에서 백링크/아웃링크를 보여주고 본문 링크로 노트 간 이동하게 한다.

**Architecture:** ingest(seed)가 `[[target]]`을 source_path로 해소해 `atomos_knowledge_links`(008에 이미 생성)를 채운다. 새 마이그레이션 009의 권한필터 RPC 2개로 note EP가 백링크/아웃링크를 회수한다. 프론트가 패널 + 본문 클릭 네비를 렌더한다. 링크 조회도 서버측 (scope,tier) 필터 — "숨김=데이터 안 옴" 일관.

**Tech Stack:** Python(seed/lint, python-frontmatter) · Postgres RPC · FastAPI(supabase-py async) · React 19 + TanStack Query + react-markdown.

**정본 spec:** `ATOMOS_BRAIN/docs/superpowers/specs/2026-06-22-atomos-brain-v2-backlinks-design.md`.

**실행 환경:** 정본=WSL. 명령은 `wsl -d Ubuntu -- bash -lc "cd ~/REPO && …"`(단일 호출·절대경로·for루프 금지). 편집은 UNC `\\wsl.localhost\ubuntu\home\glen_85\…`.

---

## ⚠️ 선행 / 워크트리

- **v1 위에 쌓는다.** Slice 4는 v1의 `seed_atomos_knowledge.py`/`lint_knowledge.py`/`brain.py`/`types.ts`/`BrainReference.tsx`/`brainWikilink.ts`를 확장한다. v1은 미병합·파킹 상태이므로 **기존 v1 워크트리·동일 브랜치에 이어서 커밋**한다(새 워크트리 X):
  - `~/ATOMOS_BRAIN-brain` (브랜치 `feat/knowledge-ingest-lint`) — 4a
  - `~/FastAPI-brain` (브랜치 `feat/brain-knowledge-layer`) — 4b
  - `~/hbs-dashboard-brain` (브랜치 `feat/brain-reference-page`) — 4c
- **구현 게이트(live)**: 007+008 적용 + ingest 라이브(= v1 ship 선행)가 끝나야 실제 색인/E2E 가능. **4a의 순수 Python 테스트·4b의 모킹 테스트·4c의 build/vitest는 지금도 그린 가능**(라이브 DB 불요). 009 *적용*과 E2E는 v1과 함께 보류.
- 008은 `atomos_knowledge_links(from_path, to_ref, to_path, resolved)` + `to_path` 인덱스를 이미 만든다 — 이 슬라이스는 채우고 읽기만. **009는 RPC 2개만 추가**(008 미수정).
- Phase1 경로(007 RPC·`app/mcp_server`) 무수정.

## 파일 구조

### ATOMOS_BRAIN (`~/ATOMOS_BRAIN-brain`)
- **Create** `scripts/links.py` — 순수 링크 유틸(`extract_links`, `resolve_target`, `build_link_rows`).
- **Modify** `scripts/seed_atomos_knowledge.py` — `build_link_rows`로 `atomos_knowledge_links` 재구축(per-from_path delete + reconcile + insert).
- **Modify** `scripts/lint_knowledge.py` — 크로스파일 패스(`_lint_links`): missing-link / orphan WARN.
- **Modify** `tests/test_knowledge_parse_lint.py` — links 유틸 + lint 크로스파일 테스트.

### FastAPI (`~/FastAPI-brain`)
- **Create** `migrations/009_atomos_brain_backlinks.sql` — `atomos_knowledge_backlinks_v2` / `atomos_knowledge_outlinks_v2`.
- **Modify** `app/api/routes/brain.py` — `brain_note`가 두 RPC로 backlinks/outlinks 채움.
- **Modify** `tests/test_brain_routes.py` — 백링크/아웃링크 채움 테스트.

### hbs-dashboard (`~/hbs-dashboard-brain`)
- **Modify** `src/api/types.ts` — `BrainLinkRef` + `BrainNoteDetail.backlinks/outlinks: BrainLinkRef[]`.
- **Modify** `src/pages/Admin/brainWikilink.ts` — `wikilinksToMarkdown`.
- **Modify** `src/pages/Admin/brainWikilink.test.ts` — `wikilinksToMarkdown` 테스트.
- **Modify** `src/pages/Admin/BrainReference.tsx` — 백링크/아웃링크 패널 + 본문 `brain:` 링크 렌더.

---

# Slice 4a — ingest 링크추출 + lint (ATOMOS_BRAIN)

> 워크트리 `~/ATOMOS_BRAIN-brain`. 테스트: `.venv/bin/python -m pytest tests/ -v`(.venv 없으면 `python3 -m venv .venv && .venv/bin/pip install -q -r scripts/requirements.txt`).

### Task 1: `scripts/links.py` 순수 유틸 (TDD)

**Files:** Create `scripts/links.py`; Modify `tests/test_knowledge_parse_lint.py`.

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_knowledge_parse_lint.py` 끝에:

```python
from scripts.links import extract_links, resolve_target, build_link_rows

def test_extract_links_simple():
    assert extract_links("see [[dept/sales/x]] now") == [("dept/sales/x", "dept/sales/x")]

def test_extract_links_label_and_multiple():
    assert extract_links("[[a|라벨]] and [[b]]") == [("a", "라벨"), ("b", "b")]

def test_extract_links_none():
    assert extract_links("no links") == []

def test_resolve_target_direct_and_md_fallback():
    known = {"global/g.md", "dept/sales/x.md"}
    assert resolve_target("global/g.md", known) == "global/g.md"
    assert resolve_target("dept/sales/x", known) == "dept/sales/x.md"   # .md 폴백
    assert resolve_target("ghost", known) is None

def test_build_link_rows_resolves_and_marks_unresolved():
    rows = [
        {"source_path": "a.md", "body": "[[b]] and [[ghost]]"},
        {"source_path": "b.md", "body": "no links"},
    ]
    out = build_link_rows(rows)
    assert {"from_path": "a.md", "to_ref": "b", "to_path": "b.md", "resolved": True} in out
    assert {"from_path": "a.md", "to_ref": "ghost", "to_path": None, "resolved": False} in out
    assert len(out) == 2

def test_build_link_rows_dedups_same_ref():
    rows = [{"source_path": "a.md", "body": "[[b]] [[b]]"}, {"source_path": "b.md", "body": ""}]
    out = build_link_rows(rows)
    assert len([r for r in out if r["from_path"] == "a.md" and r["to_ref"] == "b"]) == 1
```

- [ ] **Step 2: 실패 확인** — `... pytest tests/test_knowledge_parse_lint.py -k "links or resolve or build_link" -v` → FAIL (`ModuleNotFoundError: scripts.links`).

- [ ] **Step 3: 구현** — `scripts/links.py`:

```python
"""knowledge 본문의 [[wikilink]] 추출·해소(순수). seed·lint 공용."""
import re

_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def extract_links(body: str) -> list:
    """본문 → [(to_ref, label)]. label 없으면 to_ref. 순수."""
    return [(m.group(1).strip(), (m.group(2) or m.group(1)).strip())
            for m in _WIKILINK_RE.finditer(body or "")]


def resolve_target(to_ref: str, known_paths: set) -> str | None:
    """to_ref → source_path. to_ref, 그다음 to_ref+'.md' 시도. 미해소 None."""
    for cand in (to_ref, to_ref + ".md"):
        if cand in known_paths:
            return cand
    return None


def build_link_rows(rows: list) -> list:
    """parsed rows([{source_path, body, ...}]) → atomos_knowledge_links 행.
    rows의 source_path 집합으로 해소. (from_path,to_ref) 중복 제거."""
    known = {r["source_path"] for r in rows}
    out, seen = [], set()
    for r in rows:
        fp = r["source_path"]
        for to_ref, _label in extract_links(r.get("body") or ""):
            key = (fp, to_ref)
            if key in seen:
                continue
            seen.add(key)
            to_path = resolve_target(to_ref, known)
            out.append({"from_path": fp, "to_ref": to_ref,
                        "to_path": to_path, "resolved": to_path is not None})
    return out
```

- [ ] **Step 4: 통과 확인** — `... pytest tests/test_knowledge_parse_lint.py -v` → 모두 PASS.

- [ ] **Step 5: Commit**
```bash
cd ~/ATOMOS_BRAIN-brain && git add scripts/links.py tests/test_knowledge_parse_lint.py && \
  git commit -m "feat(brain-v2): pure wikilink utils (extract/resolve/build_link_rows)"
```

### Task 2: seed가 링크테이블 재구축

**Files:** Modify `scripts/seed_atomos_knowledge.py`.

- [ ] **Step 1: seed에 링크 적재 추가.** 파일 상단 import에 `from scripts.links import build_link_rows` 추가(이미 `import urllib.parse`, `requests` 있음 — 없으면 추가). `main()`에서 노트 upsert 루프가 끝난 직후, `return 0` 전에 다음 블록을 추가(현재 `main()`을 읽고 노트 upsert 직후에 삽입):

```python
    # ── 링크테이블 재구축(atomos_knowledge_links) ──
    link_rows = build_link_rows(rows)
    # 1) 현재 노트들의 기존 링크 삭제(per-from_path)
    for r in rows:
        fp = urllib.parse.quote(r["source_path"], safe="")
        requests.delete(f"{url}/rest/v1/atomos_knowledge_links?from_path=eq.{fp}",
                        headers=h, timeout=30)
    # 2) reconcile: 삭제된 노트의 링크 제거
    lresp = requests.get(f"{url}/rest/v1/atomos_knowledge_links?select=from_path",
                         headers=h, timeout=30)
    lresp.raise_for_status()
    existing_links = lresp.json()
    if not isinstance(existing_links, list):
        raise RuntimeError(f"unexpected links response: {existing_links!r}")
    for row in existing_links:
        fp = row.get("from_path")
        if fp and fp not in keep:
            requests.delete(
                f"{url}/rest/v1/atomos_knowledge_links?from_path=eq.{urllib.parse.quote(fp, safe='')}",
                headers=h, timeout=30)
    # 3) 현재 링크 삽입
    for lr in link_rows:
        rr = requests.post(f"{url}/rest/v1/atomos_knowledge_links",
                           headers={**h, "Prefer": "return=minimal"}, json=lr, timeout=30)
        if rr.status_code >= 300:
            print("  link insert:", lr["from_path"], "->", rr.status_code, rr.text)
    print(f"linked {len(link_rows)} edges")
```
(`keep`는 기존 main()에서 이미 정의된 현재 source_path 집합 — 노트 reconcile에서 씀. 없으면 `keep = {r["source_path"] for r in rows}` 추가.)

- [ ] **Step 2: import 동작 확인(라이브 호출 없이).** `wsl -d Ubuntu -- bash -lc 'cd ~/ATOMOS_BRAIN-brain && .venv/bin/python -c "import scripts.seed_atomos_knowledge; print(\"import ok\")"'` → `import ok`. (실제 seed 실행은 라이브 DB·v1 적용 후 — 보류. 링크 빌드 로직은 Task 1 `build_link_rows` 단위테스트로 이미 검증됨.)

- [ ] **Step 3: Commit**
```bash
cd ~/ATOMOS_BRAIN-brain && git add scripts/seed_atomos_knowledge.py && \
  git commit -m "feat(brain-v2): seed rebuilds atomos_knowledge_links (per-from_path + reconcile)"
```

### Task 3: lint 크로스파일 missing-link / orphan (TDD)

**Files:** Modify `scripts/lint_knowledge.py`, `tests/test_knowledge_parse_lint.py`.

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_knowledge_parse_lint.py` 끝에:

```python
from scripts.lint_knowledge import _lint_links

def test_lint_links_missing_and_orphan(capsys):
    docs = [
        ("a.md", {"source_path": "a.md", "body": "[[b]] and [[ghost]]"}),
        ("b.md", {"source_path": "b.md", "body": "no links"}),
        ("c.md", {"source_path": "c.md", "body": "lonely"}),
    ]
    _lint_links(docs)
    out = capsys.readouterr().out
    assert "미해소 링크 [[ghost]]" in out      # a.md → ghost 미해소
    assert "c.md: orphan" in out               # c: in/out 모두 0
    assert "a.md: orphan" not in out           # a: outbound 있음
    assert "b.md: orphan" not in out           # b: inbound 있음(a→b)
```

- [ ] **Step 2: 실패 확인** — `... pytest tests/test_knowledge_parse_lint.py -k lint_links -v` → FAIL (`cannot import name '_lint_links'`).

- [ ] **Step 3: 구현.** `scripts/lint_knowledge.py` 상단에 `from scripts.links import extract_links, resolve_target` 추가. `_lint_links` 함수 추가(파일 내 `main` 위):

```python
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
```
그리고 `main(argv)`를 수정해 파싱된 doc들을 모았다가 크로스파일 패스를 호출한다. 현재 `main`의 per-file 루프에서 파싱 성공한 doc을 리스트에 모으고, 루프 뒤 `_lint_links(docs)`를 호출:

```python
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
    _lint_links(docs)   # missing-link / orphan (WARN)
    print(f"lint: {len(files)} files, {errors} error(s)")
    return 1 if errors else 0
```
(이미 v1에서 `parse_doc`가 try/except로 감싸져 있다면 그 구조를 유지하되 `docs.append`를 추가. 현재 파일을 읽고 통합하라.)

- [ ] **Step 4: 통과 확인** — `... pytest tests/test_knowledge_parse_lint.py -v` → 전부 PASS. 그리고 실제 지식 디렉터리 lint: `.venv/bin/python scripts/lint_knowledge.py` → `lint: 2 files, 0 error(s)`(시드 2개는 링크 없음 → 둘 다 orphan WARN이 뜰 수 있음; ERROR 0이면 OK. WARN 출력은 정상).

- [ ] **Step 5: Commit**
```bash
cd ~/ATOMOS_BRAIN-brain && git add scripts/lint_knowledge.py tests/test_knowledge_parse_lint.py && \
  git commit -m "feat(brain-v2): lint cross-file missing-link + orphan (WARN)"
```

---

# Slice 4b — 백링크 RPC + note EP (FastAPI)

> 워크트리 `~/FastAPI-brain`. 테스트: `/home/glen_85/FastAPI/venv/bin/python -m pytest tests/test_brain_auth.py tests/test_brain_routes.py -v`.

### Task 4: migration 009 (RPC 2개; 008 미수정)

**Files:** Create `migrations/009_atomos_brain_backlinks.sql`.

- [ ] **Step 1: 작성** — 정확히:
```sql
-- 009_atomos_brain_backlinks.sql
-- v2 백링크: 008의 atomos_knowledge_links + atomos_tier_rank 위 권한필터 RPC.
-- 전제: 008 적용 필수.
create or replace function atomos_knowledge_backlinks_v2(
  p_source_path text, p_scopes text[], p_tier text
) returns table(source_path text, title text)
language sql stable as $$
  select k.source_path, k.title
  from atomos_knowledge_links l
  join atomos_knowledge k on k.source_path = l.from_path
  where l.to_path = p_source_path and l.resolved
    and (p_scopes is null or k.scope = any(p_scopes))
    and atomos_tier_rank(p_tier) >= atomos_tier_rank(k.read_tier)
  order by k.title;
$$;
revoke all on function atomos_knowledge_backlinks_v2(text, text[], text) from anon;
grant execute on function atomos_knowledge_backlinks_v2(text, text[], text) to service_role;

create or replace function atomos_knowledge_outlinks_v2(
  p_source_path text, p_scopes text[], p_tier text
) returns table(source_path text, title text)
language sql stable as $$
  select k.source_path, k.title
  from atomos_knowledge_links l
  join atomos_knowledge k on k.source_path = l.to_path
  where l.from_path = p_source_path and l.resolved
    and (p_scopes is null or k.scope = any(p_scopes))
    and atomos_tier_rank(p_tier) >= atomos_tier_rank(k.read_tier)
  order by k.title;
$$;
revoke all on function atomos_knowledge_outlinks_v2(text, text[], text) from anon;
grant execute on function atomos_knowledge_outlinks_v2(text, text[], text) to service_role;
```
- [ ] **Step 2: 적용은 보류**(라이브 DB·008 선행 — v1 ship 시퀀스에 포함). 파일만.
- [ ] **Step 3: Commit**
```bash
cd ~/FastAPI-brain && git add migrations/009_atomos_brain_backlinks.sql && \
  git commit -m "feat(brain-v2): migration 009 — backlinks/outlinks tier-aware RPCs"
```

### Task 5: note EP가 backlinks/outlinks 채움 (TDD)

**Files:** Modify `app/api/routes/brain.py`, `tests/test_brain_routes.py`.

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_brain_routes.py` 끝에:
```python
def test_note_includes_backlinks_and_outlinks(client, monkeypatch):
    def rows_for(name):
        if name == "atomos_knowledge_get_v2":
            return [{"source_path": "dept/sales/x.md", "title": "X", "scope": "dept:sales",
                     "read_tier": "ATOMOS_MASTER", "read_roles": ["ANALYST"], "tags": [], "body": "본문"}]
        if name == "atomos_knowledge_backlinks_v2":
            return [{"source_path": "global/g.md", "title": "G"}]
        if name == "atomos_knowledge_outlinks_v2":
            return [{"source_path": "dept/sales/y.md", "title": "Y"}]
        return []
    class FakeClient:
        def rpc(self, name, params):
            return _StubRPC(rows_for(name))
    async def fake_get_supabase():
        return FakeClient()
    monkeypatch.setattr(brain, "get_supabase", fake_get_supabase)
    r = client.get("/api/brain/notes", params={"path": "dept/sales/x.md"})
    assert r.status_code == 200
    body = r.json()
    assert body["backlinks"] == [{"source_path": "global/g.md", "title": "G"}]
    assert body["outlinks"] == [{"source_path": "dept/sales/y.md", "title": "Y"}]
```
(`_StubRPC`·`client` 픽스처는 기존 파일에 있음 — `_StubRPC.execute`는 async이고 `client` 픽스처가 reader를 MASTER로 오버라이드.)

- [ ] **Step 2: 실패 확인** — `... pytest tests/test_brain_routes.py -k backlinks_and_outlinks -v` → FAIL (현재 note EP는 `backlinks:[]/outlinks:[]` 고정).

- [ ] **Step 3: 구현** — `brain.py` `brain_note`를 다음으로 교체(404 후, 두 RPC 호출 추가):
```python
@router.get("/notes")
async def brain_note(path: str = Query(...), reader: BrainReader = Depends(require_brain_reader)):
    client = await get_supabase()
    res = await client.rpc("atomos_knowledge_get_v2", {
        "p_source_path": path, "p_scopes": reader.scopes, "p_tier": reader.tier,
    }).execute()
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="not found")
    row = rows[0]
    bl = await client.rpc("atomos_knowledge_backlinks_v2", {
        "p_source_path": path, "p_scopes": reader.scopes, "p_tier": reader.tier,
    }).execute()
    ol = await client.rpc("atomos_knowledge_outlinks_v2", {
        "p_source_path": path, "p_scopes": reader.scopes, "p_tier": reader.tier,
    }).execute()
    return {
        "source_path": row.get("source_path"), "title": row.get("title"),
        "scope": row.get("scope"), "read_tier": row.get("read_tier"),
        "read_roles": row.get("read_roles") or [], "tags": row.get("tags") or [],
        "body_md": row.get("body") or "",
        "backlinks": bl.data or [], "outlinks": ol.data or [],
    }
```

- [ ] **Step 4: 통과 확인** — `... pytest tests/test_brain_auth.py tests/test_brain_routes.py -v` → 전부 PASS(기존 `test_note_404_when_no_row` 포함 — 404는 backlinks 호출 전에 단락). 

- [ ] **Step 5: Commit**
```bash
cd ~/FastAPI-brain && git add app/api/routes/brain.py tests/test_brain_routes.py && \
  git commit -m "feat(brain-v2): note EP fills permission-filtered backlinks/outlinks"
```

---

# Slice 4c — 프론트 패널 + 클릭 네비 (hbs-dashboard)

> 워크트리 `~/hbs-dashboard-brain`. 테스트/빌드: `npm run test:run` · `npm run build`.

### Task 6: 타입 + wikilink→markdown 유틸 (TDD) + 패널/렌더

**Files:** Modify `src/api/types.ts`, `src/pages/Admin/brainWikilink.ts`, `src/pages/Admin/brainWikilink.test.ts`, `src/pages/Admin/BrainReference.tsx`.

- [ ] **Step 1: 타입 정정** — `src/api/types.ts`에서 `BrainNoteDetail`의 `backlinks`/`outlinks`를 바꾸고 `BrainLinkRef` 추가:
```typescript
export interface BrainLinkRef { source_path: string; title: string; }
```
그리고 `BrainNoteDetail` 안의 `backlinks: string[];` `outlinks: string[];` 두 줄을 `backlinks: BrainLinkRef[];` `outlinks: BrainLinkRef[];`로 교체.

- [ ] **Step 2: 실패 테스트 추가** — `src/pages/Admin/brainWikilink.test.ts`에 추가:
```typescript
import { wikilinksToMarkdown } from "./brainWikilink";

describe("wikilinksToMarkdown", () => {
  it("converts [[t]] to a brain: link", () => {
    expect(wikilinksToMarkdown("see [[dept/sales/x]]")).toBe(
      "see [dept/sales/x](brain:dept/sales/x)");
  });
  it("uses the label form", () => {
    expect(wikilinksToMarkdown("[[a/b|라벨]]")).toBe("[라벨](brain:a/b)");
  });
  it("leaves plain text untouched", () => {
    expect(wikilinksToMarkdown("no links here")).toBe("no links here");
  });
});
```

- [ ] **Step 3: 실패 확인** — `npm run test:run -- brainWikilink` → 새 테스트 FAIL(`wikilinksToMarkdown` 없음).

- [ ] **Step 4: 구현 유틸** — `src/pages/Admin/brainWikilink.ts` 끝에 추가:
```typescript
/** 본문 [[target|label]] / [[target]] → 마크다운 링크 [label](brain:target). 클릭 네비용. */
export function wikilinksToMarkdown(md: string): string {
  return md.replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
    (_m, target: string, label?: string) =>
      `[${(label ?? target).trim()}](brain:${target.trim()})`);
}
```

- [ ] **Step 5: 통과 확인** — `npm run test:run -- brainWikilink` → 전부 PASS.

- [ ] **Step 6: 페이지에 패널 + 클릭 렌더 통합** — `src/pages/Admin/BrainReference.tsx` 수정:
  1. import에 추가: `import { wikilinksToMarkdown } from "./brainWikilink";`
  2. 컴포넌트 안에 헬퍼 추가(상단, return 전): 
```tsx
  const normalize = (t: string) => (t.endsWith(".md") ? t : t + ".md");
```
  3. 노트 본문 렌더(`<ReactMarkdown>{noteQ.data.body_md}</ReactMarkdown>`)를 다음으로 교체:
```tsx
                <div style={{ fontSize: 14, lineHeight: 1.7 }}>
                  <ReactMarkdown
                    components={{
                      a: ({ href, children }) =>
                        href && href.startsWith("brain:") ? (
                          <button type="button"
                            onClick={() => setSelected(normalize(href.slice("brain:".length)))}
                            style={{ background: "none", border: "none", padding: 0,
                              color: "var(--hbs-accent, #2563eb)", cursor: "pointer",
                              font: "inherit", textDecoration: "underline" }}>
                            {children}
                          </button>
                        ) : (
                          <a href={href} target="_blank" rel="noreferrer">{children}</a>
                        ),
                    }}
                  >
                    {wikilinksToMarkdown(noteQ.data.body_md)}
                  </ReactMarkdown>
                </div>
                {(noteQ.data.backlinks.length > 0 || noteQ.data.outlinks.length > 0) && (
                  <div style={{ marginTop: 20, borderTop: "1px solid var(--border,#e5e7eb)", paddingTop: 12 }}>
                    {noteQ.data.outlinks.length > 0 && (
                      <div style={{ marginBottom: 10 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-sub)", marginBottom: 4 }}>→ 아웃링크</div>
                        {noteQ.data.outlinks.map((l) => (
                          <button key={l.source_path} type="button" onClick={() => setSelected(l.source_path)}
                            style={{ display: "block", background: "none", border: "none", padding: "2px 0",
                              color: "var(--hbs-accent, #2563eb)", cursor: "pointer", font: "inherit", textAlign: "left" }}>
                            {l.title}
                          </button>
                        ))}
                      </div>
                    )}
                    {noteQ.data.backlinks.length > 0 && (
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-sub)", marginBottom: 4 }}>← 백링크</div>
                        {noteQ.data.backlinks.map((l) => (
                          <button key={l.source_path} type="button" onClick={() => setSelected(l.source_path)}
                            style={{ display: "block", background: "none", border: "none", padding: "2px 0",
                              color: "var(--hbs-accent, #2563eb)", cursor: "pointer", font: "inherit", textAlign: "left" }}>
                            {l.title}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
```
  (이 블록은 기존 `<article>` 안, 본문 `<div>` 다음에 들어간다 — `noteQ.data &&` 분기 내부. 현재 파일을 읽고 `<ReactMarkdown>` 위치를 찾아 교체·삽입하라.)

- [ ] **Step 7: 빌드 + 테스트** — `npm run build`(타입 0 에러 — `BrainLinkRef[]`로 `.length`/`.map` 동작) + `npm run test:run`(전부 그린).

- [ ] **Step 8: Commit**
```bash
cd ~/hbs-dashboard-brain && git add src/api/types.ts src/pages/Admin/brainWikilink.ts src/pages/Admin/brainWikilink.test.ts src/pages/Admin/BrainReference.tsx && \
  git commit -m "feat(brain-v2): backlink/outlink panels + clickable in-body wikilinks"
```

---

## 범위 밖 (이 플랜 비포함)
- 그래프(react-force-graph) · pgvector 의미검색 · 학습루프 본체 — 각자 트리거 충족 시 별도 스펙.
- 009 *적용* + 실 seed 링크적재 + E2E — v1 ship 시퀀스(007+008 적용·ingest 라이브)에 종속, 그때 함께.

## 자기검토 (Self-Review)
**스펙 커버리지:**
- §1 해소(source_path, .md 폴백) → Task 1 `resolve_target`. ✅
- §2.1 ingest 링크추출·재구축 → Task 1 `build_link_rows` + Task 2 seed. ✅
- §2.2 lint missing-link/orphan → Task 3. ✅
- §3.1 009 RPC → Task 4. §3.2 note EP 채움 → Task 5. ✅
- §4.1 타입 정정 → Task 6 Step 1. §4.2 패널 + 본문 클릭(brain: href) → Task 6 Step 6. ✅
- §5 권한필터(양방향 숨김) → 009 RPC의 scope/tier 필터(Task 4). ✅
- §6 테스트 → 각 Task TDD. ✅

**플레이스홀더 스캔:** 모든 코드 스텝에 실제 코드·명령·기대 출력. seed/lint/page는 "현재 파일 읽고 통합" 지시 + 정확한 삽입 코드 제공(기존 파일 확장이라 불가피, 삽입 블록은 완전).

**타입/이름 일관성:** `build_link_rows`/`extract_links`/`resolve_target`(links.py) ↔ seed·lint import 일치. RPC명 `atomos_knowledge_backlinks_v2`/`atomos_knowledge_outlinks_v2`(009) ↔ brain.py 호출 일치. 응답 `{source_path,title}` ↔ FE `BrainLinkRef{source_path,title}` 일치. `wikilinksToMarkdown` `brain:` href ↔ 페이지 `a` 렌더러 `brain:` 분기 일치. `normalize`(.md 폴백) ↔ resolve_target(.md 폴백) 동일 규칙.
- [ ] 사용자 리뷰 → 실행
