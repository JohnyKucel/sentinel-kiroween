# Requirements — Sentinel (Kiroween 2026, Frankenstein)

## Introduction

Sentinel is an autonomous safety agent for free crypto mints. It scans
mint candidates, verifies each one against live on-chain data through a
deterministic gate pipeline, and decides `WOULD_MINT` or `SKIP` with a
recorded reason. The LLM is advisory only. Every run leaves an append-only
audit trace and a Markdown report. A kill switch halts a run within one
tick. A zero-dependency dashboard shows the run live.

## Glossary

- **Candidate:** a mint opportunity: contract address, chain, claimed free
  function, and source links.
- **Gate:** one deterministic check. Fail-fast: the first failed gate ends
  evaluation of that candidate.
- **Decision:** `WOULD_MINT` | `SKIP` | `HOLD` (awaiting human approval,
  live only) | `ABORT` (kill switch / watchdog).
- **Trace:** append-only JSONL audit log, one event per line.
- **Dry-run (default):** real read-only verification, simulated mint, no
  transaction, no wallet connection.
- **Live:** real execution; requires `--live` + per-run human approval token
  + clean preview + clear kill switch + value == 0.

## Requirements

### Requirement 1 — One-command run

**User Story:** As a wallet owner, I want one command to evaluate a list
of mint candidates, so that I get a decision per candidate without manual
checks.

#### Acceptance Criteria

1. WHEN I run `sentinel run --candidates <file>` THEN the agent SHALL
   evaluate every candidate in order and finish with a summary line.
2. WHEN a candidate file is missing or malformed THEN the agent SHALL exit
   non-zero with a clear error and write no trace.
3. WHEN the run finishes THEN `run/report.md`, `run/status.json`, and
   `run/trace.jsonl` SHALL exist.

### Requirement 2 — Deterministic gate pipeline

**User Story:** As a wallet owner, I want every decision to come from
auditable code, not from model vibes, so that a decision can be replayed
and trusted.

#### Acceptance Criteria

1. WHEN a candidate is evaluated THEN gates SHALL run in order G0–G6 and
   stop at the first failure.
2. WHEN any gate fails THEN the decision SHALL be `SKIP` with the exact
   gate id and reason recorded in the trace and the report.
3. WHEN all gates pass THEN the decision SHALL be `WOULD_MINT`.
4. WHEN the kill-switch file exists or the watchdog timed out THEN the run
   SHALL `ABORT` before evaluating further candidates.

### Requirement 3 — LLM advisory only

**User Story:** As a wallet owner, I want AI help with triage notes, but I
never want a model output to authorise money movement.

#### Acceptance Criteria

1. WHEN the LLM is unavailable THEN the run SHALL still complete with all
   decisions, using a plain-text fallback note.
2. WHEN the LLM returns text THEN it SHALL be stored as a note only, never
   parsed as a decision or a command.
3. WHEN live execution is requested THEN approval SHALL come from a human
   token, never from model output.

### Requirement 4 — Kill switch

**User Story:** As a wallet owner, I want to stop a run instantly, so that
a bad run cannot keep spending gas.

#### Acceptance Criteria

1. WHEN `sentinel stop` runs THEN a `run/KILL` file SHALL be created.
2. WHEN the `run/KILL` file exists THEN an in-progress run SHALL halt
   within one tick (before the next candidate or the next write).
3. WHEN a run aborts THEN the trace SHALL contain an `ABORTED` event and
   the report SHALL state the run was stopped.

### Requirement 5 — Hostile-input firewall

**User Story:** As a wallet owner, I want project pages and social posts
treated as untrusted data, so that an instruction hidden in a page cannot
make the agent mint, transfer, or approve anything.

#### Acceptance Criteria

1. WHEN outside content contains an instruction to mint/transfer/approve/
   execute, or a phrase like "ignore previous instructions" THEN the
   firewall SHALL quarantine it and record `TRAP_BLOCKED`.
2. WHEN `sentinel trap-test` runs THEN all 4 hostile fixtures SHALL be
   blocked and the result SHALL be printed.
3. WHEN a candidate's source content is quarantined THEN the candidate
   SHALL be `SKIP`ped with reason "hostile source".

### Requirement 6 — Audit trace

**User Story:** As a wallet owner, I want a complete record of every run,
so that I can verify what the agent did and why.

#### Acceptance Criteria

1. WHEN any event happens THEN it SHALL be appended as one JSON line with
   timestamp, run id, event type, and payload.
2. WHEN `sentinel verify-trace` runs THEN it SHALL check ordering,
   completeness, and that every decision has a matching gate trail, and
   print PASS or FAIL.
3. WHEN the trace file is tampered with (a line removed) THEN
   `verify-trace` SHALL report FAIL.

### Requirement 7 — Live dashboard

**User Story:** As a wallet owner, I want to watch a run live, so that I
can see decisions as they happen.

#### Acceptance Criteria

1. WHEN `sentinel dashboard` runs THEN it SHALL serve a status page on
   `http://127.0.0.1:8787` using only the standard library.
2. WHEN the page loads THEN it SHALL show run status, per-candidate
   decisions, and the last trace events, refreshing without a page reload
   (meta refresh is acceptable).

### Requirement 8 — Safety defaults

**User Story:** As a wallet owner, I want the safe path to be the default,
so that a typo cannot turn a read-only check into a transaction.

#### Acceptance Criteria

1. WHEN no `--live` flag is passed THEN no transaction SHALL be attempted,
   even if live credentials exist.
2. WHEN live execution is requested THEN it SHALL require a per-run human
   approval token AND a clean preview AND value == 0 AND a clear kill
   switch; any missing piece SHALL refuse with a clear message.
3. WHEN the repo is published THEN it SHALL contain no secrets, no private
   keys, and no `.env` file.
