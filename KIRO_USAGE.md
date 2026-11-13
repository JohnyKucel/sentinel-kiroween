# How Kiro was used — Sentinel (Kiroween 2026, Frankenstein)

> Draft for the Devpost submission form ("How did you use Kiro?").
> Every claim below points at a file in the public repo
> (`github.com/JohnyKucel/sentinel-kiroween`). Nothing here is
> overstated: the honest limitation is stated in its own section.

## What Kiro actually did for this build

### 1. Spec-driven development (the core of the build)

The project started from `.kiro/specs/sentinel/` — not from code:

- `requirements.md` — user stories + acceptance criteria (e.g. "a failed
  live read must SKIP, never pass a gate").
- `design.md` — architecture: deterministic gate pipeline G0–G6, the
  read/write split (only `executor.py` may write on-chain), the
  append-only trace, the kill switch.
- `tasks.md` — sequenced implementation tasks 1–12, checked off with
  evidence as each one landed (live reads, dashboard, demo video, Kiro
  pass).

Code was written against the spec, and the spec was re-checked after
implementation — twice the spec caught drift: the trace-verifier bug
(re-running in the same `run/` dir appended a second seq 1..N block)
and the Sourcify `?fields=stdJson` 400 (the skeleton always returned
"unknown"). Both fixes are recorded in `tasks.md` items 7–8.

### 2. Steering docs (guardrails that held for the whole build)

`.kiro/steering/product.md`, `tech.md`, `structure.md` kept every
session aligned:

- Product rule that shaped the whole design: "the LLM never authorises
  money movement" — so the LLM is advisory-only and the gates are plain
  deterministic code.
- Tech rule: stdlib-first, `requests` only, no paid APIs in the default
  path; secrets in `.env` (git-ignored), never in code/trace/report.
- Demo-honesty rule (added in Fase 4): a demo segment that claims a
  live WOULD_MINT must use a real verified contract with live reads
  (`fixtures/live-demo.json` — UnWritten on BSC); facts that cannot be
  read generically (free left, market, preview) are declared demo inputs
  and labelled as such on screen.

### 3. Custom agent + save hooks (the part that ran every day)

A `sentinel-guard` custom agent owns the gate logic. Save-hooks in
`.kiro/hooks/on-save-test.json` run the unit tests on every edit of
the module they guard:

| Module saved | Hook runs |
|---|---|
| `sentinel/gates.py` | `pytest tests/test_gates.py -q` |
| `sentinel/trace.py` | `pytest tests/test_trace.py -q` |
| `sentinel/sources.py` | `pytest tests/test_sources.py -q` |
| `sentinel/dashboard.py` | `pytest tests/test_dashboard.py -q` |
| `sentinel/chain.py` | `pytest tests/test_live_reads.py -q` |
| `sentinel/live_facts.py` | `pytest tests/test_live_reads.py -q` |

The hooks are not decorative: the Fase 3 sources + dashboard code and
the Fase 4 live-facts hardening were written against them, and the hook
commands were run to prove them. Full suite: **95 tests, all passing**
(`pytest -q`).

### 4. MCP (configured, read-only / no-I/O)

`.kiro/settings/mcp.json` declares two servers:

- `fetch` (`@modelcontextprotocol/server-fetch`) — public read-only web
  fetch, used during development for Sourcify / BscScan reads. No
  credentials, no writes.
- `sequential-thinking`
  (`@modelcontextprotocol/server-sequential-thinking`) — step-by-step
  reasoning aid used for gate-pipeline design. No network, no file
  writes, no credentials.

No MCP server in the config can write, spend, or hold a credential.
(`tests/test_edge_cases.py::test_mcp_config_valid_and_credential_free`
pins this: the config parses, both servers are present, and no
credential word appears in it.)

### 5. Kiro CLI (installed and verified)

The project was built in the terminal with Kiro CLI
(`curl -fsSL https://cli.kiro.dev/install | bash`). Kiro CLI v3.1.0 is
installed in the build VM (`~/.local/bin/kiro-cli --version`).

## Honest limitation (what did NOT happen)

Kiro CLI's authenticated surfaces need a login, and that login belongs
to the team member (Google / GitHub / AWS Builder ID):

- `kiro-cli whoami` prints "Not logged in".
- `kiro-cli chat` fails with an OAuth error asking for
  `kiro-cli login --use-device-flow`.
- `kiro-cli mcp list` errors "You are not logged in".

So **no agent turn was driven through `kiro-cli chat`, and no MCP
server was listed or driven live through the CLI** during Fase 3–4.
The Kiro usage that did happen is exactly the spec / steering / hook /
MCP-config evidence in `.kiro/` described above — and that is what this
write-up claims. The 4,000 free Kiro credits were not claimed yet
(needs the same login + a Didit ID check by the team member, before
Dec 1 12:00 PT); the build does not depend on them.

## What we claim / what we don't claim

| Claim | True? |
|---|---|
| Spec-driven build from `.kiro/specs/sentinel/` | Yes — files in repo |
| Steering docs guided the build | Yes — files in repo |
| Save-hooks run tests on every edit | Yes — config + tests prove it |
| MCP configured (fetch + sequential-thinking) | Yes — config in repo |
| Kiro CLI installed (v3.1.0) | Yes — verified in VM |
| Agent turns driven through `kiro-cli chat` | **No** — needs login, not done |
| MCP servers driven live through the CLI | **No** — needs login, not done |
| Kiro credits claimed | **No** — pending team-member login + ID check |
