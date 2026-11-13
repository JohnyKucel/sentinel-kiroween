# Steering — Tech

- Python 3.11+, standard library first. Runtime dependencies: `requests`
  only. Dev: `pytest`.
- No paid APIs in the default path. Gemini free tier is optional, for
  triage notes only; the run works fully offline with fixtures.
- Network access is read-only: BSC public RPC + Sourcify API. No wallet
  connection, no signing, no transaction in dry-run.
- Secrets live in `.env` (git-ignored), never in code, never in the trace,
  never in the report.
- Trace is append-only JSONL; never rewrite history. `verify-trace` replays
  it and fails on gaps.
- Every module has a single responsibility; `executor.py` is the only
  module allowed to write on-chain, and it refuses by default.
- Tests: `pytest -q` must pass before any commit.
- MCP servers declared in `.kiro/settings/mcp.json` are read-only or
  no-I/O (fetch, sequential-thinking). No credentials in MCP config.
