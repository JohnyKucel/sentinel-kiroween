"""Unit tests for the append-only trace + verifier."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel.trace import TraceWriter, read_trace, verify_trace  # noqa: E402


def _write_good_trace(path):
    tw = TraceWriter(path, "r-test")
    tw.append("RUN_START", {})
    tw.append("GATE", {"candidate": "A", "gate": "G0", "passed": True})
    tw.append("DECISION", {"candidate": "A", "decision": "WOULD_MINT"})
    tw.append("RUN_END", {})
    return tw


def test_write_and_read_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "trace.jsonl")
        _write_good_trace(path)
        records = read_trace(path)
        assert len(records) == 4
        assert [r["seq"] for r in records] == [1, 2, 3, 4]
        assert records[0]["run_id"] == "r-test"


def test_verify_passes_on_good_trace():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "trace.jsonl")
        _write_good_trace(path)
        ok, errors = verify_trace(path)
        assert ok, errors


def test_verify_fails_on_tampered_trace():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "trace.jsonl")
        _write_good_trace(path)
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        # Remove the GATE line: the DECISION loses its gate trail.
        Path(path).write_text("\n".join(lines[:1] + lines[2:]) + "\n",
                              encoding="utf-8")
        ok, errors = verify_trace(path)
        assert not ok
        assert errors


def test_verify_fails_on_empty_trace():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "trace.jsonl")
        Path(path).write_text("", encoding="utf-8")
        ok, errors = verify_trace(path)
        assert not ok
