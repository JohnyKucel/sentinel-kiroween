"""Merge live chain reads into gate facts (fail-closed).

Live reads only supply INPUT to the deterministic gates G0-G6; no gate
logic lives here. Any required live read that fails sets live_error,
which makes evaluate() SKIP the candidate — a failed read can never
pass a gate by accident.

Reads that are contract-specific (free_left, free_cap, quote, approval,
hidden fee, market, demand, preview) stay on the candidate's own
facts: there is no generic on-chain way to read them without the
contract ABI. Only the generic reads are overridden live:
Sourcify verification, totalMinted (totalSupply as fallback proxy),
MAX_SUPPLY/maxSupply, and balanceOf when a wallet is given.
"""

from __future__ import annotations

from dataclasses import replace

from .chain import BscRpc, sourcify_status
from .gates import CandidateFacts


def gather_live_facts(
    facts: CandidateFacts,
    rpc: BscRpc,
    wallet: str | None = None,
    sourcify_session=None,
) -> CandidateFacts:
    """Override fixture facts with live Sourcify + BSC RPC reads."""
    notes: list[str] = []
    error = ""

    # G2 input: Sourcify verification. "unknown" (network error, odd
    # status) is a failed read, not a pass.
    status = sourcify_status(facts.contract, facts.chain_id, session=sourcify_session)
    if status == "unknown":
        error = f"sourcify unreachable for {facts.contract}"
        verified = False
    else:
        verified = status in ("exact_match", "match")
        notes.append(f"sourcify={status}")

    # G3 input: total minted. totalMinted() first; totalSupply() only as
    # a fallback proxy (burns can make it undercount mints — recorded
    # in the note so the trace stays honest).
    total_minted = rpc.total_minted(facts.contract)
    minted_via = "totalMinted"
    if total_minted is None:
        total_minted = rpc.total_supply(facts.contract)
        minted_via = "totalSupply(proxy)"
    if total_minted is None:
        if not error:
            error = f"totalMinted/totalSupply unreadable for {facts.contract}"
    else:
        notes.append(f"total_minted={total_minted} via {minted_via}")

    # G3 input: supply cap. Many contracts have no cap getter at all, so
    # an unreadable cap is NOT a read failure — it stays 0, which the
    # G3 sold-out check already tolerates.
    max_supply = rpc.max_supply(facts.contract)
    if max_supply is None:
        max_supply = 0
        notes.append("max_supply unknown (no MAX_SUPPLY/maxSupply)")
    else:
        notes.append(f"max_supply={max_supply}")

    # G1 input: ownership, only when a wallet is given.
    already_owned = facts.already_owned
    if wallet:
        balance = rpc.balance_of(facts.contract, wallet)
        if balance is None:
            if not error:
                error = f"balanceOf unreadable for {facts.contract}"
        else:
            already_owned = balance > 0
            notes.append(f"balanceOf({wallet[:8]}...)={balance}")

    return replace(
        facts,
        verified=verified,
        total_minted=total_minted or 0,
        max_supply=max_supply,
        already_owned=already_owned,
        live_error=error,
        live_note="; ".join(notes),
    )
