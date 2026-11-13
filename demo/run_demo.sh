#!/usr/bin/env bash
# Sentinel — Kiroween 2026 demo (one unattended run, <3 min, no sound).
# Run from the repo root. Banners separate the steps; short sleeps keep
# each screen readable on video. Exits 0 when every step ran.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/bin/python -m sentinel.cli"

banner() { echo; echo "===== $1 ====="; echo; }

banner "Sentinel — the agent that says NO  |  Kiroween 2026 (Frankenstein)"
echo "One unattended run: scan -> sources -> live reads -> trap-test -> kill switch -> report"
sleep 3

banner "1/8  OFFLINE SCAN — fixtures/candidates.json"
$PY run
sleep 3

banner "2/8  SOURCES — static scan list + manual input"
$PY run --candidates '' --static-list fixtures/scan-list.json \
  --manual '{"name":"Manual: Bright Mint","contract":"0x9999999999999999999999999999999999999999","facts":{"verified":true,"free_left":50,"free_cap":1000,"total_minted":100,"max_supply":10000,"quote_wei":0,"needs_approval":false,"hidden_fee":false,"has_market":true,"preview_ok":true}}'
sleep 3

banner "3/8  LIVE READS — synthetic contracts fail closed"
echo "Live reads override fixture facts. Synthetic contracts fail live"
echo "verification, so Sentinel refuses them all — a failed read can"
echo "never pass a gate by accident."
$PY run --live-reads
sleep 3

banner "4/8  LIVE READS — real contract passes (UnWritten, BSC)"
echo "Same live reads, real contract: Sourcify exact_match, 8822/8888"
echo "minted, empty wallet. Free/market/preview facts are declared"
echo "demo inputs — Sentinel cannot read those generically without"
echo "the contract ABI; verification, supply and ownership are live."
$PY run --candidates fixtures/live-demo.json --live-reads \
  --wallet 0x000000000000000000000000000000000000dEaD
sleep 3

banner "5/8  TRAP-TEST — hostile-input firewall (4 hostile fixtures)"
$PY trap-test
sleep 3

banner "6/8  KILL SWITCH — armed mid-run, the run halts"
$PY run --live-reads > /tmp/demo-kill-out.txt 2>&1 &
RUN_PID=$!
sleep 4
$PY stop
wait "$RUN_PID"
cat /tmp/demo-kill-out.txt
sleep 2

banner "7/8  FINAL RUN + TRACE AUDIT"
$PY run
$PY verify-trace
sleep 3

banner "8/8  REPORT + LIVE DASHBOARD"
head -25 run/report.md
$PY dashboard --port 8787 > /tmp/demo-dash-out.txt 2>&1 &
DASH_PID=$!
sleep 2
curl -s http://127.0.0.1:8787/health; echo
curl -s http://127.0.0.1:8787/ | grep -o "<title>[^<]*</title>"
kill $DASH_PID 2>/dev/null
wait $DASH_PID 2>/dev/null
echo
echo "Demo complete — Sentinel refused 4 of 5 mints and proved every refusal."
echo "Trace: run/trace.jsonl  ·  Report: run/report.md  ·  Status: run/status.json"
