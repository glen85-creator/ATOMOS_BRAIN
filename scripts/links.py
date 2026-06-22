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
