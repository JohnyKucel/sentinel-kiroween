"""Unit tests for the live-read layer (chain.py + live_facts.py + CLI flag).

Network is ALWAYS mocked here — no real Sourcify/RPC call may happen in
a unit test. Fakes implement the tiny requests surface the code uses
(Session.post / Session.get returning objects with .status_code,
.json(), .raise_for_status()).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from sentinel import cli as cli_mod
from sentinel.chain import BscRpc, is_verified, sourcify_status
from sentinel.gates import CandidateFacts, evaluate
from sentinel.live_facts import gather_live_facts

REPO = Path(__file__).resolve().parent.parent
CONTRACT = "0x1111111111111111111111111111111111111111"
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
    """Scripted session: post/get behaviours consumed in call order."""

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


def _base_facts(**overrides) -> CandidateFacts:
    data = dict(
        name="Test Mint", contract=CONTRACT, verified=True, free_left=10,
        free_cap=100, total_minted=5, max_supply=100, quote_wei=0,
        has_market=True, preview_ok=True,
    )
    data.update(overrides)
    return CandidateFacts(**data)


# --- BscRpc: retry + decoding -------------------------------------------

def test_eth_call_retries_next_endpoint():
    session = FakeSession(post_behaviours=[
        requests.ConnectionError("rpc-a down"),
        _eth_result(7),
    ])
    rpc = BscRpc(
        endpoints=["https://rpc-a.example", "https://rpc-b.example"],
        session=session,
    )
    assert rpc.eth_call(CONTRACT, "0x1234") == "0x" + format(7, "064x")
    assert session.post_calls == ["https://rpc-a.example", "https://rpc-b.example"]


def test_eth_call_all_endpoints_fail_returns_none():
    session = FakeSession(post_behaviours=[
        requests.ConnectionError("down"),
        requests.Timeout("slow"),
    ])
    rpc = BscRpc(endpoints=["https://a", "https://b"], session=session)
    assert rpc.eth_call(CONTRACT, "0x1234") is None


def test_eth_call_rpc_error_object_returns_none_without_retry():
    session = FakeSession(post_behaviours=[
        FakeResponse(200, {"error": {"code": -32000, "message": "revert"}}),
    ])
    rpc = BscRpc(endpoints=["https://a", "https://b"], session=session)
    assert rpc.eth_call(CONTRACT, "0x1234") is None
    assert len(session.post_calls) == 1  # per-contract revert, not endpoint failure


def test_call_view_decodes_uint256_and_rejects_garbage():
    session = FakeSession(post_behaviours=[
        _eth_result(42),
        FakeResponse(200, {"result": "0x"}),
        FakeResponse(200, {"result": "0x1234"}),
    ])
    rpc = BscRpc(endpoints=["https://a"], session=session)
    assert rpc.call_view(CONTRACT, "18160ddd") == 42
    assert rpc.call_view(CONTRACT, "18160ddd") is None
    assert rpc.call_view(CONTRACT, "18160ddd") is None


def test_call_view_rejects_bad_address():
    rpc = BscRpc(endpoints=["https://a"], session=FakeSession())
    assert rpc.call_view("0x123", "18160ddd") is None
    assert rpc.balance_of(CONTRACT, "not-an-address") is None


# --- Sourcify ------------------------------------------------------------

@pytest.mark.parametrize("status_code,payload,expected", [
    (200, {"match": "exact_match"}, "exact_match"),
    (200, {"match": "match"}, "match"),
    (200, {"match": "partial"}, "partial"),
    (404, None, "unverified"),
    (500, None, "unknown"),
])
def test_sourcify_status_mapping(status_code, payload, expected):
    session = FakeSession(get_behaviours=[FakeResponse(status_code, payload)])
    assert sourcify_status(CONTRACT, 56, session=session) == expected


def test_sourcify_status_exception_is_unknown():
    session = FakeSession(get_behaviours=[requests.ConnectionError("down")])
    assert sourcify_status(CONTRACT, 56, session=session) == "unknown"


def test_sourcify_status_uses_abi_fields_not_stdjson():
    session = FakeSession(get_behaviours=[
        FakeResponse(200, {"match": "exact_match"}),
    ])
    sourcify_status(CONTRACT, 56, session=session)
    # The call must not have raised; fields are passed as params — the
    # fake ignores them, so assert via a recording session instead.
    seen: dict = {}

    class RecordingSession(FakeSession):
        def get(self, url, params=None, timeout=None):
            seen["params"] = params
            return super().get(url, params=params, timeout=timeout)

    rec = RecordingSession(get_behaviours=[
        FakeResponse(200, {"match": "exact_match"}),
    ])
    sourcify_status(CONTRACT, 56, session=rec)
    assert seen["params"] == {"fields": "abi"}


def test_is_verified_accepts_exact_and_match_only():
    exact = FakeSession(get_behaviours=[FakeResponse(200, {"match": "exact_match"})])
    assert is_verified(CONTRACT, 56, session=exact) is True
    partial = FakeSession(get_behaviours=[FakeResponse(200, {"match": "partial"})])
    assert is_verified(CONTRACT, 56, session=partial) is False
    missing = FakeSession(get_behaviours=[FakeResponse(404, None)])
    assert is_verified(CONTRACT, 56, session=missing) is False


# --- gather_live_facts ---------------------------------------------------

def _mock_rpc(minted=963, supply=10000, max_supply=10000, balance=0):
    rpc = MagicMock(spec=BscRpc)
    rpc.total_minted.return_value = minted
    rpc.total_supply.return_value = supply
    rpc.max_supply.return_value = max_supply
    rpc.balance_of.return_value = balance
    return rpc


def _sourcify_ok():
    return FakeSession(get_behaviours=[
        FakeResponse(200, {"match": "exact_match"}),
    ])


def test_gather_live_facts_happy_path():
    facts = gather_live_facts(
        _base_facts(verified=False, total_minted=0, max_supply=0),
        _mock_rpc(), sourcify_session=_sourcify_ok(),
    )
    assert facts.verified is True
    assert facts.total_minted == 963
    assert facts.max_supply == 10000
    assert facts.already_owned is False
    assert facts.live_error == ""
    assert "sourcify=exact_match" in facts.live_note


def test_gather_live_facts_sourcify_unknown_fails_closed():
    down = FakeSession(get_behaviours=[requests.ConnectionError("down")])
    facts = gather_live_facts(_base_facts(), _mock_rpc(), sourcify_session=down)
    assert facts.live_error != ""
    assert "sourcify" in facts.live_error
    decision, results = evaluate(facts)
    assert decision == "SKIP"
    assert results[0].gate == "LIVE"
    assert results[0].passed is False


def test_gather_live_facts_minted_falls_back_to_supply():
    rpc = _mock_rpc(minted=None, supply=500)
    facts = gather_live_facts(_base_facts(), rpc, sourcify_session=_sourcify_ok())
    assert facts.total_minted == 500
    assert "totalSupply(proxy)" in facts.live_note
    assert facts.live_error == ""


def test_gather_live_facts_both_minted_reads_fail():
    rpc = _mock_rpc(minted=None, supply=None)
    facts = gather_live_facts(_base_facts(), rpc, sourcify_session=_sourcify_ok())
    assert facts.live_error != ""
    assert "totalMinted" in facts.live_error
    decision, _ = evaluate(facts)
    assert decision == "SKIP"


def test_gather_live_facts_wallet_ownership():
    owned = gather_live_facts(
        _base_facts(), _mock_rpc(balance=2), wallet=WALLET,
        sourcify_session=_sourcify_ok(),
    )
    assert owned.already_owned is True
    free = gather_live_facts(
        _base_facts(), _mock_rpc(balance=0), wallet=WALLET,
        sourcify_session=_sourcify_ok(),
    )
    assert free.already_owned is False


def test_gather_live_facts_max_supply_unknown_is_not_fatal():
    rpc = _mock_rpc(max_supply=None)
    facts = gather_live_facts(_base_facts(), rpc, sourcify_session=_sourcify_ok())
    assert facts.max_supply == 0
    assert facts.live_error == ""


def test_evaluate_live_error_skips_before_gates():
    facts = _base_facts(live_error="sourcify unreachable for 0x1111")
    decision, results = evaluate(facts)
    assert decision == "SKIP"
    assert len(results) == 1 and results[0].gate == "LIVE"


# --- CLI wiring ----------------------------------------------------------

def test_cli_run_live_reads_flag_wires_gather(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    run_dir = tmp_path / "run"
    monkeypatch.setattr(cli_mod, "RUN_DIR", str(run_dir))

    stub_rpc = MagicMock(spec=BscRpc)
    stub_rpc.total_minted.return_value = None
    stub_rpc.total_supply.return_value = None
    stub_rpc.max_supply.return_value = None
    stub_rpc.balance_of.return_value = None
    monkeypatch.setattr(cli_mod, "BscRpc", lambda: stub_rpc)
    monkeypatch.setattr(
        "sentinel.live_facts.sourcify_status",
        lambda *args, **kwargs: "unknown",
    )

    args = argparse.Namespace(
        candidates=str(REPO / "fixtures" / "candidates.json"),
        live_reads=True, live=False, wallet="", approval_token="",
        max_seconds=60,
    )
    assert cli_mod.cmd_run(args) == 0
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    assert status["candidates"] == 5
    assert status["would_mint"] == 0
    assert all(d["live_error"] != "" for d in status["decisions"])
    trace = (run_dir / "trace.jsonl").read_text(encoding="utf-8")
    assert trace.count('"LIVE_FACTS"') == 5


def test_cli_run_twice_trace_stays_valid(tmp_path, monkeypatch):
    """Regression: re-running in the same run/ dir used to append a
    second seq-1..N block to trace.jsonl, breaking verify_trace."""
    from sentinel.trace import verify_trace

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    run_dir = tmp_path / "run"
    monkeypatch.setattr(cli_mod, "RUN_DIR", str(run_dir))
    args = argparse.Namespace(
        candidates=str(REPO / "fixtures" / "candidates.json"),
        live_reads=False, live=False, wallet="", approval_token="",
        max_seconds=60,
    )
    assert cli_mod.cmd_run(args) == 0
    assert cli_mod.cmd_run(args) == 0
    ok, errors = verify_trace(str(run_dir / "trace.jsonl"))
    assert ok, errors
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    assert (status["candidates"], status["would_mint"]) == (5, 1)
