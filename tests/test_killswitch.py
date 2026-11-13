"""Unit tests for the kill switch + watchdog."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel import killswitch  # noqa: E402


def test_arm_and_is_active():
    with tempfile.TemporaryDirectory() as tmp:
        assert not killswitch.is_active(tmp)
        killswitch.arm(tmp)
        assert killswitch.is_active(tmp)
        killswitch.disarm(tmp)
        assert not killswitch.is_active(tmp)


def test_watchdog_not_expired_then_expired():
    dog = killswitch.Watchdog(max_seconds=1000)
    assert not dog.expired
    dog2 = killswitch.Watchdog(max_seconds=0)
    assert dog2.expired
