"""Live executor — the ONLY module allowed to write on-chain.

It refuses by default. Live execution requires ALL of:
  1. live=True (the --live flag),
  2. a per-run human approval token matching SENTINEL_APPROVAL_TOKEN,
  3. SENTINEL_LIVE=1 in the environment,
  4. kill switch clear,
  5. every gate PASS,
  6. value == 0 (hard limit, SENTINEL_MAX_VALUE_WEI).

The on-chain adapter (baw contract-call) is a build-window task; until it
lands, this module validates the authorisation and then raises
NotImplementedError instead of ever touching a wallet. A skeleton that
cannot accidentally spend is the point.
"""

from __future__ import annotations

import os


class LiveRefused(Exception):
    """Raised whenever live execution is not fully authorised."""


def check_live_authorised(*, live: bool, approval_token: str,
                          kill_active: bool, gates_passed: bool,
                          value_wei: int) -> None:
    if not live:
        raise LiveRefused("live mode not requested (--live missing)")
    if os.environ.get("SENTINEL_LIVE") != "1":
        raise LiveRefused("SENTINEL_LIVE != 1 in environment")
    expected = os.environ.get("SENTINEL_APPROVAL_TOKEN", "")
    if not expected or approval_token != expected:
        raise LiveRefused("missing or invalid per-run human approval token")
    if kill_active:
        raise LiveRefused("kill switch active")
    if not gates_passed:
        raise LiveRefused("not all gates passed")
    max_value = int(os.environ.get("SENTINEL_MAX_VALUE_WEI", "0"))
    if value_wei != 0 or max_value != 0:
        raise LiveRefused(f"value must be 0 (got {value_wei} wei)")


def execute_live(*, live: bool, approval_token: str, kill_active: bool,
                 gates_passed: bool, value_wei: int, contract: str) -> dict:
    """Validate authorisation, then hand off to the wallet adapter.

    The adapter is not part of this skeleton: it must call a real preview
    first and only execute on a clean preview. Until then, authorisation
    passes but execution is refused — loudly, not silently.
    """
    check_live_authorised(
        live=live, approval_token=approval_token, kill_active=kill_active,
        gates_passed=gates_passed, value_wei=value_wei,
    )
    raise NotImplementedError(
        "live wallet adapter not installed (see SAFETY.md): authorisation "
        f"passed for {contract}, but no transaction was attempted"
    )
