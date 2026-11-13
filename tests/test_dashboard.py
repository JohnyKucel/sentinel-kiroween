"""Tests for sentinel.dashboard — render + HTTP endpoints."""

import json
import threading
import urllib.error
import urllib.request

from sentinel.dashboard import make_server, render_page
from sentinel.killswitch import arm
from sentinel.report import write_report
from sentinel.trace import TraceWriter


def _seed_run(tmp_path):
    """A finished run dir: status.json + trace.jsonl + decisions."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    decisions = [{
        "name": "Clean Free Mint",
        "contract": "0x1111111111111111111111111111111111111111",
        "decision": "WOULD_MINT",
        "reason": "all gates passed",
        "live_error": "",
        "live_note": "sourcify=exact_match; total_minted=963 via totalMinted",
        "gates": [
            {"gate": "G2", "passed": True, "reason": "verified exact_match"},
            {"gate": "G3", "passed": True, "reason": "free phase open"},
        ],
        "note": "looks clean",
    }, {
        "name": "Sold Out Free",
        "contract": "0x2222222222222222222222222222222222222222",
        "decision": "SKIP",
        "reason": "free exhausted",
        "live_error": "",
        "live_note": "",
        "gates": [
            {"gate": "G2", "passed": True, "reason": "verified exact_match"},
            {"gate": "G3", "passed": False, "reason": "free exhausted"},
        ],
        "note": "",
    }]
    write_report(str(run_dir), "r-test", decisions, "2026-11-10T00:00:00+00:00",
                 aborted=False)
    trace = TraceWriter(str(run_dir / "trace.jsonl"), "r-test")
    trace.append("RUN_START", {"candidates_file": "fixtures/candidates.json"})
    trace.append("GATE", {"candidate": "Clean Free Mint", "gate": "G2",
                          "passed": True, "reason": "verified exact_match"})
    trace.append("DECISION", {"candidate": "Clean Free Mint",
                              "decision": "WOULD_MINT",
                              "reason": "all gates passed"})
    trace.append("RUN_END", {"candidates": 2, "would_mint": 1, "aborted": False})
    return str(run_dir)


def test_render_page_shows_decisions_gates_and_live_facts(tmp_path):
    page = render_page(_seed_run(tmp_path))
    assert "Clean Free Mint" in page
    assert "WOULD_MINT" in page
    assert "Sold Out Free" in page
    assert "SKIP" in page
    assert "G2 ✓" in page
    assert "G3 ✗" in page
    assert "sourcify=exact_match" in page
    assert "COMPLETED" in page
    assert "kill switch clear" in page
    assert "RUN_END" in page


def test_render_page_shows_aborted_and_kill_armed(tmp_path):
    run_dir = _seed_run(tmp_path)
    write_report(run_dir, "r-test2", [], "2026-11-10T00:00:00+00:00",
                 note="Run stopped by kill switch.", aborted=True)
    arm(run_dir)
    page = render_page(run_dir)
    assert "ABORTED" in page
    assert "KILL ARMED" in page
    assert "Run stopped by kill switch." in page


def test_render_page_no_run_yet(tmp_path):
    page = render_page(str(tmp_path / "empty"))
    assert "No run yet" in page


def test_render_page_escapes_hostile_text(tmp_path):
    run_dir = _seed_run(tmp_path)
    decisions = [{
        "name": "<script>alert(1)</script>", "contract": "0x00",
        "decision": "SKIP", "reason": "<b>bold</b>",
        "live_error": "", "live_note": "", "gates": [], "note": "",
    }]
    write_report(run_dir, "r-x", decisions, "2026-11-10T00:00:00+00:00")
    page = render_page(run_dir)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def _get(port, path):
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}{path}", timeout=5
    ) as resp:
        return resp.status, resp.read().decode("utf-8")


def test_http_endpoints(tmp_path):
    run_dir = _seed_run(tmp_path)
    server = make_server(run_dir, "127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _get(port, "/")
        assert status == 200
        assert "Sentinel" in body
        assert "Clean Free Mint" in body
        status, body = _get(port, "/status.json")
        assert status == 200
        assert json.loads(body)["run_id"] == "r-test"
        status, body = _get(port, "/health")
        assert status == 200
        assert json.loads(body) == {"ok": True}
        try:
            _get(port, "/nope")
            raise AssertionError("expected 404")
        except urllib.error.HTTPError as err:
            assert err.code == 404
    finally:
        server.shutdown()
        server.server_close()
