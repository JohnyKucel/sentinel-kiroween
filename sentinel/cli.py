"""Sentinel CLI: run / status / stop / trap-test / verify-trace / dashboard.

Default mode is dry-run: real read-only verification, simulated mint, no
transaction, no wallet connection. Live execution is refused unless every
authorisation check in executor.py passes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

from . import advisor, killswitch
from .chain import BscRpc
from .dashboard import serve
from .executor import LiveRefused, execute_live
from .firewall import quarantine, screen
from .gates import CandidateFacts, evaluate
from .live_facts import gather_live_facts
from .report import read_status, write_report
from .sources import collect_candidates
from .trace import TraceWriter, verify_trace

RUN_DIR = "run"
MAX_RUNTIME_SECONDS = 600


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _facts_from_candidate(cand: dict) -> CandidateFacts:
    facts = cand.get("facts", {})
    return CandidateFacts(
        name=cand.get("name", "unnamed"),
        contract=cand.get("contract", ""),
        chain_id=int(cand.get("chainId", 56)),
        already_owned=bool(facts.get("already_owned", False)),
        verified=bool(facts.get("verified", False)),
        free_left=int(facts.get("free_left", 0)),
        free_cap=int(facts.get("free_cap", 0)),
        total_minted=int(facts.get("total_minted", 0)),
        max_supply=int(facts.get("max_supply", 0)),
        quote_wei=int(facts.get("quote_wei", 0)),
        needs_approval=bool(facts.get("needs_approval", False)),
        hidden_fee=bool(facts.get("hidden_fee", False)),
        has_market=bool(facts.get("has_market", False)),
        deployer_track_record=bool(facts.get("deployer_track_record", False)),
        strong_demand=bool(facts.get("strong_demand", False)),
        preview_ok=bool(facts.get("preview_ok", False)),
        hostile_source=bool(facts.get("hostile_source", False)),
    )


def cmd_run(args) -> int:
    run_id = f"r-{uuid.uuid4().hex[:8]}"
    started = _now_iso()
    os.makedirs(RUN_DIR, exist_ok=True)
    killswitch.disarm(RUN_DIR)
    # Fresh trace per run: report.md/status.json are already overwritten
    # per run, so a stale trace would orphan old records and break the
    # sequence check in verify_trace() (TraceWriter restarts seq at 1).
    trace_path = os.path.join(RUN_DIR, "trace.jsonl")
    if os.path.exists(trace_path):
        os.remove(trace_path)
    trace = TraceWriter(trace_path, run_id)
    trace.append("RUN_START", {
        "candidates_file": args.candidates,
        "live": args.live,
        "live_reads": bool(args.live_reads),
    })
    watchdog = killswitch.Watchdog(args.max_seconds)
    rpc = BscRpc() if args.live_reads else None

    try:
        candidates, source_warnings = collect_candidates(
            args.candidates,
            getattr(args, "static_list", "") or "",
            getattr(args, "manual", None) or [],
        )
    except (OSError, ValueError) as exc:
        print(f"error: cannot load candidates: {exc}", file=sys.stderr)
        return 2
    for warning in source_warnings:
        print(f"warning: {warning}", file=sys.stderr)
    trace.append("SOURCES", {
        "file": args.candidates,
        "static_list": getattr(args, "static_list", "") or "",
        "manual": len(getattr(args, "manual", None) or []),
        "candidates": len(candidates),
        "warnings": len(source_warnings),
    })

    decisions = []
    for cand in candidates:
        if killswitch.is_active(RUN_DIR) or watchdog.expired:
            trace.append("ABORTED", {"reason": "kill switch or watchdog"})
            break
        name = cand.get("name", "unnamed")
        # Firewall screen over any free-text notes attached to the candidate.
        notes = cand.get("notes", "")
        blocked, matched = screen(notes)
        if blocked:
            trace.append("TRAP_BLOCKED", quarantine(notes, source=name))
        facts = _facts_from_candidate(cand)
        if blocked:
            facts.hostile_source = True
        if rpc is not None:
            # Live reads override the generic facts (verification,
            # total minted, supply cap, ownership). A failed required
            # read sets live_error and the candidate SKIPs.
            facts = gather_live_facts(
                facts, rpc, wallet=args.wallet or None,
            )
            trace.append("LIVE_FACTS", {
                "candidate": name,
                "live_note": facts.live_note,
                "live_error": facts.live_error,
            })
        decision, results = evaluate(
            facts,
            kill_active=killswitch.is_active(RUN_DIR),
            watchdog_expired=watchdog.expired,
        )
        for result in results:
            trace.append("GATE", {
                "candidate": name,
                "gate": result.gate,
                "passed": result.passed,
                "reason": result.reason,
            })
        reason = next(
            (r.reason for r in results if not r.passed),
            "all gates passed",
        )
        gate_trail = "; ".join(
            f"{r.gate}:{'PASS' if r.passed else 'FAIL'}" for r in results
        )
        note = advisor.triage_note(name, decision, reason, gate_trail)
        trace.append("DECISION", {
            "candidate": name, "decision": decision, "reason": reason,
        })
        if decision == "WOULD_MINT" and args.live:
            try:
                execute_live(
                    live=True, approval_token=args.approval_token or "",
                    kill_active=killswitch.is_active(RUN_DIR),
                    gates_passed=True, value_wei=0, contract=facts.contract,
                )
            except (LiveRefused, NotImplementedError) as exc:
                trace.append("LIVE_REFUSED", {"candidate": name, "error": str(exc)})
                decision = "HOLD"
                reason = f"live execution refused: {exc}"
        elif decision == "WOULD_MINT":
            trace.append("SIMULATED_MINT", {
                "candidate": name, "value_wei": 0,
                "note": "dry-run: no transaction attempted",
            })
        decisions.append({
            "name": name,
            "contract": facts.contract,
            "decision": decision,
            "reason": reason,
            "live_error": facts.live_error,
            "live_note": facts.live_note,
            "gates": [
                {"gate": r.gate, "passed": r.passed, "reason": r.reason}
                for r in results
            ],
            "note": note,
        })

    aborted = killswitch.is_active(RUN_DIR) or watchdog.expired
    report_path, status_path = write_report(
        RUN_DIR, run_id, decisions, started,
        note="Run stopped by kill switch." if aborted else "",
        aborted=aborted,
    )
    trace.append("RUN_END", {
        "candidates": len(decisions),
        "would_mint": sum(1 for d in decisions if d["decision"] == "WOULD_MINT"),
        "aborted": aborted,
    })
    print(f"run {run_id}: {len(decisions)} candidates, "
          f"{sum(1 for d in decisions if d['decision'] == 'WOULD_MINT')} WOULD_MINT, "
          f"{sum(1 for d in decisions if d['decision'] != 'WOULD_MINT')} SKIP/HOLD")
    print(f"report: {report_path} · status: {status_path}")
    return 0


def cmd_status(_args) -> int:
    status = read_status(RUN_DIR)
    if status is None:
        print("no run yet — run `sentinel run` first")
        return 1
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0


def cmd_stop(_args) -> int:
    path = killswitch.arm(RUN_DIR)
    print(f"kill switch armed: {path} — the run halts within one tick")
    return 0


def cmd_trap_test(args) -> int:
    try:
        traps = _load_json(args.traps)
    except (OSError, ValueError) as exc:
        print(f"error: cannot load traps file: {exc}", file=sys.stderr)
        return 2
    blocked = 0
    for i, trap in enumerate(traps, start=1):
        is_blocked, matched = screen(trap.get("text", ""))
        print(f"trap {i}: {'BLOCKED' if is_blocked else 'MISSED'} "
              f"({trap.get('label', '')})")
        if is_blocked:
            blocked += 1
    print(f"trap-test: {blocked}/{len(traps)} hostile inputs blocked")
    return 0 if blocked == len(traps) else 1


def cmd_verify_trace(_args) -> int:
    path = os.path.join(RUN_DIR, "trace.jsonl")
    ok, errors = verify_trace(path)
    print("verify-trace: PASS" if ok else "verify-trace: FAIL")
    for err in errors:
        print(f"  - {err}")
    return 0 if ok else 1


def cmd_dashboard(args) -> int:
    serve(RUN_DIR, port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="evaluate candidates (dry-run by default)")
    p_run.add_argument("--candidates", default="fixtures/candidates.json",
                       help="candidate JSON file (use '' to skip the file)")
    p_run.add_argument("--static-list", default="",
                       help="extra candidates from a static scan-list JSON file")
    p_run.add_argument("--manual", action="append", default=[],
                       help="one-off candidate: 'Name|0xContract' or a full "
                            "candidate JSON object (repeatable)")
    p_run.add_argument("--live-reads", action="store_true",
                       help="override generic facts with live Sourcify + BSC "
                            "RPC reads (fixtures stay the offline fallback)")
    p_run.add_argument("--wallet", default="",
                       help="wallet address for live ownership check (G1)")
    p_run.add_argument("--live", action="store_true",
                       help="attempt live execution (refused unless authorised)")
    p_run.add_argument("--approval-token", default="")
    p_run.add_argument("--max-seconds", type=float, default=MAX_RUNTIME_SECONDS)
    p_run.set_defaults(func=cmd_run)

    p_status = sub.add_parser("status", help="show the last run status")
    p_status.set_defaults(func=cmd_status)

    p_stop = sub.add_parser("stop", help="arm the kill switch")
    p_stop.set_defaults(func=cmd_stop)

    p_trap = sub.add_parser("trap-test", help="prove the hostile-input firewall")
    p_trap.add_argument("--traps", default="fixtures/traps.json")
    p_trap.set_defaults(func=cmd_trap_test)

    p_verify = sub.add_parser("verify-trace", help="audit the run trace")
    p_verify.set_defaults(func=cmd_verify_trace)

    p_dash = sub.add_parser("dashboard", help="serve the live status page")
    p_dash.add_argument("--port", type=int, default=8787)
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
