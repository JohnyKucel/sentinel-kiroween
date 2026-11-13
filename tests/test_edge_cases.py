"""Edge-case tests for Fase 4 hardening (sources + live facts + chain
+ dashboard + MCP config).

Network is ALWAYS mocked here — no real Sourcify/RPC call may happen in
a unit test. The small fakes are duplicated from test_live_reads.py on
purpose so this file stays self-contained.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from sentinel.chain import BscRpc, sourcify_status
from sentinel.dashboard import make_server, render_page
from sentinel.gates import CandidateFacts, evaluate
from sentinel.live_facts import gather_live_facts
from sentinel.report import write_report
from sentinel.sources import (
    collect_candidates,
    load_static_scan_list,
    merge_candidates,
    normalize_candidate,
    parse_manual_candidate,
)
from sentinel.trace import TraceWriter

REPO = Path(__file__).resolve().parent.parent
CONTRACT = "0x1111111111111111111111111111111111111111"
CONTRACT_B = "0x2222222222222222222222222222222222222222"
WALLET = "0x3B86826245Eb2268E44bD942CFb946Aa1666D707"


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no JSON body")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, post_behaviours=None, get_behaviours=None):
        self._post = list(post_behaviours or [])
        self._get = list(get_behaviours or [])
        self.post_calls: list[str] = []
        self.get_calls: list[str] = []

    def post(self, url, json=None, timeout=None):
        self.post_calls.append(url)
        if not self._post:
            raise AssertionError("unexpected POST")
        behaviour = self._post.pop(0)
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour

    def get(self, url, params=None, timeout=None):
        self.get_calls.append(url)
        if not self._get:
            raise AssertionError("unexpected GET")
        behaviour = self._get.pop(0)
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour


def _eth_result(value: int) -> FakeResponse:
    return FakeResponse(200, {
        "jsonrpc": "2.0", "id": 1, "result": "0x" + format(value, "064x"),
    })


def _sourcify_ok(match="exact_match"):
    return FakeSession(get_behaviours=[FakeResponse(200, {"match": match})])


def _base_facts(**overrides) -> CandidateFacts:
    data = dict(
        name="Test Mint", contract=CONTRACT, verified=True, free_left=10,
        free_cap=100, total_minted=5, max_supply=100, quote_wei=0,
        has_market=True, preview_ok=True,
    )
    data.update(overrides)
    return CandidateFacts(**data)


def _mock_rpc(minted=963, supply=10000, max_supply=10000, balance=0):
    rpc = MagicMock(spec=BscRpc)
    rpc.total_minted.return_value = minted
    rpc.total_supply.return_value = supply
    rpc.max_supply.return_value = max_supply
    rpc.balance_of.return_value = balance
    return rpc


# --- sources: coercion + validation edges --------------------------------

def test_coerce_bool_string_false_is_false():
    # Regression: bool("false") is True in Python — a JSON string must be
    # parsed explicitly, or "verified": "false" would pass G2.
    cand = normalize_candidate(
        {"name": "M", "contract": CONTRACT,
         "facts": {"verified": "false", "preview_ok": "true",
                   "has_market": "TRUE", "hidden_fee": "0"}},
        "t",
    )
    assert cand is not None
    assert cand["facts"]["verified"] is False
    assert cand["facts"]["preview_ok"] is True
    assert cand["facts"]["has_market"] is True
    assert cand["facts"]["hidden_fee"] is False
    assert cand["facts"]["already_owned"] is False  # int 0 stays False


def test_normalize_keeps_free_function_and_notes_drops_unknown_keys():
    cand = normalize_candidate(
        {"name": "M", "contract": CONTRACT, "freeFunction": "mint(uint256)",
         "notes": "seen on a scan", "surprise_key": 1},
        "t",
    )
    assert cand is not None
    assert cand["freeFunction"] == "mint(uint256)"
    assert cand["notes"] == "seen on a scan"
    assert "surprise_key" not in cand


def test_normalize_chain_id_string_coerced_bad_falls_back_to_56():
    cand = normalize_candidate(
        {"name": "M", "contract": CONTRACT, "chainId": "56"}, "t"
    )
    assert cand is not None and cand["chainId"] == 56
    cand = normalize_candidate(
        {"name": "M", "contract": CONTRACT, "chainId": "bogus"}, "t"
    )
    assert cand is not None and cand["chainId"] == 56


def test_collect_candidates_non_list_file_warns_but_static_loads(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    s = tmp_path / "s.json"
    s.write_text(json.dumps([{"name": "Static", "contract": CONTRACT}]),
                 encoding="utf-8")
    cands, warnings = collect_candidates(str(f), str(s), [])
    assert [c["name"] for c in cands] == ["Static"]
    assert any("must contain a JSON list" in w for w in warnings)


def test_collect_candidates_manual_bad_spec_raises(tmp_path):
    with pytest.raises(ValueError):
        collect_candidates("", "", ["NoPipeHere"])


def test_collect_candidates_static_missing_raises(tmp_path):
    with pytest.raises(OSError):
        collect_candidates("", str(tmp_path / "missing.json"), [])


def test_load_static_scan_list_invalid_json_raises(tmp_path):
    path = tmp_path / "scan.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_static_scan_list(str(path))


def test_merge_preserves_order_first_wins():
    a = {"name": "A", "contract": CONTRACT}
    b = {"name": "B", "contract": CONTRACT_B}
    b2 = {"name": "B2", "contract": CONTRACT_B.upper()}
    c = {"name": "C", "contract": "0x3333333333333333333333333333333333333333"}
    assert [m["name"] for m in merge_candidates([a, b], [b2, c])] == ["A", "B", "C"]


def test_parse_manual_json_drops_unknown_keys():
    spec = json.dumps({
        "name": "Json Mint", "contract": CONTRACT, "surprise": 1,
        "facts": {"verified": True, "unknown_fact": 9},
    })
    cand = parse_manual_candidate(spec)
    assert "surprise" not in cand
    assert "unknown_fact" not in cand["facts"]
    assert cand["facts"]["verified"] is True


def test_parse_manual_pipe_trims_whitespace():
    cand = parse_manual_candidate(f"  Spaced Mint  |  {CONTRACT}  ")
    assert cand["name"] == "Spaced Mint"
    assert cand["contract"] == CONTRACT


def test_parse_manual_json_missing_name_raises():
    with pytest.raises(ValueError):
        parse_manual_candidate(json.dumps({"contract": CONTRACT}))


# --- live_facts: partial / wallet / zero / first-error edges -------------

def test_sourcify_partial_is_known_not_fatal():
    facts = gather_live_facts(
        _base_facts(), _mock_rpc(), sourcify_session=_sourcify_ok("partial")
    )
    assert facts.verified is False  # partial never passes G2
    assert facts.live_error == ""  # but it is a known answer, not a failure
    assert "sourcify=partial" in facts.live_note
    decision, results = evaluate(facts)
    assert decision == "SKIP"
    assert any(r.gate == "G2" and not r.passed for r in results)


def test_sourcify_match_verifies():
    facts = gather_live_facts(
        _base_facts(), _mock_rpc(), sourcify_session=_sourcify_ok("match")
    )
    assert facts.verified is True
    assert facts.live_error == ""


def test_balance_of_unreadable_fails_closed():
    facts = gather_live_facts(
        _base_facts(), _mock_rpc(balance=None), wallet=WALLET,
        sourcify_session=_sourcify_ok(),
    )
    assert "balanceOf" in facts.live_error
    decision, results = evaluate(facts)
    assert decision == "SKIP"
    assert results[0].gate == "LIVE"


def test_wallet_none_keeps_fixture_ownership():
    facts = gather_live_facts(
        _base_facts(already_owned=True), _mock_rpc(),
        sourcify_session=_sourcify_ok(),
    )
    assert facts.already_owned is True
    assert facts.live_error == ""
    decision, results = evaluate(facts)
    assert decision == "SKIP"
    assert any(r.gate == "G1" and not r.passed for r in results)


def test_total_minted_zero_is_a_real_reading_not_an_error():
    facts = gather_live_facts(
        _base_facts(), _mock_rpc(minted=0), sourcify_session=_sourcify_ok()
    )
    assert facts.total_minted == 0
    assert facts.live_error == ""
    assert "total_minted=0 via totalMinted" in facts.live_note


def test_first_error_kept_when_sourcify_and_minted_both_fail():
    down = FakeSession(get_behaviours=[requests.ConnectionError("down")])
    facts = gather_live_facts(
        _base_facts(), _mock_rpc(minted=None, supply=None),
        sourcify_session=down,
    )
    assert "sourcify" in facts.live_error
    assert "totalMinted" not in facts.live_error


# --- chain: sourcify mapping + calldata encoding edges -------------------

def test_sourcify_200_without_match_field_is_match():
    session = FakeSession(get_behaviours=[FakeResponse(200, {"abi": []})])
    assert sourcify_status(CONTRACT, 56, session=session) == "match"


def test_sourcify_200_unknown_match_value_is_match():
    session = FakeSession(get_behaviours=[FakeResponse(200, {"match": "weird"})])
    assert sourcify_status(CONTRACT, 56, session=session) == "match"


def test_eth_call_non_json_body_returns_none():
    session = FakeSession(post_behaviours=[FakeResponse(200, None)])
    rpc = BscRpc(endpoints=["https://a"], session=session)
    assert rpc.eth_call(CONTRACT, "0x1234") is None


def test_balance_of_encodes_wallet_as_padded_uint256():
    class RecordingSession(FakeSession):
        def __init__(self, result):
            super().__init__(post_behaviours=[result])
            self.seen_payload = None

        def post(self, url, json=None, timeout=None):
            self.seen_payload = json
            return super().post(url, json=json, timeout=timeout)

    session = RecordingSession(_eth_result(3))
    rpc = BscRpc(endpoints=["https://a"], session=session)
    assert rpc.balance_of(CONTRACT, WALLET) == 3
    data = session.seen_payload["params"][0]["data"]
    assert data == "0x70a08231" + format(int(WALLET, 16), "064x")


# --- dashboard: live errors, trace tail cap, query strings ---------------

def _seed_run(tmp_path, decisions, n_gate_events=0):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_report(str(run_dir), "r-edge", decisions,
                 "2026-11-10T00:00:00+00:00", aborted=False)
    trace = TraceWriter(str(run_dir / "trace.jsonl"), "r-edge")
    trace.append("RUN_START", {"candidates_file": "fixtures/candidates.json"})
    for i in range(n_gate_events):
        trace.append("GATE", {"candidate": "C", "gate": "G2",
                              "passed": True, "reason": "ok"})
    trace.append("RUN_END", {"candidates": len(decisions), "would_mint": 0,
                             "aborted": False})
    return str(run_dir)


def test_render_page_shows_live_error(tmp_path):
    run_dir = _seed_run(tmp_path, [{
        "name": "Flaky", "contract": CONTRACT, "decision": "SKIP",
        "reason": "live read failed", "live_error": "sourcify unreachable",
        "live_note": "", "gates": [], "note": "",
    }])
    page = render_page(run_dir)
    assert "live error: sourcify unreachable" in page


def test_render_page_trace_tail_capped_at_15(tmp_path):
    run_dir = _seed_run(tmp_path, [], n_gate_events=20)
    page = render_page(run_dir)
    # 22 events total (RUN_START + 20 GATE + RUN_END); tail shows last 15.
    assert "[8]" in page
    assert "[7]" not in page
    assert "run started" not in page  # seq 1, dropped from the tail


def test_render_page_escapes_live_note(tmp_path):
    run_dir = _seed_run(tmp_path, [{
        "name": "X", "contract": CONTRACT, "decision": "SKIP",
        "reason": "x", "live_error": "",
        "live_note": "sourcify=<b>exact</b>", "gates": [], "note": "",
    }])
    page = render_page(run_dir)
    assert "&lt;b&gt;" in page
    assert "<b>exact</b>" not in page


def _get(port, path):
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}{path}", timeout=5
    ) as resp:
        return resp.status, resp.read().decode("utf-8")


def test_http_status_json_empty_when_no_run(tmp_path):
    server = make_server(str(tmp_path / "empty"), "127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _get(port, "/status.json")
        assert status == 200
        assert json.loads(body) == {}
    finally:
        server.shutdown()
        server.server_close()


def test_http_root_with_query_string_still_serves(tmp_path):
    run_dir = _seed_run(tmp_path, [])
    server = make_server(run_dir, "127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _get(port, "/?refresh=1")
        assert status == 200
        assert "Sentinel" in body
    finally:
        server.shutdown()
        server.server_close()


# --- MCP config: valid, credential-free -----------------------------------

def test_mcp_config_valid_and_credential_free():
    text = (REPO / ".kiro" / "settings" / "mcp.json").read_text(encoding="utf-8")
    config = json.loads(text)
    servers = config["mcpServers"]
    assert "fetch" in servers
    assert "sequential-thinking" in servers
    for server in servers.values():
        assert server["command"] == "npx"
        assert server["args"][0] == "-y"
    lowered = text.lower()
    for secret_word in ("apikey", "api_key", "token", "password", "secret"):
        assert secret_word not in lowered


# --- live-demo fixture: pinned live pass ----------------------------------

def test_live_demo_fixture_passes_with_mocked_live_reads():
    data = json.loads(
        (REPO / "fixtures" / "live-demo.json").read_text(encoding="utf-8")
    )
    assert len(data) == 1
    cand = data[0]
    assert cand["contract"] == "0x10e46d53411f2EC60715718ce2E259182901709f"
    facts = CandidateFacts(
        name=cand["name"], contract=cand["contract"],
        free_left=cand["facts"]["free_left"],
        free_cap=cand["facts"]["free_cap"],
        quote_wei=cand["facts"]["quote_wei"],
        has_market=cand["facts"]["has_market"],
        preview_ok=cand["facts"]["preview_ok"],
    )
    rpc = _mock_rpc(minted=8822, supply=8822, max_supply=8888, balance=0)
    live = gather_live_facts(
        facts, rpc,
        wallet="0x000000000000000000000000000000000000dEaD",
        sourcify_session=_sourcify_ok("exact_match"),
    )
    assert live.live_error == ""
    decision, _ = evaluate(live)
    assert decision == "WOULD_MINT"
