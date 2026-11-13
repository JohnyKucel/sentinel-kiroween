"""Tests for sentinel.sources — static scan list + manual input."""

import json

import pytest

from sentinel.sources import (
    blank_facts,
    collect_candidates,
    is_valid_address,
    load_static_scan_list,
    merge_candidates,
    normalize_candidate,
    parse_manual_candidate,
)

ADDR_A = "0x1111111111111111111111111111111111111111"
ADDR_B = "0x2222222222222222222222222222222222222222"


def test_is_valid_address():
    assert is_valid_address(ADDR_A)
    assert is_valid_address("0x" + "aB" * 20)
    assert not is_valid_address("0x1234")  # too short
    assert not is_valid_address("1111111111111111111111111111111111111111")
    assert not is_valid_address("0x" + "g" * 40)  # not hex
    assert not is_valid_address(None)
    assert not is_valid_address(123)


def test_blank_facts_fail_closed():
    facts = blank_facts()
    assert facts["verified"] is False
    assert facts["free_left"] == 0
    assert facts["preview_ok"] is False
    # mutating one copy must not leak into the next
    facts["verified"] = True
    assert blank_facts()["verified"] is False


def test_normalize_candidate_fills_defaults():
    cand = normalize_candidate(
        {"name": "  Some Mint ", "contract": ADDR_A}, "test"
    )
    assert cand is not None
    assert cand["name"] == "Some Mint"
    assert cand["chainId"] == 56
    assert cand["facts"] == blank_facts()
    assert cand["sources"] == ["test"]


def test_normalize_candidate_rejects_bad_entries():
    assert normalize_candidate({"name": "x", "contract": "0x1234"}, "t") is None
    assert normalize_candidate({"name": "  ", "contract": ADDR_A}, "t") is None
    assert normalize_candidate({"contract": ADDR_A}, "t") is None
    assert normalize_candidate("not a dict", "t") is None
    assert normalize_candidate(None, "t") is None


def test_normalize_candidate_coerces_facts():
    cand = normalize_candidate(
        {"name": "M", "contract": ADDR_A,
         "facts": {"verified": 1, "free_left": "37", "unknown_key": 9}},
        "t",
    )
    assert cand is not None
    assert cand["facts"]["verified"] is True
    assert cand["facts"]["free_left"] == 37
    assert "unknown_key" not in cand["facts"]


def test_parse_manual_pipe_form():
    cand = parse_manual_candidate(f"Manual Mint|{ADDR_A}")
    assert cand["name"] == "Manual Mint"
    assert cand["contract"] == ADDR_A
    assert cand["chainId"] == 56
    assert cand["facts"] == blank_facts()
    assert cand["sources"] == ["manual"]


def test_parse_manual_pipe_form_with_chain():
    cand = parse_manual_candidate(f"Mint|{ADDR_A}|1")
    assert cand["chainId"] == 1


def test_parse_manual_json_form():
    spec = json.dumps({
        "name": "Json Mint", "contract": ADDR_B,
        "facts": {"verified": True, "free_left": 5},
    })
    cand = parse_manual_candidate(spec)
    assert cand["name"] == "Json Mint"
    assert cand["facts"]["verified"] is True
    assert cand["facts"]["free_left"] == 5
    assert cand["facts"]["preview_ok"] is False


def test_parse_manual_rejects_bad_input():
    with pytest.raises(ValueError):
        parse_manual_candidate("")
    with pytest.raises(ValueError):
        parse_manual_candidate("NoPipeHere")
    with pytest.raises(ValueError):
        parse_manual_candidate(f"Bad|0x1234")
    with pytest.raises(ValueError):
        parse_manual_candidate("{not json")
    with pytest.raises(ValueError):
        parse_manual_candidate(f"Name|{ADDR_A}|notanint")


def test_load_static_scan_list(tmp_path):
    path = tmp_path / "scan.json"
    path.write_text(json.dumps([
        {"name": "Good", "contract": ADDR_A},
        {"name": "Bad", "contract": "0x1234"},
        "junk",
        {"name": "Also Good", "contract": ADDR_B},
    ]), encoding="utf-8")
    cands, warnings = load_static_scan_list(str(path))
    assert [c["name"] for c in cands] == ["Good", "Also Good"]
    assert len(warnings) == 2
    assert all("static-list" in c["sources"] for c in cands)


def test_load_static_scan_list_rejects_non_list(tmp_path):
    path = tmp_path / "scan.json"
    path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    cands, warnings = load_static_scan_list(str(path))
    assert cands == []
    assert len(warnings) == 1


def test_load_static_scan_list_missing_file(tmp_path):
    with pytest.raises(OSError):
        load_static_scan_list(str(tmp_path / "nope.json"))


def test_merge_candidates_dedupes_case_insensitive():
    a = {"name": "A", "contract": ADDR_A}
    b = {"name": "B", "contract": ADDR_A.upper()}
    c = {"name": "C", "contract": ADDR_B}
    merged = merge_candidates([a], [b, c])
    assert [m["name"] for m in merged] == ["A", "C"]


def test_collect_candidates_merges_all_sources(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps(
        [{"name": "File", "contract": ADDR_A}]
    ), encoding="utf-8")
    s = tmp_path / "s.json"
    s.write_text(json.dumps(
        [{"name": "Static", "contract": ADDR_B}]
    ), encoding="utf-8")
    cands, warnings = collect_candidates(
        str(f), str(s), ["Manual|0x3333333333333333333333333333333333333333"]
    )
    assert [c["name"] for c in cands] == ["File", "Static", "Manual"]
    assert warnings == []


def test_collect_candidates_file_missing_but_manual_ok(tmp_path):
    cands, warnings = collect_candidates(
        str(tmp_path / "missing.json"), "",
        [f"Manual|{ADDR_A}"],
    )
    assert [c["name"] for c in cands] == ["Manual"]
    assert len(warnings) == 1


def test_collect_candidates_nothing_raises():
    with pytest.raises(ValueError):
        collect_candidates("", "", [])
