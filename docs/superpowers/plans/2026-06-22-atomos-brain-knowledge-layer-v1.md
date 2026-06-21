# ATOMOS BRAIN 지식 레이어 v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사람이 콘솔에서 ATOMOS 지식 위키를 권한대로(서버측 강제) 검색·열람하는 "BRAIN 참조" v1 + 그 지식을 git push로 색인·검증하는 ingest/lint 파이프라인.

**Architecture:** 지식 SSOT = `ATOMOS_BRAIN/knowledge/**.md`(frontmatter `scope`/`read_tier`/`read_roles`/`tags`). GitHub Action이 push마다 lint(ERROR면 차단) → Supabase `atomos_knowledge` 색인. FastAPI가 사람의 Supabase JWT를 `auth.get_user()`로 검증→`app_users.role`→BRAIN tier 매핑→tier-aware RPC(`atomos_knowledge_search_v2`)로 **서버측 필터**(클라 필터 0). 콘솔 `/admin/brain` 페이지가 검색·노트뷰·스코프탐색을 React로 렌더. **에이전트 경로(Phase 1의 007 RPC·`tools.py`)는 일절 수정하지 않는다** — 사람은 새 v2 함수를 쓴다.

**Tech Stack:** FastAPI + supabase-py(async) + Postgres FTS; React 19 + React Router v7 + TanStack Query v5 + axios + react-markdown; Python(ingest/lint, python-frontmatter); GitHub Actions.

**실행 환경:** 정본=WSL. 모든 명령은 WSL Ubuntu에서 실행(`wsl -d Ubuntu -- bash -lc "cd ~/REPO && …"`). 편집은 UNC `\\wsl.localhost\ubuntu\home\glen_85\…`.

---

## ⚠️ 선행 조건 (Prerequisites — 실행 전 충족 필수)

1. **Phase 1 병합 완료**: `feat/atomos-phase1-hermes-mcp`가 `main`에 병합 + `migrations/007_atomos_phase1_mcp.sql` 적용(= `atomos_knowledge` 테이블·007 RPC 존재). 이 플랜은 그 위에 008을 얹는다.
2. **Supabase 접근**: 마이그레이션 008 적용 권한(operator).
3. **GitHub Action 시크릿**(operator 수동 등록, ATOMOS_BRAIN repo Settings → Secrets): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`.
4. **각 repo의 작업 브랜치**: 기능 브랜치에서 작업(예: FastAPI `feat/brain-knowledge-layer`, hbs-dashboard `feat/brain-reference-page`, ATOMOS_BRAIN `feat/knowledge-ingest-lint`). **`feat/atomos-phase1-hermes-mcp` 및 D-COGS 미커밋 파일 수정 금지.**

---

## 파일 구조 (생성/수정)

### FastAPI (`~/FastAPI`)
- **Create** `migrations/008_atomos_brain_knowledge_layer.sql` — `read_tier`·`tags`·v2 예약 컬럼, `atomos_tier_rank()`, `atomos_knowledge_search_v2()`(사람 tier-aware), `atomos_knowledge_links` 테이블. (007·tools.py 미수정)
- **Create** `app/api/routes/brain.py` — `require_brain_reader` 의존성 + `BrainReader` + `ROLE_TIER` + 스코프 빌더 + 3 EP(search/notes/scopes).
- **Modify** `main.py` — brain_router import + include.
- **Create** `tests/test_brain_auth.py` — JWT→tier 매핑·fail-closed 단위 테스트.
- **Create** `tests/test_brain_routes.py` — EP를 `dependency_overrides`로 테스트.

### ATOMOS_BRAIN (`~/ATOMOS_BRAIN`)
- **Modify** `knowledge/global/grounding-rules.md`, `knowledge/dept/sales/anomaly-playbook.md` — `read_tier: ATOMOS_MASTER` 추가(백필).
- **Modify** `scripts/seed_atomos_knowledge.py` — python-frontmatter 파서, `read_tier`·`tags` 적재, 삭제 reconcile.
- **Create** `scripts/lint_knowledge.py` — frontmatter 검증(ERROR/WARN), 종료코드.
- **Create** `scripts/requirements.txt` — requests, python-frontmatter, pytest.
- **Create** `tests/test_knowledge_parse_lint.py` — parse + lint 단위 테스트.
- **Create** `.github/workflows/knowledge-index.yml` — push(knowledge/**) → lint → seed.

### hbs-dashboard (`~/hbs-dashboard`)
- **Modify** `src/api/client.ts` — Supabase JWT 요청 인터셉터 + `brainApi`.
- **Modify** `src/api/types.ts` — brain 응답 타입.
- **Modify** `src/App.tsx` — `/admin/brain` 라우트.
- **Modify** `src/auth/permissions.ts` — `/admin/brain` 엔트리.
- **Create** `src/pages/Admin/BrainReference.tsx` — 페이지(검색·노트뷰·스코프탐색).
- **Create** `src/pages/Admin/brainWikilink.ts` + `src/pages/Admin/brainWikilink.test.ts` — `[[wikilink]]` 파서(순수, vitest).
- **Modify** `package.json` — `react-markdown` 추가.

---

# Slice 1 — 스키마 + ingest + lint

> 결과: 지식 편집(git push)이 lint 통과 시 Supabase에 색인됨. tier-aware 검색 함수 준비 완료.

### Task 1: 마이그레이션 008 — 컬럼·tier_rank·v2 검색함수·링크테이블

**Files:**
- Create: `migrations/008_atomos_brain_knowledge_layer.sql`

- [ ] **Step 1: 마이그레이션 작성**

```sql
-- 008_atomos_brain_knowledge_layer.sql
-- BRAIN 지식 레이어 v1: 4계층 권한(read_tier) + 태그 + v2 예약 + 사람 tier-aware 검색.
-- 정본: ATOMOS_BRAIN/docs/superpowers/specs/2026-06-22-atomos-brain-knowledge-layer-design.md
-- 주의: 007(에이전트 경로: atomos_knowledge_search, app/mcp_server/tools.py)는 건드리지 않는다.
--       사람은 새 함수 atomos_knowledge_search_v2 를 쓴다. 추후 통합은 별도 작업.

-- ── 컬럼 추가 (기존 행은 read_tier 기본 ATOMOS_MASTER = fail-closed) ──
alter table atomos_knowledge
  add column if not exists read_tier  text    not null default 'ATOMOS_MASTER',
  add column if not exists tags       text[]  not null default '{}',
  add column if not exists source     text,        -- v2 inert
  add column if not exists verified   boolean,     -- v2 inert
  add column if not exists confidence numeric,     -- v2 inert
  add column if not exists supersedes text;         -- v2 inert

create index if not exists atomos_knowledge_read_tier_idx on atomos_knowledge(read_tier);

-- ── tier 단조 rank ──
create or replace function atomos_tier_rank(t text) returns int language sql immutable as $$
  select case t
    when 'STORE_OWNER'   then 0
    when 'HQ_STAFF'      then 1
    when 'HQ_EXEC'       then 2
    when 'ATOMOS_MASTER' then 3
    else 99 end;   -- 미지 tier = 사실상 차단(요청 tier가 99면 어떤 read_tier도 통과 못 함)
$$;

-- ── 사람 tier-aware 검색 (p_scopes IS NULL = 스코프 무제한; tier rank로 read_tier 게이트) ──
create or replace function atomos_knowledge_search_v2(
  p_query  text,
  p_scopes text[],     -- NULL = 전 스코프(MASTER/EXEC). 그 외 = 허용 스코프 화이트리스트.
  p_tier   text,       -- 요청자 사람 tier
  p_limit  int default 20
) returns table(source_path text, scope text, read_tier text, title text,
                tags text[], snippet text, rank real)
language sql stable as $$
  select k.source_path, k.scope, k.read_tier, k.title, k.tags,
         left(k.body, 280) as snippet,
         ts_rank(k.ts, plainto_tsquery('simple', coalesce(p_query,''))) as rank
  from atomos_knowledge k
  where (p_scopes is null or k.scope = any(p_scopes))
    and atomos_tier_rank(p_tier) >= atomos_tier_rank(k.read_tier)
    and (coalesce(p_query,'') = '' or k.ts @@ plainto_tsquery('simple', p_query))
  order by rank desc, k.created_at desc
  limit greatest(p_limit, 1);
$$;

revoke all on function atomos_knowledge_search_v2(text, text[], text, int) from anon;
grant execute on function atomos_knowledge_search_v2(text, text[], text, int) to service_role;

-- ── 단건 노트 조회(사람 tier-aware) — 권한 밖이면 0행(404로 매핑) ──
create or replace function atomos_knowledge_get_v2(
  p_source_path text, p_scopes text[], p_tier text
) returns table(source_path text, scope text, read_tier text, read_roles text[],
                title text, tags text[], body text)
language sql stable as $$
  select k.source_path, k.scope, k.read_tier, k.read_roles, k.title, k.tags, k.body
  from atomos_knowledge k
  where k.source_path = p_source_path
    and (p_scopes is null or k.scope = any(p_scopes))
    and atomos_tier_rank(p_tier) >= atomos_tier_rank(k.read_tier)
  limit 1;
$$;

revoke all on function atomos_knowledge_get_v2(text, text[], text) from anon;
grant execute on function atomos_knowledge_get_v2(text, text[], text) to service_role;

-- ── 스코프 목록(사람 tier-aware) — 가시 노트 수 ──
create or replace function atomos_knowledge_scopes_v2(
  p_scopes text[], p_tier text
) returns table(scope text, count bigint)
language sql stable as $$
  select k.scope, count(*)::bigint
  from atomos_knowledge k
  where (p_scopes is null or k.scope = any(p_scopes))
    and atomos_tier_rank(p_tier) >= atomos_tier_rank(k.read_tier)
  group by k.scope
  order by k.scope;
$$;

revoke all on function atomos_knowledge_scopes_v2(text[], text) from anon;
grant execute on function atomos_knowledge_scopes_v2(text[], text) to service_role;

-- ── 링크(백링크·그래프·lint missing-link 공용) — v1은 스키마만, 채움은 Slice 4 ──
create table if not exists atomos_knowledge_links (
  from_path text not null,
  to_ref    text not null,
  to_path   text,
  resolved  boolean not null default false,
  primary key (from_path, to_ref)
);
create index if not exists atomos_knowledge_links_to_idx on atomos_knowledge_links(to_path);
```

- [ ] **Step 2: 마이그레이션 적용 (operator/Supabase)**

Run (Supabase SQL editor 또는 psql로 008 실행). 적용 후 검증:
```sql
\d atomos_knowledge
select atomos_tier_rank('HQ_EXEC');   -- expect 2
select * from atomos_knowledge_search_v2('급락', NULL, 'ATOMOS_MASTER', 5);  -- 기존 시드 행 반환
select * from atomos_knowledge_search_v2('급락', NULL, 'STORE_OWNER', 5);    -- 0행(시드는 read_tier=MASTER)
```
Expected: `read_tier`/`tags`/`source`/`verified`/`confidence`/`supersedes` 컬럼 존재; `atomos_tier_rank('HQ_EXEC')`=2; MASTER 검색은 시드 반환, STORE_OWNER 검색은 0행.

- [ ] **Step 3: Commit**

```bash
cd ~/FastAPI && git add migrations/008_atomos_brain_knowledge_layer.sql && \
  git commit -m "feat(brain): migration 008 — read_tier/tags + tier-aware v2 search RPCs + links table"
```

---

### Task 2: 시드 파일 read_tier 백필

**Files:**
- Modify: `knowledge/global/grounding-rules.md`
- Modify: `knowledge/dept/sales/anomaly-playbook.md`

- [ ] **Step 1: 두 파일 frontmatter에 `read_tier` 추가**

`knowledge/global/grounding-rules.md` frontmatter를:
```yaml
---
scope: global
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 분석 그라운딩 규칙
---
```
`knowledge/dept/sales/anomaly-playbook.md` frontmatter를:
```yaml
---
scope: dept:sales
read_tier: ATOMOS_MASTER
read_roles: [ANALYST]
title: 매출 급락 대응 플레이북 (D-SALES)
---
```
(둘 다 에이전트 분석규율 → 사람은 MASTER만 열람. 에이전트는 read_roles로 접근 유지.)

- [ ] **Step 2: Commit** (ingest 검증은 Task 5 이후)

```bash
cd ~/ATOMOS_BRAIN && git add knowledge/global/grounding-rules.md knowledge/dept/sales/anomaly-playbook.md && \
  git commit -m "feat(brain): backfill read_tier on seed knowledge (ATOMOS_MASTER)"
```

---

### Task 3: lint 스크립트 (TDD)

**Files:**
- Create: `scripts/requirements.txt`
- Create: `scripts/lint_knowledge.py`
- Create: `tests/test_knowledge_parse_lint.py`

- [ ] **Step 1: 의존성 파일 작성**

`scripts/requirements.txt`:
```
requests>=2.31.0
python-frontmatter>=1.1.0
pytest>=8.0.0
```

- [ ] **Step 2: 실패 테스트 작성** — `tests/test_knowledge_parse_lint.py`

```python
import frontmatter
from scripts.lint_knowledge import lint_doc, VALID_TIERS, ROLE_REGISTRY, SCOPE_RE

def _doc(meta: dict, body: str = "본문") -> dict:
    post = frontmatter.Post(body, **meta)
    parsed = {
        "scope": meta.get("scope"),
        "read_tier": meta.get("read_tier"),
        "read_roles": meta.get("read_roles"),
        "title": meta.get("title"),
        "tags": meta.get("tags", []),
        "source_path": "x/y.md",
    }
    return parsed

def test_valid_doc_no_errors():
    findings = lint_doc(_doc({"scope": "global", "read_tier": "HQ_STAFF",
                              "read_roles": ["ANALYST"], "title": "T"}))
    assert [f for f in findings if f.level == "ERROR"] == []

def test_missing_scope_is_error():
    findings = lint_doc(_doc({"read_tier": "HQ_STAFF", "title": "T"}))
    assert any(f.level == "ERROR" and "scope" in f.message for f in findings)

def test_bad_scope_syntax_is_error():
    findings = lint_doc(_doc({"scope": "bogus", "read_tier": "HQ_STAFF", "title": "T"}))
    assert any(f.level == "ERROR" and "scope" in f.message for f in findings)

def test_missing_title_is_error():
    findings = lint_doc(_doc({"scope": "global", "read_tier": "HQ_STAFF"}))
    assert any(f.level == "ERROR" and "title" in f.message for f in findings)

def test_bad_tier_enum_is_error():
    findings = lint_doc(_doc({"scope": "global", "read_tier": "BOSS", "title": "T"}))
    assert any(f.level == "ERROR" and "read_tier" in f.message for f in findings)

def test_missing_read_tier_is_warn_not_error():
    findings = lint_doc(_doc({"scope": "global", "title": "T"}))
    assert any(f.level == "WARN" and "read_tier" in f.message for f in findings)
    assert [f for f in findings if f.level == "ERROR"] == []

def test_unknown_role_is_warn():
    findings = lint_doc(_doc({"scope": "global", "read_tier": "HQ_STAFF",
                              "read_roles": ["WIZARD"], "title": "T"}))
    assert any(f.level == "WARN" and "WIZARD" in f.message for f in findings)
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd ~/ATOMOS_BRAIN && python -m pip install -r scripts/requirements.txt -q && python -m pytest tests/test_knowledge_parse_lint.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.lint_knowledge` (아직 미작성).

- [ ] **Step 4: lint 스크립트 구현** — `scripts/lint_knowledge.py`

```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd ~/ATOMOS_BRAIN && python -m pytest tests/test_knowledge_parse_lint.py -v`
Expected: PASS (7 passed).

- [ ] **Step 6: 실제 지식 파일에 lint 실행 (시드 검증)**

Run: `cd ~/ATOMOS_BRAIN && python scripts/lint_knowledge.py`
Expected: `lint: 2 files, 0 error(s)` (백필된 시드는 ERROR 0).

- [ ] **Step 7: Commit**

```bash
cd ~/ATOMOS_BRAIN && git add scripts/requirements.txt scripts/lint_knowledge.py tests/test_knowledge_parse_lint.py && \
  git commit -m "feat(brain): knowledge lint (frontmatter validation, ERROR blocks ingest)"
```

---

### Task 4: seed 스크립트 강화 — read_tier·tags·삭제 reconcile (TDD)

**Files:**
- Modify: `scripts/seed_atomos_knowledge.py`
- Modify: `tests/test_knowledge_parse_lint.py` (parse 테스트 추가)

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_knowledge_parse_lint.py` 끝에 추가

```python
from scripts.seed_atomos_knowledge import parse_row

def test_parse_row_reads_tier_and_tags(tmp_path):
    p = tmp_path / "n.md"
    p.write_text("---\nscope: store:ST-1\nread_tier: HQ_STAFF\n"
                 "read_roles: [ANALYST]\ntags: [매출, 급락]\ntitle: T\n---\n본문입니다",
                 encoding="utf-8")
    row = parse_row(str(p), str(tmp_path))
    assert row["scope"] == "store:ST-1"
    assert row["read_tier"] == "HQ_STAFF"
    assert row["read_roles"] == ["ANALYST"]
    assert row["tags"] == ["매출", "급락"]
    assert row["title"] == "T"
    assert row["body"] == "본문입니다"
    assert row["source_path"] == "n.md"

def test_parse_row_defaults_tier_to_master(tmp_path):
    p = tmp_path / "n.md"
    p.write_text("---\nscope: global\ntitle: T\n---\n본문", encoding="utf-8")
    row = parse_row(str(p), str(tmp_path))
    assert row["read_tier"] == "ATOMOS_MASTER"
    assert row["read_roles"] == []
    assert row["tags"] == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/ATOMOS_BRAIN && python -m pytest tests/test_knowledge_parse_lint.py -k parse_row -v`
Expected: FAIL — `ImportError: cannot import name 'parse_row'`.

- [ ] **Step 3: seed 스크립트 재작성** — `scripts/seed_atomos_knowledge.py` 전체 교체

```python
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

    # 삭제 reconcile: 리포에 더 없는 source_path 행 제거
    existing = requests.get(f"{url}/rest/v1/atomos_knowledge?select=source_path",
                            headers=h, timeout=30).json()
    for row in existing:
        sp = row.get("source_path")
        if sp and sp not in keep:
            requests.delete(f"{url}/rest/v1/atomos_knowledge?source_path=eq.{sp}", headers=h, timeout=30)
            print("deleted", sp)

    # upsert(멱등): 같은 source_path 삭제 후 삽입
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/ATOMOS_BRAIN && python -m pytest tests/test_knowledge_parse_lint.py -v`
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/ATOMOS_BRAIN && git add scripts/seed_atomos_knowledge.py tests/test_knowledge_parse_lint.py && \
  git commit -m "feat(brain): seed reads read_tier/tags + deletion reconcile (python-frontmatter)"
```

---

### Task 5: GitHub Action — push 시 lint→seed 색인

**Files:**
- Create: `.github/workflows/knowledge-index.yml`

- [ ] **Step 1: 워크플로 작성**

```yaml
name: knowledge-index
on:
  push:
    branches: [main]
    paths: ["knowledge/**", "scripts/seed_atomos_knowledge.py", "scripts/lint_knowledge.py"]
  pull_request:
    paths: ["knowledge/**"]
jobs:
  lint-and-index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r scripts/requirements.txt
      - name: Lint knowledge (ERROR blocks)
        run: python scripts/lint_knowledge.py
      - name: Index to Supabase (main push only)
        if: github.event_name == 'push'
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
        run: python scripts/seed_atomos_knowledge.py
```

- [ ] **Step 2: Commit & push (Action 발화 확인)**

```bash
cd ~/ATOMOS_BRAIN && git add .github/workflows/knowledge-index.yml && \
  git commit -m "feat(brain): GitHub Action — lint + index knowledge on push" && git push
```
Expected: push 후 Actions 탭에서 `knowledge-index` 잡 성공(lint 0 error, seed `seeded 2 docs`). (시크릿 미등록 시 seed 스텝 실패 → 선행조건 3 확인.)

> **검증(수동, Supabase)**: `select source_path, scope, read_tier, tags from atomos_knowledge order by source_path;` → 2행, read_tier=ATOMOS_MASTER.

---

# Slice 2 — BRAIN API (FastAPI)

> 결과: 사람 JWT를 검증해 tier로 서버측 필터하는 3개 EP. Phase 1 파일 미수정.

### Task 6: `require_brain_reader` 인증 의존성 (TDD)

**Files:**
- Create: `app/api/routes/brain.py`
- Create: `tests/test_brain_auth.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_brain_auth.py`

```python
import pytest
from app.api.routes import brain


def test_role_tier_maps_super_admin_to_master():
    assert brain.ROLE_TIER.get("super_admin") == "ATOMOS_MASTER"

def test_unmapped_role_has_no_tier():
    # v1: 하위 역할은 미배선(실 점주 온보딩 때 점등)
    assert brain.ROLE_TIER.get("store_manager") is None

def test_scope_filter_master_is_none():
    # MASTER/EXEC = 전 스코프(NULL = RPC가 스코프 무제한)
    assert brain.scope_filter_for("ATOMOS_MASTER", None, []) is None
    assert brain.scope_filter_for("HQ_EXEC", None, []) is None

def test_resolve_reader_rejects_missing_token():
    with pytest.raises(brain.BrainAuthError):
        brain._resolve_reader(authorization=None)

def test_resolve_reader_rejects_bad_scheme():
    with pytest.raises(brain.BrainAuthError):
        brain._resolve_reader(authorization="Token abc")

def test_resolve_reader_super_admin_master(monkeypatch):
    monkeypatch.setattr(brain, "_verify_jwt", lambda tok: "user-1")
    monkeypatch.setattr(brain, "_load_app_user",
                        lambda uid: {"role": "super_admin", "is_active": True,
                                     "br_id_scope": None, "st_id_scope": []})
    reader = brain._resolve_reader(authorization="Bearer good")
    assert reader.tier == "ATOMOS_MASTER"
    assert reader.scopes is None   # 전 스코프

def test_resolve_reader_inactive_forbidden(monkeypatch):
    monkeypatch.setattr(brain, "_verify_jwt", lambda tok: "user-1")
    monkeypatch.setattr(brain, "_load_app_user",
                        lambda uid: {"role": "super_admin", "is_active": False,
                                     "br_id_scope": None, "st_id_scope": []})
    with pytest.raises(brain.BrainAuthError):
        brain._resolve_reader(authorization="Bearer good")

def test_resolve_reader_unmapped_role_forbidden(monkeypatch):
    monkeypatch.setattr(brain, "_verify_jwt", lambda tok: "user-2")
    monkeypatch.setattr(brain, "_load_app_user",
                        lambda uid: {"role": "store_manager", "is_active": True,
                                     "br_id_scope": "BR-1", "st_id_scope": ["ST-1"]})
    with pytest.raises(brain.BrainAuthError):
        brain._resolve_reader(authorization="Bearer good")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && venv/bin/pytest tests/test_brain_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: app.api.routes.brain`.

- [ ] **Step 3: `brain.py` 인증 부분 구현** — `app/api/routes/brain.py` (라우트는 Task 7에서 추가)

```python
"""BRAIN 참조 — 사람이 콘솔에서 권한대로 지식을 검색/열람하는 읽기 전용 API.
강제 지점 = 백엔드(이 모듈) + tier-aware RPC. 클라이언트 필터 금지("숨김=데이터 안 옴").
사람 신원 = Supabase JWT(auth.get_user 검증) → app_users.role → BRAIN tier.
v1: super_admin → ATOMOS_MASTER 만 배선. 하위 tier는 실 점주 온보딩(풀 유저인증) 때 점등.
에이전트 경로(007 RPC / app/mcp_server)는 수정하지 않는다.
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from app.core.supabase import get_supabase

router = APIRouter(prefix="/api/brain", tags=["brain"])

# console role → BRAIN tier. v1 = super_admin 만. 나머지는 None(미배선 → 403).
ROLE_TIER = {"super_admin": "ATOMOS_MASTER"}


class BrainAuthError(Exception):
    pass


@dataclass
class BrainReader:
    user_id: str
    tier: str
    scopes: Optional[list]   # None = 전 스코프(MASTER/EXEC). list = 화이트리스트.


def scope_filter_for(tier: str, br_scope, st_scope) -> Optional[list]:
    """tier → RPC p_scopes 값. MASTER/EXEC = None(무제한). 하위 tier는 v1 미도달."""
    if tier in ("ATOMOS_MASTER", "HQ_EXEC"):
        return None
    # STORE_OWNER/HQ_STAFF 스코프 화이트리스트 산출은 실 점주 온보딩 때 구현(스펙 §6).
    raise NotImplementedError(f"tier {tier} scope resolution deferred to real-owner onboarding")


def _verify_jwt(token: str) -> str:
    """Supabase JWT 검증 → user id. 실패 시 BrainAuthError. (별도 함수 = 테스트 monkeypatch 지점)"""
    import asyncio
    async def _go():
        client = await get_supabase()
        return await client.auth.get_user(token)
    try:
        resp = asyncio.get_event_loop().run_until_complete(_go()) if False else None
    except Exception:
        resp = None
    # NOTE: 동기 헬퍼 회피 — 실제 호출은 라우트(async)에서 await 한다. 아래 async 버전 사용.
    raise BrainAuthError("use _verify_jwt_async")


async def _verify_jwt_async(token: str) -> str:
    client = await get_supabase()
    try:
        resp = await client.auth.get_user(token)
    except Exception as e:
        raise BrainAuthError(f"jwt verify failed: {e}") from e
    user = getattr(resp, "user", None)
    if not user or not getattr(user, "id", None):
        raise BrainAuthError("invalid token: no user")
    return user.id


async def _load_app_user_async(user_id: str) -> dict:
    client = await get_supabase()
    res = await client.table("app_users").select(
        "role,is_active,br_id_scope,st_id_scope").eq("id", user_id).limit(1).execute()
    rows = res.data or []
    if not rows:
        raise BrainAuthError("no app_users row")
    return rows[0]


async def resolve_reader(authorization: Optional[str]) -> BrainReader:
    if not authorization or not authorization.startswith("Bearer "):
        raise BrainAuthError("missing bearer token")
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise BrainAuthError("empty token")
    user_id = await _verify_jwt_async(token)
    profile = await _load_app_user_async(user_id)
    if not profile.get("is_active"):
        raise BrainAuthError("user inactive")
    tier = ROLE_TIER.get(profile.get("role"))
    if not tier:
        raise BrainAuthError(f"BRAIN access not enabled for role {profile.get('role')!r}")
    scopes = scope_filter_for(tier, profile.get("br_id_scope"), profile.get("st_id_scope") or [])
    return BrainReader(user_id=user_id, tier=tier, scopes=scopes)


async def require_brain_reader(
    authorization: Optional[str] = Header(default=None),
) -> BrainReader:
    try:
        return await resolve_reader(authorization)
    except BrainAuthError:
        # fail-closed + 존재여부 누출 금지: 401(인증). 권한 부족은 라우트에서 404와 동일 처리.
        raise HTTPException(status_code=401, detail="unauthorized")
```

> **테스트용 동기 헬퍼**: 위 단위 테스트는 `_verify_jwt`/`_load_app_user`(동기명)와 `_resolve_reader`(동기)를 monkeypatch한다. 테스트 가능하도록 **동기 시임**을 추가한다(아래 Step 3b). async 라우트는 `resolve_reader`(async)를 쓰고, 동기 시임은 그것을 감싼 순수-로직 버전이다.

- [ ] **Step 3b: 테스트가 기대하는 동기 시임 추가** — `brain.py`에 추가

기존 `_verify_jwt`(잘못된 더미)를 **삭제**하고, 순수 로직을 동기로 뽑아 테스트 가능하게 한다:

```python
# ── 순수 로직(테스트 가능) — async 래퍼와 공유 ──
def _verify_jwt(token: str) -> str:           # 테스트에서 monkeypatch
    raise BrainAuthError("not wired in sync path")

def _load_app_user(user_id: str) -> dict:     # 테스트에서 monkeypatch
    raise BrainAuthError("not wired in sync path")

def _resolve_reader(authorization: Optional[str]) -> BrainReader:
    """동기 순수 해석(JWT검증·프로필조회는 주입). 단위 테스트 진입점."""
    if not authorization or not authorization.startswith("Bearer "):
        raise BrainAuthError("missing bearer token")
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise BrainAuthError("empty token")
    user_id = _verify_jwt(token)
    profile = _load_app_user(user_id)
    if not profile.get("is_active"):
        raise BrainAuthError("user inactive")
    tier = ROLE_TIER.get(profile.get("role"))
    if not tier:
        raise BrainAuthError("role not enabled")
    scopes = scope_filter_for(tier, profile.get("br_id_scope"), profile.get("st_id_scope") or [])
    return BrainReader(user_id=user_id, tier=tier, scopes=scopes)
```

그리고 async `resolve_reader`는 그대로 두되, 위 `_verify_jwt`(동기 더미)를 남기지 말고 **async 경로는 `_verify_jwt_async`/`_load_app_user_async`를 사용**한다(이미 그러함). 동기 `_verify_jwt`/`_load_app_user`는 테스트 monkeypatch 표적일 뿐 실 호출 경로 아님.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/FastAPI && venv/bin/pytest tests/test_brain_auth.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/FastAPI && git add app/api/routes/brain.py tests/test_brain_auth.py && \
  git commit -m "feat(brain): require_brain_reader — JWT→tier (super_admin→MASTER), fail-closed"
```

---

### Task 7: BRAIN 라우트 3개 + main 등록 (TDD)

**Files:**
- Modify: `app/api/routes/brain.py`
- Modify: `main.py`
- Create: `tests/test_brain_routes.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_brain_routes.py`

```python
import pytest
from fastapi.testclient import TestClient

import main
from app.api.routes import brain


class _StubRPC:
    def __init__(self, rows): self._rows = rows
    def execute(self): 
        class R: data = self._rows
        return R()


@pytest.fixture
def client(monkeypatch):
    # require_brain_reader 우회 — MASTER reader 주입
    async def fake_reader(authorization=None):
        return brain.BrainReader(user_id="u", tier="ATOMOS_MASTER", scopes=None)
    main.app.dependency_overrides[brain.require_brain_reader] = fake_reader
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def _patch_rpc(monkeypatch, rows):
    class FakeClient:
        def rpc(self, name, params):
            FakeClient.last = (name, params)
            return _StubRPC(rows)
    async def fake_get_supabase():
        return FakeClient()
    monkeypatch.setattr(brain, "get_supabase", fake_get_supabase)
    return FakeClient


def test_search_returns_results(client, monkeypatch):
    _patch_rpc(monkeypatch, [{"source_path": "dept/sales/x.md", "scope": "dept:sales",
                              "read_tier": "ATOMOS_MASTER", "title": "T", "tags": ["매출"],
                              "snippet": "...", "rank": 0.5}])
    r = client.get("/api/brain/search", params={"q": "급락"})
    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["source_path"] == "dept/sales/x.md"


def test_search_passes_null_scopes_for_master(client, monkeypatch):
    fc = _patch_rpc(monkeypatch, [])
    client.get("/api/brain/search", params={"q": "x"})
    name, params = fc.last
    assert name == "atomos_knowledge_search_v2"
    assert params["p_scopes"] is None
    assert params["p_tier"] == "ATOMOS_MASTER"


def test_note_404_when_no_row(client, monkeypatch):
    _patch_rpc(monkeypatch, [])
    r = client.get("/api/brain/notes", params={"path": "dept/sales/missing.md"})
    assert r.status_code == 404


def test_scopes_returns_counts(client, monkeypatch):
    _patch_rpc(monkeypatch, [{"scope": "global", "count": 1},
                             {"scope": "dept:sales", "count": 2}])
    r = client.get("/api/brain/scopes")
    assert r.status_code == 200
    assert r.json()["scopes"][1]["scope"] == "dept:sales"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/FastAPI && venv/bin/pytest tests/test_brain_routes.py -v`
Expected: FAIL — 라우트 미정의(404 for /api/brain/search 또는 import 에러).

- [ ] **Step 3: 라우트 구현** — `app/api/routes/brain.py` 끝에 추가

```python
from fastapi import Depends


@router.get("/search")
async def brain_search(
    q: str = Query(default=""),
    scope: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    reader: BrainReader = Depends(require_brain_reader),
):
    p_scopes = reader.scopes
    if scope:  # 사용자가 특정 스코프로 좁힘 — 허용 범위와 교집합
        if p_scopes is None:
            p_scopes = [scope]
        elif scope in p_scopes:
            p_scopes = [scope]
        else:
            return {"results": []}   # 허용 밖 스코프 요청 → 빈 결과(누출 금지)
    client = await get_supabase()
    res = await client.rpc("atomos_knowledge_search_v2", {
        "p_query": q or "", "p_scopes": p_scopes, "p_tier": reader.tier, "p_limit": int(limit),
    }).execute()
    return {"results": res.data or []}


@router.get("/notes")
async def brain_note(
    path: str = Query(...),
    reader: BrainReader = Depends(require_brain_reader),
):
    client = await get_supabase()
    res = await client.rpc("atomos_knowledge_get_v2", {
        "p_source_path": path, "p_scopes": reader.scopes, "p_tier": reader.tier,
    }).execute()
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="not found")   # 403도 동일(누출 금지)
    row = rows[0]
    return {
        "source_path": row.get("source_path"), "title": row.get("title"),
        "scope": row.get("scope"), "read_tier": row.get("read_tier"),
        "read_roles": row.get("read_roles") or [], "tags": row.get("tags") or [],
        "body_md": row.get("body") or "",
        "backlinks": [], "outlinks": [],   # v2(Slice 4)에서 채움
    }


@router.get("/scopes")
async def brain_scopes(reader: BrainReader = Depends(require_brain_reader)):
    client = await get_supabase()
    res = await client.rpc("atomos_knowledge_scopes_v2", {
        "p_scopes": reader.scopes, "p_tier": reader.tier,
    }).execute()
    return {"scopes": res.data or []}
```

- [ ] **Step 4: main.py에 라우터 등록** — `main.py`

import 블록(다른 route import 근처)에 추가:
```python
from app.api.routes.brain import router as brain_router
```
`app.mount("/mcp", mcp_asgi)` 직전(다른 include_router 묶음 끝)에 추가:
```python
app.include_router(brain_router)             # /api/brain/*    — BRAIN 참조(사람 tier-aware 읽기)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd ~/FastAPI && venv/bin/pytest tests/test_brain_routes.py tests/test_brain_auth.py -v`
Expected: PASS (12 passed).

- [ ] **Step 6: 전체 회귀 (Phase 1 미파손 확인)**

Run: `cd ~/FastAPI && venv/bin/pytest -q`
Expected: 기존 테스트 전부 PASS + 신규 PASS. (007/tools.py 미수정이므로 에이전트 테스트 영향 없음.)

- [ ] **Step 7: Commit**

```bash
cd ~/FastAPI && git add app/api/routes/brain.py main.py tests/test_brain_routes.py && \
  git commit -m "feat(brain): /api/brain search·notes·scopes (tier-aware v2 RPC, 404/403 unified)"
```

---

# Slice 3 — BRAIN 참조 페이지 (hbs-dashboard)

> 결과: `/admin/brain`에서 검색·노트뷰·스코프탐색. JWT 자동 첨부.

### Task 8: Supabase JWT 요청 인터셉터 + brainApi + 타입

**Files:**
- Modify: `src/api/client.ts`
- Modify: `src/api/types.ts`
- Modify: `package.json` (react-markdown)

- [ ] **Step 1: react-markdown 설치**

Run: `cd ~/hbs-dashboard && npm install react-markdown@^9.0.1`
Expected: package.json dependencies에 `react-markdown` 추가, 설치 성공.

- [ ] **Step 2: 요청 인터셉터 추가** — `src/api/client.ts`, `http` 인스턴스 생성 직후

```typescript
import { supabase } from "../lib/supabase";

// 인증 토큰 자동 첨부 — 세션 있으면 Authorization 헤더(미인증 EP는 무시, BRAIN EP는 검증).
http.interceptors.request.use(async (config) => {
  try {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } catch {
    /* 세션 조회 실패 시 헤더 없이 진행(미인증 EP 정상 동작) */
  }
  return config;
});
```

- [ ] **Step 3: brain 타입 추가** — `src/api/types.ts` 끝에

```typescript
export interface BrainSearchResult {
  source_path: string;
  title: string;
  scope: string;
  read_tier: string;
  tags: string[];
  snippet: string;
  rank: number;
}
export interface BrainSearchResponse { results: BrainSearchResult[]; }
export interface BrainNoteDetail {
  source_path: string;
  title: string;
  scope: string;
  read_tier: string;
  read_roles: string[];
  tags: string[];
  body_md: string;
  backlinks: string[];
  outlinks: string[];
}
export interface BrainScope { scope: string; count: number; }
export interface BrainScopesResponse { scopes: BrainScope[]; }
```

- [ ] **Step 4: brainApi 추가** — `src/api/client.ts` 끝(`naverApi` 뒤)

```typescript
import type {
  BrainSearchResponse, BrainNoteDetail, BrainScopesResponse,
} from "./types";

export const brainApi = {
  search: (params: { q?: string; scope?: string; limit?: number }) =>
    http.get<BrainSearchResponse>("/api/brain/search", { params }).then((r) => r.data),
  note: (path: string) =>
    http.get<BrainNoteDetail>("/api/brain/notes", { params: { path } }).then((r) => r.data),
  scopes: () =>
    http.get<BrainScopesResponse>("/api/brain/scopes").then((r) => r.data),
};
```

- [ ] **Step 5: 빌드(타입) 확인**

Run: `cd ~/hbs-dashboard && npm run build`
Expected: `tsc -b && vite build` 성공(타입 에러 0).

- [ ] **Step 6: Commit**

```bash
cd ~/hbs-dashboard && git add src/api/client.ts src/api/types.ts package.json package-lock.json && \
  git commit -m "feat(brain): axios JWT interceptor + brainApi + types + react-markdown"
```

---

### Task 9: wikilink 파서 (TDD, 순수 유틸)

**Files:**
- Create: `src/pages/Admin/brainWikilink.ts`
- Create: `src/pages/Admin/brainWikilink.test.ts`

- [ ] **Step 1: 실패 테스트 작성** — `src/pages/Admin/brainWikilink.test.ts`

```typescript
import { describe, it, expect } from "vitest";
import { parseWikilinks } from "./brainWikilink";

describe("parseWikilinks", () => {
  it("extracts a simple [[target]]", () => {
    expect(parseWikilinks("see [[dept/sales/x]] now")).toEqual([
      { target: "dept/sales/x", label: "dept/sales/x" },
    ]);
  });
  it("supports [[target|label]]", () => {
    expect(parseWikilinks("[[a/b|읽기쉬운 라벨]]")).toEqual([
      { target: "a/b", label: "읽기쉬운 라벨" },
    ]);
  });
  it("returns [] when none", () => {
    expect(parseWikilinks("no links here")).toEqual([]);
  });
  it("finds multiple", () => {
    expect(parseWikilinks("[[a]] and [[b|B]]")).toEqual([
      { target: "a", label: "a" },
      { target: "b", label: "B" },
    ]);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd ~/hbs-dashboard && npm run test:run -- brainWikilink`
Expected: FAIL — `Cannot find module './brainWikilink'`.

- [ ] **Step 3: 구현** — `src/pages/Admin/brainWikilink.ts`

```typescript
export interface Wikilink { target: string; label: string; }

const WIKILINK_RE = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g;

/** 본문에서 [[target]] / [[target|label]] 을 추출(순수). v1에서 클릭 네비게이션에 사용. */
export function parseWikilinks(md: string): Wikilink[] {
  const out: Wikilink[] = [];
  for (const m of md.matchAll(WIKILINK_RE)) {
    const target = m[1].trim();
    out.push({ target, label: (m[2] ?? target).trim() });
  }
  return out;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd ~/hbs-dashboard && npm run test:run -- brainWikilink`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/hbs-dashboard && git add src/pages/Admin/brainWikilink.ts src/pages/Admin/brainWikilink.test.ts && \
  git commit -m "feat(brain): wikilink parser (pure, vitest)"
```

---

### Task 10: BrainReference 페이지 + 라우트 + 권한

**Files:**
- Create: `src/pages/Admin/BrainReference.tsx`
- Modify: `src/App.tsx`
- Modify: `src/auth/permissions.ts`

- [ ] **Step 1: 페이지 컴포넌트 작성** — `src/pages/Admin/BrainReference.tsx`

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { Search } from "lucide-react";
import { brainApi } from "@/api/client";

export default function BrainReference() {
  const [tab, setTab] = useState<"search" | "scopes">("search");
  const [q, setQ] = useState("");
  const [scope, setScope] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const searchQ = useQuery({
    queryKey: ["brain", "search", q, scope],
    queryFn: () => brainApi.search({ q, scope: scope ?? undefined, limit: 30 }),
    staleTime: 5 * 60_000,
  });
  const scopesQ = useQuery({
    queryKey: ["brain", "scopes"],
    queryFn: () => brainApi.scopes(),
    staleTime: 5 * 60_000,
  });
  const noteQ = useQuery({
    queryKey: ["brain", "note", selected],
    queryFn: () => brainApi.note(selected as string),
    enabled: !!selected,
  });

  const results = searchQ.data?.results ?? [];

  return (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px" }}>🧠 BRAIN 참조</h1>
      <p style={{ fontSize: 13, color: "var(--text-sub)", margin: "0 0 16px" }}>
        ATOMOS 지식 위키 — 권한 범위 내 노트를 검색·열람(서버측 권한 강제).
      </p>

      {/* 탭 바 */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "1px solid var(--border,#e5e7eb)" }}>
        {([["search", "🔍 검색"], ["scopes", "🗂 스코프"]] as const).map(([id, label]) => (
          <button key={id} type="button" onClick={() => setTab(id)}
            style={{ padding: "8px 14px", fontSize: 13, fontWeight: 700, cursor: "pointer", background: "none",
              border: "none", borderBottom: tab === id ? "2px solid #2563eb" : "2px solid transparent",
              color: tab === id ? "#2563eb" : "var(--text-sub)", marginBottom: -1 }}>
            {label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, alignItems: "start" }}>
        {/* 좌측: 검색 또는 스코프 목록 */}
        <div>
          {tab === "search" && (
            <>
              <div style={{ position: "relative", marginBottom: 12 }}>
                <Search size={16} style={{ position: "absolute", left: 10, top: 9, color: "var(--text-sub)" }} />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="노트 검색…"
                  style={{ width: "100%", padding: "8px 10px 8px 34px", borderRadius: 8,
                    border: "1px solid var(--border,#e5e7eb)", fontSize: 13, background: "var(--surface,#fff)" }} />
              </div>
              {scope && (
                <div style={{ fontSize: 12, marginBottom: 8 }}>
                  스코프: <b>{scope}</b>{" "}
                  <button onClick={() => setScope(null)} style={{ border: "none", background: "none", color: "#2563eb", cursor: "pointer" }}>해제</button>
                </div>
              )}
              {searchQ.isLoading ? <div style={{ fontSize: 13, color: "var(--text-sub)" }}>검색 중…</div>
                : results.length === 0 ? <div style={{ fontSize: 13, color: "var(--text-sub)" }}>결과 없음</div>
                : results.map((r) => (
                  <button key={r.source_path} onClick={() => setSelected(r.source_path)}
                    style={{ display: "block", width: "100%", textAlign: "left", padding: "10px 12px", marginBottom: 6,
                      borderRadius: 8, border: "1px solid var(--border,#e5e7eb)",
                      background: selected === r.source_path ? "var(--surface-muted,#f1f5f9)" : "var(--surface,#fff)", cursor: "pointer" }}>
                    <div style={{ fontWeight: 700, fontSize: 13 }}>{r.title}</div>
                    <div style={{ fontSize: 11, color: "var(--text-sub)" }}>{r.scope} · {r.read_tier}</div>
                    <div style={{ fontSize: 12, color: "var(--text-sub)", marginTop: 4 }}>{r.snippet}</div>
                  </button>
                ))}
            </>
          )}
          {tab === "scopes" && (
            <>
              {scopesQ.isLoading ? <div style={{ fontSize: 13, color: "var(--text-sub)" }}>로딩 중…</div>
                : (scopesQ.data?.scopes ?? []).map((s) => (
                  <button key={s.scope} onClick={() => { setScope(s.scope); setTab("search"); }}
                    style={{ display: "flex", justifyContent: "space-between", width: "100%", padding: "10px 12px",
                      marginBottom: 6, borderRadius: 8, border: "1px solid var(--border,#e5e7eb)",
                      background: "var(--surface,#fff)", cursor: "pointer", fontSize: 13 }}>
                    <span>{s.scope}</span><span style={{ color: "var(--text-sub)" }}>{s.count}</span>
                  </button>
                ))}
            </>
          )}
        </div>

        {/* 우측: 노트 상세 */}
        <div style={{ border: "1px solid var(--border,#e5e7eb)", borderRadius: 12, padding: 20, minHeight: 300, background: "var(--surface,#fff)" }}>
          {!selected ? <div style={{ fontSize: 13, color: "var(--text-sub)" }}>좌측에서 노트를 선택하세요.</div>
            : noteQ.isLoading ? <div style={{ fontSize: 13, color: "var(--text-sub)" }}>불러오는 중…</div>
            : noteQ.isError ? <div style={{ fontSize: 13, color: "var(--status-danger,#dc2626)" }}>열람 권한이 없거나 노트를 찾을 수 없습니다.</div>
            : noteQ.data && (
              <article>
                <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 4px" }}>{noteQ.data.title}</h2>
                <div style={{ fontSize: 11, color: "var(--text-sub)", marginBottom: 16 }}>
                  {noteQ.data.scope} · {noteQ.data.read_tier}
                  {noteQ.data.tags.length > 0 && <> · {noteQ.data.tags.join(", ")}</>}
                </div>
                <div style={{ fontSize: 14, lineHeight: 1.7 }}>
                  <ReactMarkdown>{noteQ.data.body_md}</ReactMarkdown>
                </div>
              </article>
            )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 라우트 등록** — `src/App.tsx`

import 추가(다른 Admin 페이지 import 근처):
```typescript
import BrainReference from "./pages/Admin/BrainReference";
```
`<Route path="/admin/atomos" element={<AtomosSettings />} />` 바로 다음 줄에 추가:
```tsx
<Route path="/admin/brain" element={<BrainReference />} />
```

- [ ] **Step 3: 권한 엔트리 추가** — `src/auth/permissions.ts` MENU_PERMISSIONS의 `/admin/atomos` 엔트리 다음에

```typescript
{ path: '/admin/brain', label: 'BRAIN 참조', group: '설정',
  permissions: { super_admin: 'r', brand_admin: 'none', brand_manager: 'none', sv: 'none', store_manager: 'none', staff: 'none', viewer: 'none' } },
```
(v1: super_admin만 읽기. 백엔드가 진짜 강제점이지만 메뉴/라우트 게이트도 일치시킨다.)

- [ ] **Step 4: 빌드 확인**

Run: `cd ~/hbs-dashboard && npm run build`
Expected: 타입·빌드 성공.

- [ ] **Step 5: 회귀 테스트(기존 vitest)**

Run: `cd ~/hbs-dashboard && npm run test:run`
Expected: wikilink 테스트 PASS, 기타 깨짐 없음.

- [ ] **Step 6: Commit**

```bash
cd ~/hbs-dashboard && git add src/pages/Admin/BrainReference.tsx src/App.tsx src/auth/permissions.ts && \
  git commit -m "feat(brain): /admin/brain page (search·note view·scope browse)"
```

---

### Task 11: 수동 E2E 검증 (preview)

**Files:** 없음(검증만)

- [ ] **Step 1: 백엔드 가동 + 008 적용 확인** — 로컬 또는 Railway에 008 적용, FastAPI 기동(`VITE_API_URL` 대상).
- [ ] **Step 2: 콘솔 dev 서버 + super_admin 로그인** — `npm run dev`, super_admin 계정으로 로그인.
- [ ] **Step 3: `/admin/brain` 접속** → 검색창에 "급락" → 결과(anomaly-playbook) 노출 확인.
- [ ] **Step 4: 노트 클릭** → 우측에 마크다운 본문(매출 급락 대응 플레이북) 렌더 확인.
- [ ] **Step 5: 스코프 탭** → `global`, `dept:sales` + 카운트 노출, 클릭 시 해당 스코프로 검색 좁힘 확인.
- [ ] **Step 6: 권한 음성 확인** — (가능 시) store_manager 계정으로 `/admin/brain` 접근 → 메뉴 숨김/403. 또는 토큰 없이 `/api/brain/search` 직접 호출 → 401.

> 통과선: super_admin은 전 노트 검색·열람 / 미배선 역할은 차단(서버 401·404) / 클라 필터 없이 백엔드가 결정.

---

## 범위 밖 (이 플랜 비포함 — 후속)

- **Slice 4 (v2)**: `[[wikilink]]` 링크추출 → `atomos_knowledge_links` 채움 + 백링크/아웃링크 EP·UI + pgvector 하이브리드 의미검색 + 그래프(`react-force-graph`) + 학습 seam 활성화. **별도 플랜.**
- **하위 tier 점등**: STORE_OWNER/HQ_STAFF/HQ_EXEC role→tier 매핑 + 스코프 화이트리스트(`scope_filter_for` 확장) — 실 점주 온보딩(풀 유저인증)과 함께. **별도 작업**(스펙 §6).
- **v2 학습루프 본체**: ingest 정규화·모순 플래그·query-filed-back compound·모순/stale lint — Phase 4. **별도 스펙.**
- **에이전트 경로 통합**: 007 RPC와 v2 함수 통합(`tools.py`에 `p_reader_kind` 도입) — 선택적 정리, Phase 1 안정화 후.

---

## 자기검토 (Self-Review)

**1. 스펙 커버리지:**
- ① frontmatter(read_tier/read_roles/생략→MASTER+lint) → Task 1(컬럼)·2(백필)·3(lint)·4(seed). ✅
- ② JWT→tier·API 계약(search/notes/scopes·404통일)·페이지 → Task 6·7·8·10. ✅ (graph EP는 v2 — 범위 밖 명시)
- ③ FTS+태그+스코프 v1 / 링크테이블 스키마 → Task 1·7·10. (의미검색·그래프 채움 = Slice 4) ✅
- ④ v1 ingest(GH Action)+lint / v2 seam(예약 컬럼) → Task 1(예약컬럼)·3·4·5. (v2 본체 = 범위 밖) ✅

**2. 플레이스홀더 스캔:** 모든 코드 스텝에 실제 코드·실제 명령·기대 출력 포함. "적절히 처리" 류 없음.

**3. 타입/이름 일관성:** `atomos_knowledge_search_v2`(검색)·`atomos_knowledge_get_v2`(단건)·`atomos_knowledge_scopes_v2`(스코프) — Task 1 정의 ↔ Task 7 호출 일치. `BrainReader{user_id,tier,scopes}`·`ROLE_TIER`·`scope_filter_for`·`require_brain_reader` — Task 6 정의 ↔ Task 7 사용 일치. `brainApi.{search,note,scopes}` ↔ EP 경로(`/api/brain/{search,notes,scopes}`) 일치. 응답 키(`results`/`body_md`/`scopes`) ↔ 타입 일치.

**알려진 구현 주의:** Task 6의 동기 시임(`_resolve_reader`/`_verify_jwt`/`_load_app_user`)은 **단위 테스트 진입점**이며 실 호출은 async(`resolve_reader`/`_verify_jwt_async`/`_load_app_user_async`)가 담당한다. 두 경로의 로직(스킴 검사·is_active·ROLE_TIER·scope_filter_for)은 동일하게 유지할 것 — 분기 시 한쪽만 고치지 말 것.
