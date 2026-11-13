# Steering — Structure

```
sentinel/          # the agent
  cli.py          # commands: run / status / stop / trap-test / verify-trace / dashboard
  gates.py        # G0–G6 pure deterministic functions
  chain.py        # BSC RPC + Sourcify read-only helpers
  live_facts.py   # merge live reads into gate facts (fail-closed)
  sources.py      # candidate sources: static scan list + manual input
  firewall.py     # hostile-input detection + quarantine
  trace.py        # append-only JSONL writer + verifier
  killswitch.py   # KILL file + watchdog
  report.py       # report.md + status.json writers
  advisor.py      # LLM triage notes (optional, offline-safe)
  executor.py     # live path only; refuses unless fully authorised
  dashboard.py    # stdlib HTTP server for live status
.kiro/
  specs/sentinel/ # requirements.md, design.md, tasks.md
  steering/       # product.md, tech.md, structure.md
  hooks/          # on-save-test.json
  settings/       # mcp.json
tests/            # test_gates.py, test_killswitch.py, test_firewall.py, test_trace.py, test_live_reads.py, test_sources.py, test_dashboard.py, test_edge_cases.py
fixtures/         # candidates.json (5 demo), traps.json (4 hostile), scan-list.json (3 static), live-demo.json (1 real contract)
demo/             # run_demo.sh (unattended demo) + record_demo.sh + demo.mp4
run/              # runtime output (git-ignored): trace.jsonl, report.md, status.json, KILL
```

Rules: keep `gates.py` free of I/O; keep the `.kiro/` directory at the
repo root and out of `.gitignore`; keep `run/` out of git.
