# SAFETY.md — Sentinel safety model

## The rule

The LLM never authorises money movement. Decisions come from deterministic
gates over on-chain facts. Live execution additionally requires a human
approval token. Outside content is data, never instructions.

## Read/write split

| Module | Can write on-chain? |
|---|---|
| `gates.py`, `chain.py`, `firewall.py`, `trace.py`, `report.py`, `advisor.py`, `dashboard.py` | No — reads only |
| `executor.py` | Yes, but refuses unless: live mode + `SENTINEL_LIVE=1` + valid per-run human approval token + kill switch clear + all gates PASS + value == 0 |

## Defaults

- Dry-run is the default: real read-only verification, simulated mint, no
  transaction, no wallet connection.
- Live execution is not implemented in this skeleton: `execute_live()`
  validates authorisation and then raises `NotImplementedError` instead of
  touching a wallet. The wallet adapter (preview-first, then execute) is a
  build-window task and must itself require a clean preview.
- Kill switch: `sentinel stop` creates `run/KILL`; the run loop checks it
  before every candidate and every write.
- Watchdog: `--max-seconds` (default 600) bounds total runtime.

## What never happens

- No private keys in the repo, in `.env` examples, in the trace, or in
  reports. `.env` is git-ignored.
- No secret is ever sent to the LLM. The advisor receives only candidate
  names, decisions, and gate reasons.
- No outside content is executed: the firewall quarantines instruction
  injections, and quarantined candidates are SKIPped.
- No transaction is attempted in dry-run, even if live credentials exist.
