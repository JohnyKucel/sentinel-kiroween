"""Unit tests for the deterministic gates G0-G6."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel.gates import CandidateFacts, evaluate  # noqa: E402


def _clean(**overrides):
    facts = dict(
        name="Test",
        contract="0x0000000000000000000000000000000000000001",
        verified=True,
        free_left=10,
        free_cap=100,
        total_minted=90,
        max_supply=1000,
        quote_wei=0,
        preview_ok=True,
        has_market=True,
    )
    facts.update(overrides)
    return CandidateFacts(**facts)


def test_all_pass_would_mint():
    decision, results = evaluate(_clean())
    assert decision == "WOULD_MINT"
    assert all(r.passed for r in results)


def test_kill_switch_fails_first():
    decision, results = evaluate(_clean(), kill_active=True)
    assert decision == "SKIP"
    assert results[0].gate == "G0" and not results[0].passed


def test_watchdog_expired_fails_g0():
    decision, results = evaluate(_clean(), watchdog_expired=True)
    assert decision == "SKIP"
    assert results[0].gate == "G0"


def test_already_owned_g1():
    decision, results = evaluate(_clean(already_owned=True))
    assert decision == "SKIP"
    assert results[-1].gate == "G1"


def test_unverified_g2():
    decision, results = evaluate(_clean(verified=False))
    assert decision == "SKIP"
    assert results[-1].gate == "G2"


def test_sold_out_g3():
    decision, results = evaluate(_clean(total_minted=1000, max_supply=1000))
    assert decision == "SKIP"
    assert results[-1].gate == "G3"


def test_free_exhausted_g3():
    decision, results = evaluate(_clean(free_left=0))
    assert decision == "SKIP"
    assert results[-1].gate == "G3"


def test_nonzero_quote_g4():
    decision, results = evaluate(_clean(quote_wei=1000))
    assert decision == "SKIP"
    assert results[-1].gate == "G4"


def test_approval_required_g4():
    decision, results = evaluate(_clean(needs_approval=True))
    assert decision == "SKIP"
    assert results[-1].gate == "G4"


def test_hidden_fee_g4():
    decision, results = evaluate(_clean(hidden_fee=True))
    assert decision == "SKIP"
    assert results[-1].gate == "G4"


def test_no_value_signal_g5():
    decision, results = evaluate(_clean(has_market=False))
    assert decision == "SKIP"
    assert results[-1].gate == "G5"


def test_value_signal_via_demand():
    decision, _ = evaluate(_clean(has_market=False, strong_demand=True))
    assert decision == "WOULD_MINT"


def test_preview_revert_g6():
    decision, results = evaluate(_clean(preview_ok=False))
    assert decision == "SKIP"
    assert results[-1].gate == "G6"


def test_hostile_source_short_circuits():
    decision, results = evaluate(_clean(hostile_source=True))
    assert decision == "SKIP"
    assert results[0].gate == "FW"


def test_fail_fast_stops_at_first_failure():
    # Unverified AND sold out: only G2 should appear after G0/G1.
    decision, results = evaluate(_clean(verified=False, total_minted=1000,
                                        max_supply=1000))
    assert decision == "SKIP"
    assert [r.gate for r in results] == ["G0", "G1", "G2"]
