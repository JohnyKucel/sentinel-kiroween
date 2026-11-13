# Design — Sentinel (Kiroween 2026, Frankenstein)

## Overview

Sentinel is a single-process Python CLI. One run = one cycle:
`discover → gate (fail-fast) → decide → report`. Optional live execution
is a separate, heavily guarded path. A tiny stdlib HTTP server provides the
live dashboard. The LLM is a note-writer, never a decider.

```
TRIGGER (sentinel run / cron)
  → DISCOVER candidates (JSON file; live scan sources later)
  → PER CANDIDATE: firewall screen → gates G0–G6 (fail-fast)
  → DECIDE: WOULD_MINT / SKIP (+ reason) / HOLD (live, awaiting approval)
  → EXECUTE (live only: approval token + clean preview + kill switch clear)
  → REPORT: run/report.md + run/status.json + run/trace.jsonl
  → STOP: kill switch / watchdog / max runtime
```

## Architecture

```
sentinel/
  cli.py          # run / status / stop / trap-test / verify-trace / dashboard
  gates.py        # G0–G6, pure deterministic functions (no I/O except reads)
  chain.py        # BSC RPC + Sourcify reads (read-only, requests)
  firewall.py     # hostile-input detection + quarantine
  trace.py        # append-only JSONL writer + verifier
  killswitch.py   # KILL file + watchdog checks
  report.py       # report.md + status.json
  executor.py     # the ONLY module that can write on-chain; refuses by default
  dashboard.py    # stdlib http.server, serves live status page
  advisor.py      # LLM triage notes (Gemini free tier); offline-safe fallback
```

## Key design decisions

### Read/write split

`gates.py`, `chain.py`, `firewall.py`, `trace.py`, and `report.py` cannot
write on-chain. Only `executor.py` can, and it refuses unless **all** of:
live mode, valid per-run human approval token, clean preview, kill switch
clear, all gates PASS, value == 0. This is the same split as the safety
model in `SAFETY.md`.

### Deterministic gates, LLM advisory

Gate outcomes are pure functions over on-chain/API facts. The LLM receives
the facts and returns a one-paragraph triage note. The note is stored, never
parsed. If the LLM is absent, the note is a fixed fallback string. A run
with no LLM is still a complete, verifiable run — this keeps the judges'
dry-run free and deterministic.

### Fail-fast, recorded

Gates run in order and stop at the first failure. Every gate result is a
trace event, so a decision can be replayed from the trace alone.

### Trace as flight recorder

`run/trace.jsonl` is append-only: one JSON object per line with
`ts`, `run_id`, `event`, and `data`. `verify-trace` replays it and checks
that every decision event is preceded by its gate trail and that sequence
numbers are contiguous — a removed line breaks the chain.

### Kill switch within one tick

The run loop checks `run/KILL` before each candidate and before each
write. `sentinel stop` creates the file. No polling daemon, no race: the
check is synchronous in the loop.

### Dashboard with zero dependencies

`dashboard.py` uses `http.server` from the standard library and reads
`run/status.json` + the tail of `run/trace.jsonl`. No JavaScript framework,
no build step — judges can run it with stock Python.

## Data model

Candidate (JSON):

```json
{
  "name": "Example Free Mint",
  "contract": "0x...",
  "chainId": 56,
  "freeFunction": "mint(uint256)",
  "sources": ["https://example.com/mint"]
}
```

Gate result:

```json
{"gate": "G3", "passed": false, "reason": "free exhausted: 1000/1000 claimed"}
```

Trace event:

```json
{"seq": 12, "ts": "2026-11-10T04:00:00Z", "run_id": "r-01", "event": "GATE", "data": {...}}
```

## Testing strategy

- Unit tests for every gate (pass + fail cases), the kill switch, the
  firewall (4 hostile fixtures), and the trace verifier (including a
  tampered trace).
- Property-style test: a random candidate generator must never produce a
  `WOULD_MINT` when any gate fact is failing.
- Demo fixtures: 5 candidates — 1 passes everything, 4 fail on different
  gates — so the demo video shows the full decision range in one run.
