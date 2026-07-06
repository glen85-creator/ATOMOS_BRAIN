"""GLEN_WORK 위키 1계층 → ATOMOS_BRAIN knowledge/global/glen/**.md 변환(시드).

입력(read-only): /mnt/d/WORK/GLEN/GLEN_WORK/wiki/{entities/**,concepts,decisions}/*.md
출력: knowledge/global/glen/{category}/{slug}.md  (source_path = global/glen/{category}/{slug})

핵심 규칙(spec 2026-07-06-glen-wiki-brain-seed-design §4):
- frontmatter: scope=global · read_tier=ATOMOS_MASTER · read_roles=[ANALYST] (전부 고정)
  · title = 본문 첫 H1 → aliases[0] → 파일명(확장자·YYYY-MM-DD- 프리픽스 제거, 한글 보존)
  · tags = GLEN_WORK tags + "glen-wiki" + "type/{gw_type}" (중복 제거·순서 보존)
- 위키링크 2패스: 먼저 원본경로→새 source_path 매핑 구축, 그 뒤 본문 [[wiki/...]] 변환.
  시드 대상이면 [[global/glen/{category}/{slug}]](라벨 보존), 아니면 대괄호 제거 텍스트로 강등.
- sources: → 본문 하단 "## 출처(원본)" 텍스트 목록(위키링크 아님).
- related: (wiki 링크) → 시드 대상이면 본문 말미 "## 관련" 위키링크, 밖이면 생략.
- README.md 제외(폴더 인덱스·frontmatter 없음).
- 멱등: knowledge/global/glen/ 전체 삭제 후 재생성.
- 파일만 생성. DB/Supabase 미접근(seed는 기존 GitHub Action이 push 시 수행).

주의: 일부 GLEN_WORK frontmatter는 엄격 YAML 파싱 실패(flow sequence에 `#`/특수문자).
      → python-frontmatter 실패 시 관대한 라인 파서로 폴백(필요 필드만 추출).
"""
import glob
import os
import re
import shutil
import sys

import yaml

# ── 경로 ──────────────────────────────────────────────────────────────
GW_WIKI = "/mnt/d/WORK/GLEN/GLEN_WORK/wiki"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_BASE = os.path.join(ROOT, "knowledge", "global", "glen")

# GLEN_WORK 서브폴더 → BRAIN category(평탄화, 1뎁스)
CATEGORY_MAP = {
    "entities/people": "entities-people",
    "entities/projects": "entities-projects",
    "entities/organizations": "entities-organizations",
    "entities/technologies": "entities-technologies",
    "concepts": "concepts",
    "decisions": "decisions",
}

H1_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
FM_SPLIT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


# ── frontmatter 로드(관대) ────────────────────────────────────────────
def _lenient_yaml_lines(fm_text: str) -> dict:
    """엄격 YAML 실패 시: 필요 필드만 라인 기반으로 추출.
    지원: 스칼라(key: val), 인라인 리스트(key: [a, b]), 블록 리스트(- item).
    """
    meta: dict = {}
    lines = fm_text.splitlines()
    i = 0
    cur_key = None
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            cur_key = key
            if val == "":
                meta[key] = []  # 블록 리스트/맵 시작 후보
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                meta[key] = [x.strip().strip("'\"") for x in _split_flow(inner)] if inner else []
                cur_key = None
            else:
                meta[key] = val.strip().strip("'\"")
                cur_key = None
        elif line.lstrip().startswith("-") and cur_key is not None:
            item = line.lstrip()[1:].strip().strip("'\"")
            if not isinstance(meta.get(cur_key), list):
                meta[cur_key] = []
            meta[cur_key].append(item)
        # 그 외(맵 하위 등) 무시 — 우리가 쓰는 필드 아님
    return meta


def _split_flow(inner: str) -> list:
    """flow 시퀀스 내부를 콤마로 분할하되 대괄호 중첩은 무시(단순용)."""
    return [p for p in inner.split(",")]


def load_doc(path: str) -> tuple:
    """(metadata dict, body str) 반환. 엄격 YAML → 실패 시 관대 파서."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    m = FM_SPLIT_RE.match(text)
    if not m:
        return {}, text.strip()
    fm_text, body = m.group(1), m.group(2)
    try:
        meta = yaml.safe_load(fm_text) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = _lenient_yaml_lines(fm_text)
    return meta, body.strip()


# ── 슬러그·제목 ───────────────────────────────────────────────────────
def slugify(name: str) -> str:
    """파일명(확장자 제거) → 안전 슬러그. 한글 보존, 소문자화 안 함.
    공백/특수문자 → '-', 연속 '-' 축약, 양끝 '-' 제거.
    """
    base = os.path.splitext(name)[0]
    # 경로 구분자 안전(윈도 백슬래시 포함)만 치환, 한글·영숫자·._- 유지
    out = re.sub(r"[\\/:*?\"<>|#\[\]\s]+", "-", base)
    out = re.sub(r"-{2,}", "-", out).strip("-")
    return out or "untitled"


def strip_date_prefix(name: str) -> str:
    base = os.path.splitext(name)[0]
    return DATE_PREFIX_RE.sub("", base)


def derive_title(body: str, meta: dict, filename: str) -> str:
    h1 = H1_RE.search(body or "")
    if h1:
        return h1.group(1).strip()
    aliases = meta.get("aliases")
    if isinstance(aliases, list) and aliases:
        first = str(aliases[0]).strip()
        if first:
            return first
    elif isinstance(aliases, str) and aliases.strip():
        return aliases.strip()
    return strip_date_prefix(filename)


# ── 링크 변환 ─────────────────────────────────────────────────────────
def normalize_ref(ref: str) -> str:
    """[[wiki/concepts/ATOMOS]] / [[wiki/concepts/ATOMOS.md]] → 'concepts/ATOMOS' 형태 상대키.
    'wiki/' 프리픽스 제거·'.md' 제거. raw/summaries 등 non-wiki는 그대로(미시드 판정용).
    """
    r = ref.strip()
    if r.endswith(".md"):
        r = r[:-3]
    if r.startswith("wiki/"):
        r = r[len("wiki/"):]
    return r


def gw_relkey_to_category_slug(relkey: str) -> tuple:
    """'entities/projects/HBS Dashboard' → ('entities/projects', 'HBS Dashboard').
    concepts/decisions는 2세그먼트. 매칭 안 되면 (None, None).
    """
    parts = relkey.split("/")
    if len(parts) >= 3 and parts[0] == "entities":
        sub = "/".join(parts[:2])
        rest = "/".join(parts[2:])
        return sub, rest
    if len(parts) >= 2 and parts[0] in ("concepts", "decisions"):
        return parts[0], "/".join(parts[1:])
    return None, None


def convert_body_links(body: str, ref_to_source: dict) -> tuple:
    """본문 [[...]] 2패스 변환. ref_to_source: normalize_ref 결과 → new source_path.
    반환 (new_body, unresolved_count).
    """
    unresolved = 0

    def repl(m):
        nonlocal unresolved
        target, label = m.group(1).strip(), m.group(2)
        key = normalize_ref(target)
        new_sp = ref_to_source.get(key)
        if new_sp:
            if label:
                return f"[[{new_sp}|{label.strip()}]]"
            return f"[[{new_sp}]]"
        # 미시드 → 대괄호 제거, 라벨(있으면) 또는 원 타겟의 마지막 세그먼트로 텍스트 강등
        unresolved += 1
        if label:
            return label.strip()
        return key.split("/")[-1]

    return WIKILINK_RE.sub(repl, body or ""), unresolved


def as_text(value) -> str:
    """sources 항목을 텍스트로. [[...]] 위키링크면 라벨/마지막세그먼트로 벗김."""
    s = str(value).strip()
    m = WIKILINK_RE.fullmatch(s)
    if m:
        target, label = m.group(1).strip(), m.group(2)
        return (label.strip() if label else target)
    return s


# ── 출력 파일 조립 ────────────────────────────────────────────────────
def yaml_list(items: list) -> str:
    """['a','b'] → '[a, b]' (스칼라 안전: 특수문자 포함 시 따옴표)."""
    def q(x):
        s = str(x)
        if re.search(r"[\[\]{}:,&*#?|<>=!%@`\"']", s) or s.strip() != s:
            return '"' + s.replace('"', '\\"') + '"'
        return s
    return "[" + ", ".join(q(x) for x in items) + "]"


def yaml_scalar(s: str) -> str:
    s = str(s)
    if re.search(r"[:\[\]{}#&*!|>'\"%@`]", s) or s.strip() != s or s == "":
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def build_output(meta: dict, body: str, title: str,
                 ref_to_source: dict) -> tuple:
    gw_type = meta.get("type")
    # tags: gw tags + glen-wiki + type/{gw_type}
    gw_tags = meta.get("tags")
    if isinstance(gw_tags, str):
        gw_tags = [gw_tags]
    elif not isinstance(gw_tags, list):
        gw_tags = []
    tags = [str(t).strip() for t in gw_tags if str(t).strip()]
    tags.append("glen-wiki")
    if gw_type:
        tags.append(f"type/{gw_type}")
    seen, dedup = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            dedup.append(t)

    new_body, unresolved = convert_body_links(body, ref_to_source)

    # related: 시드 대상만 위키링크로
    related = meta.get("related") or []
    if isinstance(related, str):
        related = [related]
    related_links = []
    for r in related:
        key = normalize_ref(str(r).lstrip("[").rstrip("]"))
        # r이 이미 [[...]] 문자열일 수 있으니 안쪽 추출
        m = WIKILINK_RE.fullmatch(str(r).strip())
        if m:
            key = normalize_ref(m.group(1).strip())
        new_sp = ref_to_source.get(key)
        if new_sp:
            related_links.append(new_sp)
    # 중복 제거
    related_links = list(dict.fromkeys(related_links))

    # sources: → 출처(원본) 텍스트
    sources = meta.get("sources") or []
    if isinstance(sources, str):
        sources = [sources]
    source_texts = [as_text(s) for s in sources if str(s).strip()]

    parts = [new_body.rstrip()]
    if related_links:
        parts.append("")
        parts.append("## 관련")
        parts.append("")
        for sp in related_links:
            parts.append(f"- [[{sp}]]")
    if source_texts:
        parts.append("")
        parts.append("## 출처(원본)")
        parts.append("")
        for st in source_texts:
            parts.append(f"- {st}")
    body_out = "\n".join(parts).rstrip() + "\n"

    fm = [
        "---",
        "scope: global",
        "read_tier: ATOMOS_MASTER",
        "read_roles: [ANALYST]",
        f"title: {yaml_scalar(title)}",
        f"tags: {yaml_list(dedup)}",
        "---",
        "",
    ]
    return "\n".join(fm) + body_out, unresolved


# ── 메인 ──────────────────────────────────────────────────────────────
def collect_inputs() -> list:
    """[(gw_path, gw_subdir, category, filename, slug, relkey)] — README 제외."""
    out = []
    for sub, category in CATEGORY_MAP.items():
        for path in sorted(glob.glob(os.path.join(GW_WIKI, sub, "*.md"))):
            fn = os.path.basename(path)
            if fn.lower() == "readme.md":
                continue
            slug = slugify(fn)
            relkey = f"{sub}/{os.path.splitext(fn)[0]}"  # 위키링크 매칭용(원 파일명)
            out.append((path, sub, category, fn, slug, relkey))
    return out


def main() -> int:
    inputs = collect_inputs()
    if not inputs:
        print("ERROR: 입력 없음 — GW_WIKI 경로 확인:", GW_WIKI)
        return 1

    # 1패스: 원본 relkey → 새 source_path 매핑
    ref_to_source = {}
    for _p, _sub, category, _fn, slug, relkey in inputs:
        source_path = f"global/glen/{category}/{slug}"
        ref_to_source[relkey] = source_path

    # 멱등: knowledge/global/glen/ 전체 재생성
    if os.path.isdir(OUT_BASE):
        shutil.rmtree(OUT_BASE)
    os.makedirs(OUT_BASE, exist_ok=True)

    per_cat = {}
    total_unresolved = 0
    written = 0
    for path, _sub, category, fn, slug, _relkey in inputs:
        meta, body = load_doc(path)
        title = derive_title(body, meta, fn)
        content, unresolved = build_output(meta, body, title, ref_to_source)
        total_unresolved += unresolved

        out_dir = os.path.join(OUT_BASE, category)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, slug + ".md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        written += 1
        per_cat[category] = per_cat.get(category, 0) + 1

    print("── GLEN_WORK 시드 완료 ──")
    for cat in sorted(per_cat):
        print(f"  {cat}: {per_cat[cat]}")
    print(f"  합계: {written} 파일")
    print(f"  미해소(강등) 위키링크: {total_unresolved}")
    print(f"  출력: {OUT_BASE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
