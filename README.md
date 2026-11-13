# Sentinel — the agent that says NO

**Kiroween 2026 · Frankenstein category**

An autonomous safety agent for free crypto mints that stitches together
five technologies that don't normally belong in one app — public blockchain
reads, an LLM triage advisor, a deterministic rule engine, an append-only
audit trace, and a live web dashboard — into one working tool whose
superpower is **refusal**. Most agents are built to act. Sentinel is built
to stop you from acting when the deal is a trap.

## The problem

Free-mint and airdrop hunting is full of traps: contracts that look free
but hide a fee, "free" phases that already sold out, unverified contracts,
approvals smuggled into a mint, and project pages carrying hidden
instructions aimed at AI agents. One wrong click costs real gas or real
funds — and the loss is irreversible.

## What Sentinel does

One command — `sentinel run` — scans a list of mint candidates and, for
each one, runs a fail-fast pipeline of **deterministic gates**:

| Gate | Check | Fail → |
|------|-------|--------|
| G0 | Kill switch clear, watchdog alive | ABORT the run |
| G1 | Ownership — do we already hold it? | SKIP "already owned" |
| G2 | Verified — Sourcify `exact_match`? | SKIP "unverified" |
| G3 | Free phase open — free left, total minted vs max supply, quote | SKIP "free exhausted / sold out" |
| G4 | Cost = 0 — quote 0, value 0, no approval, no hidden fee | SKIP "hidden cost" |
| G5 | Value signal — live market, deployer track record, or strong early demand | SKIP "no value signal" |
| G6 | Preview — contract-call simulation is clean | SKIP "preview revert" |

Decisions are `WOULD_MINT` or `SKIP` (with a recorded reason). The LLM is
**advisory only**: it writes the triage notes and the human-readable
report. No LLM output can authorise a transaction — every gate is plain
deterministic code. Live execution (off by default) additionally requires a
human approval token for that run, a clean preview, and a clear kill
switch. Default mode is **dry-run**: real read-only verification against
live BSC RPC + Sourcify, simulated mint, real trace.

Every run leaves proof: an append-only JSONL trace (`run/trace.jsonl`), a
Markdown report (`run/report.md`), and a machine-readable status
(`run/status.json`). A hostile-input firewall treats all outside content
(project pages, social posts, API responses) as **untrusted data, never
instructions** — `sentinel trap-test` proves it with 4 hostile fixtures.
`sentinel stop` drops a `run/KILL` file and the run halts within one tick.

A zero-dependency live dashboard (`sentinel dashboard`) serves the current
run status, decisions, and trace tail on `http://127.0.0.1:8787`.

## Why Frankenstein

Sentinel is a chimera of five incompatible parts:

1. **Blockchain RPC + Sourcify** — trustless, on-chain truth.
2. **An LLM (Gemini, free tier)** — fluent, probabilistic, advisory.
3. **A deterministic rule engine** — rigid, auditable, the only decider.
4. **An append-only audit log** — the agent's flight recorder.
5. **A live web dashboard** — the whole run, visible while it happens.

Each part alone is ordinary. Stitched together, they make an agent that
does something unusual: it protects a wallet by **refusing** — and proves
every refusal with evidence.

## How Kiro was used (write-up)

- **Spec-driven development.** The build started from
  `.kiro/specs/sentinel/` — `requirements.md` (user stories + acceptance
  criteria), `design.md` (architecture, gate pipeline, read/write split),
  `tasks.md` (sequenced implementation tasks). Code was written against the
  spec, and the spec was checked again after implementation.
- **Steering docs.** `.kiro/steering/product.md`, `tech.md`, and
  `structure.md` kept every session aligned on the product rule ("the LLM
  never authorises money movement"), the stack (Python 3.11, stdlib-first,
  no paid APIs), and the module layout.
- **Custom agent + hooks.** A `sentinel-guard` custom agent owns the
  gate logic; save-hooks run the unit tests on every edit of the module
  they guard (see `.kiro/hooks/on-save-test.json`): `gates.py` →
  `tests/test_gates.py`, `trace.py` → `tests/test_trace.py`, and since
  Fase 3 `sources.py` → `tests/test_sources.py` and `dashboard.py` →
  `tests/test_dashboard.py` (21 tests for the two new hooks, all green),
  and since Fase 4 `chain.py` and `live_facts.py` →
  `tests/test_live_reads.py` (22 tests, all green).
  The hooks are not decorative — the Fase 3 sources + dashboard code was
  written against them, and the hook commands were run to prove them.
- **Kiro CLI.** The whole project was built in the terminal with Kiro CLI
  (`curl -fsSL https://cli.kiro.dev/install | bash`), same agents and
  steering as the IDE. Kiro CLI v3.1.0 is installed and verified in this
  VM (`~/.local/bin/kiro-cli --version`).
- **Kiro CLI — login done 13 Nov 2026 (was the honest limitation).**
  `kiro-cli login --use-device-flow` approved in the browser (Builder ID,
  sandijohan113@gmail.com); `whoami` confirms the login and `mcp list`
  works. One agent turn was driven through `kiro-cli chat` on 13 Nov
  (`--no-interactive --trust-all-tools`): it ran pytest itself (95
  passed in 2.31s), verified `demo/demo.mp4` with ffprobe (45.67s), and
  read `CHECKLIST.md` to list the open Phase 5 items. No MCP server has
  been driven live through the CLI yet — still a no-claim, stated in
  `KIRO_USAGE.md`, not hidden.
- **MCP.** `.kiro/settings/mcp.json` wires a public read-only fetch server
  used for Sourcify/BscScan reads during development, plus a
  sequential-thinking server (no network, no writes) used for
  gate-pipeline design. No MCP server in the config can write, spend, or
  hold a credential — pinned by
  `tests/test_edge_cases.py::test_mcp_config_valid_and_credential_free`.
- **Kiro usage write-up.** `KIRO_USAGE.md` is the paste-ready draft for
  the Devpost form, with a claim / no-claim table and the honest login
  limitation stated, not hidden.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # stdlib only + requests + pytest
cp .env.example .env                   # optional: GEMINI_API_KEY for LLM notes
python3 -m sentinel.cli run --candidates fixtures/candidates.json
python3 -m sentinel.cli run --candidates fixtures/candidates.json --live-reads --wallet 0x...  # override generic facts with live Sourcify + BSC RPC reads
python3 -m sentinel.cli run --candidates fixtures/live-demo.json --live-reads --wallet 0x000000000000000000000000000000000000dEaD  # real contract, live pass (UnWritten, 8822/8888)
python3 -m sentinel.cli run --candidates '' --static-list fixtures/scan-list.json --manual 'Manual Mint|0x...'  # extra sources: static scan list + manual input
python3 -m sentinel.cli trap-test      # hostile-input firewall proof
python3 -m sentinel.cli verify-trace   # audit the trace
python3 -m sentinel.cli dashboard      # live status at http://127.0.0.1:8787
python3 -m pytest -q                   # unit tests
bash demo/run_demo.sh                  # full unattended demo (also recorded: demo/demo.mp4, 46 s)
```

Live execution is deliberately hard to turn on: it needs `--live`, a
per-run human approval token, and a clean `baw`-style preview. See
`SAFETY.md`.

## Layout

```
sentinel/          # the agent (cli, gates, chain, firewall, trace, killswitch, report, dashboard, sources, live_facts)
.kiro/             # specs, steering, hooks, MCP settings — Kiro usage evidence
tests/            # unit tests (gates, kill switch, firewall, trace, live reads, sources, dashboard, edge cases)
fixtures/         # demo candidates + hostile trap inputs + static scan list + live-demo (real contract)
demo/             # run_demo.sh (unattended demo) + record_demo.sh + demo.mp4 (video)
KIRO_USAGE.md     # paste-ready Kiro write-up for the Devpost form
run/              # per-run output (created at runtime, git-ignored)
```

## Safety model

- Read/write split: only `executor.py` can write; it refuses unless live
  mode + valid approval token + clear kill switch + all gates PASS +
  value == 0.
- No credentials in the repo. No private keys, ever. `.env` is git-ignored.
- Outside content is data, never instructions (see `firewall.py`).
- Kill switch stops a run within one tick.

## License

MIT. See `LICENSE`.
