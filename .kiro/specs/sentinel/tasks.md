# Tasks — Sentinel (Kiroween 2026, Frankenstein)

Status: skeleton (Nov 10) — items 1–6 done in skeleton form, 7–12 to
complete during the build window (deadline Dec 4, 2026 14:00 PT).

- [x] 1. Scaffold repo: README, LICENSE (MIT), .env.example, .gitignore
      (`.kiro/` explicitly NOT ignored), requirements.txt
- [x] 2. Write Kiro spec: requirements.md, design.md, tasks.md
- [x] 3. Write steering docs: product.md, tech.md, structure.md
- [x] 4. Implement core modules (skeleton, working):
  - [x] 4.1 `gates.py` — G0–G6 pure functions + `evaluate()`
  - [x] 4.2 `firewall.py` — hostile-pattern screen + quarantine
  - [x] 4.3 `trace.py` — append-only JSONL writer + verifier
  - [x] 4.4 `killswitch.py` — KILL file + watchdog
  - [x] 4.5 `chain.py` — BSC RPC + Sourcify read-only helpers
  - [x] 4.6 `report.py` — report.md + status.json
  - [x] 4.7 `advisor.py` — LLM notes with offline fallback
  - [x] 4.8 `executor.py` — live path, refuses by default
  - [x] 4.9 `dashboard.py` — stdlib live status server
  - [x] 4.10 `cli.py` — run / status / stop / trap-test / verify-trace / dashboard
- [x] 5. Fixtures: 5 demo candidates (1 pass, 4 fail on distinct gates)
      + 4 hostile trap inputs
- [x] 6. Unit tests: gates, kill switch, firewall, trace verifier
- [x] 7. Wire live chain reads into `run` (Sourcify + BSC RPC per
      candidate); keep fixtures as the offline fallback — DONE 10 Nov
      (46 tests, live demo UnWritten: 8822/8888, exact_match)
- [x] 8. Run the full demo end-to-end; record the 3-minute demo video
      (one unattended run: scan → 1 pass + 4 skips → trap-test → kill
      switch → report) — DONE 10 Nov: `demo/demo.mp4` (38 detik,
      1280x720, rekaman layar nyata Xvfb + xterm + ffmpeg, tanpa suara).
      Offline run 1 WOULD_MINT + 4 SKIP; sources run 2 + 2; live-reads
      0 + 5 (fail-closed); trap-test 4/4; kill switch armed mid-run,
      run aborted after 3 candidates; final run verify-trace PASS.
- [x] 9. Kiro usage pass: drive remaining implementation through Kiro CLI
      (spec tasks, hooks, steering); record the Kiro write-up with real
      examples (specs, hooks, steering, MCP) for the submission form
      — DONE 10 Nov: hooks extended (sources + dashboard on-save tests,
      21 passed); specs/steering drove the Fase 3 build. Kiro CLI chat
      + `mcp list` BLOCKED — not logged in, needs Grey's login
      (`kiro-cli login --use-device-flow`); limitation recorded in
      README, not hidden. Fase 4 extension (10 Nov, same day): hooks +2
      (`chain.py`, `live_facts.py` → `test_live_reads.py`, 22 passed),
      MCP server `sequential-thinking` added, paste-ready write-up
      `KIRO_USAGE.md` with claim / no-claim table; chat/MCP still
      blocked on login — not run, not claimed.
      **13 Nov update: login DONE** via device flow (Builder ID
      sandijohan113@gmail.com; `whoami` confirms, `mcp list` works).
      One agent turn driven through `kiro-cli chat` (13 Nov,
      `--no-interactive --trust-all-tools`): pytest 95 passed in
      2.31s, ffprobe demo.mp4 45.67s, CHECKLIST.md Phase 5 read — all
      verified by the turn itself. MCP servers still NOT driven live
      through the CLI (no-claim stands). `KIRO_USAGE.md` + README
      updated to the new honest state.
- [ ] 10. Claim the 4,000 free Kiro credits (Grey: Resources tab, ID
      verification, before Dec 1 12:00 PT) — needed only if Kiro usage
      exceeds the free plan during the build. **13 Nov: Devpost
      registration DONE + Kiro User ID known
      (`d-9067c98495.04a874c8-20c1-7000-ea62-d1058ad6c3c9`), so the
      form is fillable; only the Didit ID check still needs Grey.**
- [x] 11. Publish public GitHub repo (Grey presses publish) with LICENSE
      visible, `.kiro/` at root, README + demo video link — **DONE
      13 Nov: https://github.com/JohnyKucel/sentinel-kiroween (PUBLIC,
      MIT detected, `.kiro/` at root, commit 5c37490).**
- [ ] 12. Submit on Devpost (Grey): category Frankenstein, repo URL,
      working app URL/instructions, demo video (YouTube, public, <3 min),
      Kiro usage write-up, description. **13 Nov: submission packet
      drafted in `SUBMISSION.md` (all fields except the YouTube URL);
      video upload still needs Grey; submit needs parent confirmation.**
