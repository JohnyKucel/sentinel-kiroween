"""Live dashboard — zero-dependency status server.

Serves the current run status, per-candidate decisions with their gate
trail and live-facts notes, and the trace tail as a plain HTML page on
http://127.0.0.1:8787, using only the standard library. No framework,
no build step, no external requests.

Endpoints:
  /             HTML dashboard (auto-refreshes every 5 seconds)
  /status.json  the raw run/status.json ({} when no run has happened)
  /health       {"ok": true} — liveness probe
Everything else returns 404. Read-only: the server never writes.
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .killswitch import is_active as kill_active
from .report import read_status
from .trace import read_trace

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
TRACE_TAIL = 15


def _esc(value: object) -> str:
    return html.escape(str(value))


def _gate_chips(decision: dict) -> str:
    """One PASS/FAIL chip per gate, e.g. G2 ✓ / G3 ✗."""
    chips = []
    for gate in decision.get("gates", []):
        mark = "✓" if gate.get("passed") else "✗"
        cls = "pass" if gate.get("passed") else "fail"
        chips.append(
            f'<span class="{cls}">{_esc(gate.get("gate", "?"))} {mark}</span>'
        )
    return " ".join(chips)


def _live_facts(decision: dict) -> str:
    """Short live-reads note: the Sourcify/RPC evidence or the error."""
    note = decision.get("live_note", "") or ""
    error = decision.get("live_error", "") or ""
    if error:
        return f'<span class="fail">live error: {_esc(error)}</span>'
    return _esc(note)


def _event_detail(event: dict) -> str:
    """One-line human summary of a trace event."""
    kind = str(event.get("event", ""))
    data = event.get("data") or {}
    cand = str(data.get("candidate", ""))
    if kind == "GATE":
        mark = "PASS" if data.get("passed") else "FAIL"
        return f"{cand} — {data.get('gate', '?')} {mark}: {data.get('reason', '')}"
    if kind == "DECISION":
        return f"{cand} — {data.get('decision', '?')}: {data.get('reason', '')}"
    if kind == "LIVE_FACTS":
        note = data.get("live_note", "") or data.get("live_error", "")
        return f"{cand} — live: {note}"
    if kind == "TRAP_BLOCKED":
        return f"{cand or 'input'} — hostile input quarantined"
    if kind == "RUN_START":
        return "run started"
    if kind == "RUN_END":
        return (
            f"run ended: {data.get('candidates', '?')} candidates, "
            f"{data.get('would_mint', '?')} WOULD_MINT"
        )
    if kind == "ABORTED":
        return f"run aborted: {data.get('reason', '')}"
    if kind == "SIMULATED_MINT":
        return f"{cand} — simulated mint (dry-run, no transaction)"
    if kind == "LIVE_REFUSED":
        return f"{cand} — live execution refused: {data.get('error', '')}"
    detail = json.dumps(data, ensure_ascii=False)
    return f"{cand + ' — ' if cand else ''}{detail[:140]}"


def render_page(run_dir: str) -> str:
    status = read_status(run_dir)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kill_state = (
        '<span class="fail">KILL ARMED</span>'
        if kill_active(run_dir)
        else '<span class="pass">kill switch clear</span>'
    )
    trace_path = os.path.join(run_dir, "trace.jsonl")
    tail: list[dict] = []
    if os.path.exists(trace_path):
        try:
            tail = read_trace(trace_path)[-TRACE_TAIL:]
        except ValueError:
            tail = []

    if not status:
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>Sentinel — live run</title>
<style>body{{font-family:system-ui,sans-serif;margin:2em}}
h1{{font-size:1.4em}}.pass{{color:#0a7d0a;font-weight:bold}}
.fail{{color:#c00;font-weight:bold}}</style></head>
<body><h1>Sentinel — live run</h1>
<p>No run yet — run <code>sentinel run</code> first.</p>
<p>Kill switch: {kill_state}</p>
<p><small>Auto-refreshes every 5 seconds. Read-only view of run/.</small></p>
</body></html>"""

    aborted = bool(status.get("aborted"))
    badge = (
        '<span class="fail">ABORTED — stopped by kill switch</span>'
        if aborted
        else '<span class="pass">COMPLETED</span>'
    )
    summary = (
        f"Run {_esc(status.get('run_id', ''))} — {badge}<br>"
        f"Started {_esc(status.get('started', ''))} UTC · "
        f"ended {_esc(status.get('ended', ''))} UTC<br>"
        f"{status.get('candidates', 0)} candidates, "
        f"{status.get('would_mint', 0)} WOULD_MINT, "
        f"{status.get('skipped', 0)} SKIP"
    )
    if status.get("note"):
        summary += f"<br>Note: {_esc(status.get('note'))}"

    rows = ""
    for d in status.get("decisions", []):
        rows += (
            "<tr>"
            f"<td>{_esc(d.get('name', ''))}</td>"
            f"<td>{_esc(d.get('decision', ''))}</td>"
            f"<td>{_esc(d.get('reason', ''))}</td>"
            f"<td>{_gate_chips(d)}</td>"
            f"<td>{_live_facts(d)}</td>"
            "</tr>"
        )
    events = "".join(
        f"<li>[{_esc(e.get('seq', ''))}] "
        f"{_esc(e.get('ts', ''))} {_esc(e.get('event', ''))} — "
        f"{_esc(_event_detail(e))}</li>"
        for e in tail
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>Sentinel — live run</title>
<style>body{{font-family:system-ui,sans-serif;margin:2em}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:6px 10px;text-align:left;vertical-align:top}}
h1{{font-size:1.4em}}.pass{{color:#0a7d0a;font-weight:bold}}
.fail{{color:#c00;font-weight:bold}}
.chip{{display:inline-block}}</style></head>
<body><h1>Sentinel — live run</h1><p>{summary}</p>
<p>Kill switch: {kill_state}</p>
<table><tr><th>Candidate</th><th>Decision</th><th>Reason</th>
<th>Gate trail</th><th>Live facts</th></tr>{rows}</table>
<h2>Latest trace events</h2><ul>{events}</ul>
<p><small>Last updated {now} UTC · auto-refreshes every 5 seconds ·
read-only view of run/.</small></p>
</body></html>"""


def _send(handler: BaseHTTPRequestHandler, code: int, body: bytes,
          content_type: str) -> None:
    handler.send_response(code)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_server(run_dir: str, host: str = DEFAULT_HOST,
                port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    run_dir_abs = os.path.abspath(run_dir)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib naming
            path = urlparse(self.path).path
            if path == "/":
                _send(self, 200, render_page(run_dir_abs).encode("utf-8"),
                      "text/html; charset=utf-8")
            elif path == "/status.json":
                status = read_status(run_dir_abs) or {}
                _send(self, 200,
                      json.dumps(status, ensure_ascii=False).encode("utf-8"),
                      "application/json")
            elif path == "/health":
                _send(self, 200, b'{"ok": true}', "application/json")
            else:
                _send(self, 404, b"not found", "text/plain")

        def log_message(self, *args):  # keep the console quiet
            pass

    return ThreadingHTTPServer((host, port), Handler)


def serve(run_dir: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    server = make_server(run_dir, host, port)
    print(f"Sentinel dashboard at http://{host}:{port} (Ctrl+C to stop)")
    server.serve_forever()
