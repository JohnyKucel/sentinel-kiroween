"""Run reporting: report.md (human) + status.json (machine).

Both are written at the end of a run from the same decision list, so the
human report and the machine status can never disagree.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_report(run_dir: str, run_id: str, decisions: list[dict],
                 started: str, note: str = "",
                 aborted: bool = False) -> tuple[str, str]:
    """decisions: [{name, contract, decision, reason, gates: [...], note}].

    Returns (report_path, status_path).
    """
    os.makedirs(run_dir, exist_ok=True)
    ended = _now_iso()
    passed = sum(1 for d in decisions if d["decision"] == "WOULD_MINT")
    skipped = len(decisions) - passed

    lines = [
        f"# Sentinel run {run_id}",
        "",
        f"Started: {started} UTC · Ended: {ended} UTC",
        f"Decisions: {len(decisions)} candidates — "
        f"{passed} WOULD_MINT, {skipped} SKIP",
    ]
    if note:
        lines += ["", note]
    lines += ["", "## Decisions", ""]
    for d in decisions:
        lines.append(f"### {d['name']} — {d['decision']}")
        lines.append(f"- Contract: `{d['contract']}`")
        lines.append(f"- Reason: {d['reason']}")
        for g in d.get("gates", []):
            mark = "PASS" if g["passed"] else "FAIL"
            lines.append(f"  - {g['gate']}: {mark} — {g['reason']}")
        if d.get("note"):
            lines.append(f"- Triage note: {d['note']}")
        lines.append("")
    report_path = os.path.join(run_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    status = {
        "run_id": run_id,
        "started": started,
        "ended": ended,
        "candidates": len(decisions),
        "would_mint": passed,
        "skipped": skipped,
        "aborted": aborted,
        "note": note,
        "decisions": decisions,
    }
    status_path = os.path.join(run_dir, "status.json")
    with open(status_path, "w", encoding="utf-8") as fh:
        json.dump(status, fh, indent=2, ensure_ascii=False)
    return report_path, status_path


def read_status(run_dir: str) -> dict | None:
    path = os.path.join(run_dir, "status.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
