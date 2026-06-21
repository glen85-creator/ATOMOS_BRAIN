from scripts.lint_knowledge import lint_doc

def _doc(meta: dict, body: str = "본문") -> dict:
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

def test_scalar_read_roles_is_single_error():
    findings = lint_doc({"scope": "global", "read_tier": "HQ_STAFF",
                         "read_roles": "ANALYST", "title": "T"})
    errs = [f for f in findings if f.level == "ERROR"]
    assert len(errs) == 1 and "read_roles" in errs[0].message

def test_malformed_frontmatter_file_is_error(tmp_path, capsys):
    import scripts.lint_knowledge as lk
    bad = tmp_path / "bad.md"
    bad.write_text("---\nscope: [unclosed\n---\nbody", encoding="utf-8")
    rc = lk.main(["lint_knowledge.py", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "파싱 실패" in out


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
