"""Kill switch + watchdog.

`sentinel stop` creates run/KILL. The run loop checks it before every
candidate and before every write, so a run halts within one tick. The
watchdog bounds total runtime: a run that exceeds max_seconds aborts.
"""

from __future__ import annotations

import os
import time

KILL_FILENAME = "KILL"


def kill_path(run_dir: str) -> str:
    return os.path.join(run_dir, KILL_FILENAME)


def arm(run_dir: str) -> str:
    """Create the KILL file. Returns its path."""
    os.makedirs(run_dir, exist_ok=True)
    path = kill_path(run_dir)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"stopped at {time.time()}\n")
    return path


def is_active(run_dir: str) -> bool:
    return os.path.exists(kill_path(run_dir))


def disarm(run_dir: str) -> None:
    path = kill_path(run_dir)
    if os.path.exists(path):
        os.remove(path)


class Watchdog:
    """Simple elapsed-time guard. Expired = the run must abort."""

    def __init__(self, max_seconds: float):
        self.max_seconds = max_seconds
        self.started = time.monotonic()

    @property
    def expired(self) -> bool:
        return (time.monotonic() - self.started) > self.max_seconds

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started
