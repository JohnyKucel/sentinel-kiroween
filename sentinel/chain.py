"""Read-only chain helpers: BSC public RPC + Sourcify verification.

No wallet connection, no signing, no transaction. Every function is a
read; failures return "unknown"/None instead of raising, so a flaky RPC
can never flip a gate to PASS by accident.
"""

from __future__ import annotations

import requests

DEFAULT_BSC_RPC = "https://bsc-dataseed1.binance.org"

BSC_RPC_ENDPOINTS = [
    "https://bsc-dataseed1.defibit.io",
    "https://bsc-dataseed2.defibit.io",
    "https://bsc-dataseed1.binance.org",
    "https://bsc.publicnode.com",
]

SOURCIFY_V2 = "https://sourcify.dev/server/v2/contract"
TIMEOUT = 15

# View-function selectors (keccak256 of the signature, first 4 bytes).
_SEL_TOTAL_SUPPLY = "18160ddd"   # totalSupply()
_SEL_TOTAL_MINTED = "a2309ff8"   # totalMinted()
_SEL_MAX_SUPPLY = "32cb6b0c"     # MAX_SUPPLY()
_SEL_MAX_SUPPLY_ALT = "d5abeb01"  # maxSupply()
_SEL_BALANCE_OF = "70a08231"     # balanceOf(address)


def _is_address(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 42
        and value.startswith("0x")
        and all(c in "0123456789abcdefABCDEF" for c in value[2:])
    )


def _decode_uint256(result: str | None) -> int | None:
    """Decode a 32-byte eth_call return value; None on revert/empty/garbage."""
    if not isinstance(result, str) or not result.startswith("0x"):
        return None
    body = result[2:]
    if len(body) != 64:
        return None
    try:
        return int(body, 16)
    except ValueError:
        return None


class BscRpc:
    """BSC JSON-RPC reader: requests.Session, multi-endpoint retry.

    One eth_call per invocation, no batching. The Session honours the
    process proxy environment (HTTP_PROXY/HTTPS_PROXY). Endpoints are
    tried in order until one answers; a total failure returns None.
    A per-contract revert (missing function) is a read failure, not an
    endpoint failure, so it returns None immediately.
    """

    def __init__(self, endpoints=None, session=None):
        self.endpoints = list(endpoints or BSC_RPC_ENDPOINTS)
        self.session = session or requests.Session()

    def eth_call(self, to: str, data: str) -> str | None:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": to, "data": data}, "latest"],
        }
        for url in self.endpoints:
            try:
                resp = self.session.post(url, json=payload, timeout=TIMEOUT)
                resp.raise_for_status()
                result = resp.json().get("result")
                if isinstance(result, str):
                    return result
                # JSON-RPC error object (e.g. reverted call): the
                # function is absent on this contract on every endpoint.
                return None
            except (requests.RequestException, ValueError):
                continue
        return None

    def call_view(self, contract: str, selector: str, args=()) -> int | None:
        """Call a no-arg (or uint256-arg) view function, decode uint256."""
        if not _is_address(contract):
            return None
        data = "0x" + selector
        for arg in args:
            data += format(int(arg), "064x")
        return _decode_uint256(self.eth_call(contract, data))

    def total_supply(self, contract: str) -> int | None:
        return self.call_view(contract, _SEL_TOTAL_SUPPLY)

    def total_minted(self, contract: str) -> int | None:
        return self.call_view(contract, _SEL_TOTAL_MINTED)

    def max_supply(self, contract: str) -> int | None:
        value = self.call_view(contract, _SEL_MAX_SUPPLY)
        if value is None:
            value = self.call_view(contract, _SEL_MAX_SUPPLY_ALT)
        return value

    def balance_of(self, contract: str, wallet: str) -> int | None:
        if not _is_address(wallet):
            return None
        return self.call_view(contract, _SEL_BALANCE_OF, (int(wallet, 16),))


def default_rpc() -> BscRpc:
    return BscRpc()


def balance_of(contract: str, wallet: str, rpc: BscRpc | None = None) -> int | None:
    """ERC-721/ERC-20 balanceOf. Returns None when the read fails."""
    return (rpc or default_rpc()).balance_of(contract, wallet)


def sourcify_status(contract: str, chain_id: int = 56, session=None) -> str:
    """Return 'exact_match' | 'match' | 'partial' | 'unverified' | 'unknown'.

    Sourcify v2 answers 200 for a verified contract (top-level `match`
    field); 404 means unverified. NOTE: `?fields=stdJson` is rejected
    with HTTP 400 by the v2 API — `fields=abi` is the working query.
    """
    if not _is_address(contract):
        return "unknown"
    sess = session or requests.Session()
    try:
        resp = sess.get(
            f"{SOURCIFY_V2}/{chain_id}/{contract}",
            params={"fields": "abi"},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            match = resp.json().get("match")
            return match if match in ("exact_match", "match", "partial") else "match"
        if resp.status_code == 404:
            return "unverified"
        return "unknown"
    except (requests.RequestException, ValueError):
        return "unknown"


def is_verified(contract: str, chain_id: int = 56, session=None) -> bool:
    return sourcify_status(contract, chain_id, session=session) in (
        "exact_match",
        "match",
    )
