"""Append-only JSONL audit trace — the run's flight recorder.

One JSON object per line: seq, ts, run_id, event, data. Lines are only
appended, never rewritten. verify_trace() replays a trace file and fails
on gaps, out-of-order sequences, or decisions without a gate trail.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TraceWriter:
    def __init__(self, path: str, run_id: str):
        self.path = path
        self.run_id = run_id
        self.seq = 0
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.exists(path):
            open(path, "w").close()

    def append(self, event: str, data: dict | None = None) -> dict:
        self.seq += 1
        record = {
            "seq": self.seq,
            "ts": _now_iso(),
            "run_id": self.run_id,
            "event": event,
            "data": data or {},
        }
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record


def read_trace(path: str) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def verify_trace(path: str):
    """Replay a trace file. Returns (ok, errors).

    Checks: sequence numbers contiguous from 1; every DECISION event is
    preceded by at least one GATE event for the same candidate; every run
    starts with RUN_START.
    """
    errors: list[str] = []
    try:
        records = read_trace(path)
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"cannot read trace: {exc}"]
    if not records:
        return False, ["trace is empty"]
    for i, rec in enumerate(records, start=1):
        if rec.get("seq") != i:
            errors.append(f"sequence gap: line {i} has seq {rec.get('seq')}")
    if records[0].get("event") != "RUN_START":
        errors.append("first event is not RUN_START")
    seen_gate: set[str] = set()
    for rec in records:
        event = rec.get("event")
        data = rec.get("data") or {}
        if event == "GATE":
            seen_gate.add(str(data.get("candidate", "")))
        elif event == "DECISION":
            cand = str(data.get("candidate", ""))
            if cand not in seen_gate:
                errors.append(f"DECISION for {cand} without a prior GATE trail")
    return (not errors), errors
