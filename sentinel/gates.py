"""Deterministic gates G0-G6 — the ONLY decider in the system.

Pure functions: facts in, results out. No I/O, no network, no LLM.
A candidate passes only if every gate passes. First failure stops
evaluation (fail-fast) and the reason is recorded.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CandidateFacts:
    """All facts a gate needs, gathered by chain.py (live) or fixtures."""

    name: str
    contract: str
    chain_id: int = 56
    already_owned: bool = False
    verified: bool = False
    free_left: int = 0
    free_cap: int = 0
    total_minted: int = 0
    max_supply: int = 0
    quote_wei: int = 0
    needs_approval: bool = False
    hidden_fee: bool = False
    has_market: bool = False
    deployer_track_record: bool = False
    strong_demand: bool = False
    preview_ok: bool = False
    hostile_source: bool = False
    # Live-read provenance (set by live_facts.py, empty when offline).
    # live_error != "" means a required live read failed: the candidate
    # must SKIP, never pass on missing data.
    live_error: str = ""
    live_note: str = ""


@dataclass
class GateResult:
    gate: str
    passed: bool
    reason: str


def gate_g0_kill_switch(kill_active: bool, watchdog_expired: bool) -> GateResult:
    if kill_active:
        return GateResult("G0", False, "kill switch active (run/KILL present)")
    if watchdog_expired:
        return GateResult("G0", False, "watchdog timeout expired")
    return GateResult("G0", True, "kill switch clear")


def gate_g1_ownership(f: CandidateFacts) -> GateResult:
    if f.already_owned:
        return GateResult("G1", False, "already owned")
    return GateResult("G1", True, "not owned yet")


def gate_g2_verified(f: CandidateFacts) -> GateResult:
    if not f.verified:
        return GateResult("G2", False, "contract unverified on Sourcify")
    return GateResult("G2", True, "contract verified (exact_match)")


def gate_g3_free_phase(f: CandidateFacts) -> GateResult:
    if f.max_supply and f.total_minted >= f.max_supply:
        return GateResult(
            "G3", False, f"sold out: {f.total_minted}/{f.max_supply} minted"
        )
    if f.free_left <= 0:
        return GateResult(
            "G3", False, f"free exhausted: {f.free_left}/{f.free_cap} free left"
        )
    return GateResult("G3", True, f"free open: {f.free_left}/{f.free_cap} left")


def gate_g4_zero_cost(f: CandidateFacts) -> GateResult:
    if f.quote_wei != 0:
        return GateResult("G4", False, f"quote is not zero: {f.quote_wei} wei")
    if f.needs_approval:
        return GateResult("G4", False, "mint requires a token approval")
    if f.hidden_fee:
        return GateResult("G4", False, "hidden fee detected (platform/VRF/reveal)")
    return GateResult("G4", True, "cost is zero, no approval, no hidden fee")


def gate_g5_value_signal(f: CandidateFacts) -> GateResult:
    if f.has_market:
        return GateResult("G5", True, "value signal: live market with floor/sales")
    if f.deployer_track_record:
        return GateResult("G5", True, "value signal: deployer track record")
    if f.strong_demand:
        return GateResult("G5", True, "value signal: strong early demand")
    return GateResult("G5", False, "no value signal (no market, no track record, no demand)")


def gate_g6_preview(f: CandidateFacts) -> GateResult:
    if not f.preview_ok:
        return GateResult("G6", False, "preview reverted or not clean")
    return GateResult("G6", True, "preview clean (value 0, gas only)")


def evaluate(facts: CandidateFacts, kill_active: bool = False,
             watchdog_expired: bool = False):
    """Run gates G0-G6 fail-fast.

    Returns (decision, results). Decision is WOULD_MINT only when every
    gate passes; otherwise SKIP with the first failing gate's reason.
    A hostile source short-circuits before G0.
    """
    if facts.hostile_source:
        return "SKIP", [GateResult("FW", False, "hostile source quarantined")]
    if facts.live_error:
        # Fail-closed pre-check: a required live read failed, so no gate
        # may pass on missing data. The G0-G6 functions below are untouched.
        return "SKIP", [
            GateResult("LIVE", False, f"live read failed: {facts.live_error}")
        ]
    results = [gate_g0_kill_switch(kill_active, watchdog_expired)]
    if not results[-1].passed:
        return "SKIP", results
    checks = [
        gate_g1_ownership(facts),
        gate_g2_verified(facts),
        gate_g3_free_phase(facts),
        gate_g4_zero_cost(facts),
        gate_g5_value_signal(facts),
        gate_g6_preview(facts),
    ]
    for result in checks:
        results.append(result)
        if not result.passed:
            return "SKIP", results
    return "WOULD_MINT", results
