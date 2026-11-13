"""Candidate sources — where mint candidates come from.

Two sources, both read-only and offline-safe:

1. Static scan list — a curated JSON file (``fixtures/scan-list.json``)
   produced by an earlier scan. Entries use the same shape as
   ``fixtures/candidates.json``.
2. Manual input — one-off candidates typed on the command line with
   ``--manual``, either as ``Name|0xContract`` (blank facts, meant to be
   enriched by ``--live-reads``) or as a full candidate JSON object.

All loaders are pure functions: they never touch the network and never
write. A bad entry in a scan list is skipped with a warning — it must
never kill the whole run. Candidates are deduplicated by contract
address (case-insensitive), first occurrence wins.
"""

from __future__ import annotations

import json
import re

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Facts for a candidate we know nothing about yet. Every gate that needs
# evidence fails closed on these, so a blank candidate can only SKIP
# until live reads (or explicit facts) supply evidence.
BLANK_FACTS = {
    "already_owned": False,
    "verified": False,
    "free_left": 0,
    "free_cap": 0,
    "total_minted": 0,
    "max_supply": 0,
    "quote_wei": 0,
    "needs_approval": False,
    "hidden_fee": False,
    "has_market": False,
    "deployer_track_record": False,
    "strong_demand": False,
    "preview_ok": False,
    "hostile_source": False,
}


def is_valid_address(address: object) -> bool:
    """True for a 0x-prefixed 40-hex-char address string."""
    return isinstance(address, str) and bool(_ADDRESS_RE.match(address))


def blank_facts() -> dict:
    """A fresh copy of the all-unknown facts dict."""
    return dict(BLANK_FACTS)


def _coerce_facts(raw: object) -> dict:
    """Merge user-supplied facts over the blank defaults.

    Unknown keys are dropped; booleans and ints are coerced so a JSON
    file with "free_left": "37" still behaves.
    """
    facts = blank_facts()
    if not isinstance(raw, dict):
        return facts
    for key, default in BLANK_FACTS.items():
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(default, bool):
            # bool("false") is True in Python, so a JSON string must be
            # parsed explicitly — otherwise "verified": "false" would
            # silently pass G2.
            if isinstance(value, str):
                facts[key] = value.strip().lower() in ("true", "1")
            else:
                facts[key] = bool(value)
        elif isinstance(default, int):
            try:
                facts[key] = int(value)
            except (TypeError, ValueError):
                pass
    return facts


def normalize_candidate(raw: object, source: str) -> dict | None:
    """Validate one raw candidate dict and fill in defaults.

    Returns the normalized candidate, or None (with the caller warned)
    when the entry is unusable: not a dict, no usable name, or an
    invalid contract address.
    """
    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    contract = raw.get("contract")
    if not isinstance(name, str) or not name.strip():
        return None
    if not is_valid_address(contract):
        return None
    try:
        chain_id = int(raw.get("chainId", 56))
    except (TypeError, ValueError):
        chain_id = 56
    sources = raw.get("sources")
    if not isinstance(sources, list):
        sources = []
    sources = [str(s) for s in sources]
    if source not in sources:
        sources.append(source)
    candidate: dict = {
        "name": name.strip(),
        "contract": contract,
        "chainId": chain_id,
        "facts": _coerce_facts(raw.get("facts")),
        "sources": sources,
    }
    for optional in ("freeFunction", "notes"):
        if raw.get(optional):
            candidate[optional] = raw[optional]
    return candidate


def parse_manual_candidate(spec: str) -> dict:
    """Parse one --manual spec into a candidate dict.

    Forms:
      "Name|0xContract"            — blank facts (use with --live-reads)
      "Name|0xContract|56"         — blank facts, explicit chain id
      '{"name": ..., "contract": ..., "facts": {...}}'
                                   — full candidate JSON object

    Raises ValueError on anything unparseable. A mistyped manual
    candidate fails fast: it is the operator's own input, not a scan
    file, so silence would hide the typo.
    """
    text = (spec or "").strip()
    if not text:
        raise ValueError("empty --manual spec")
    if text.startswith("{"):
        try:
            raw = json.loads(text)
        except ValueError as exc:
            raise ValueError(f"invalid --manual JSON: {exc}") from exc
        candidate = normalize_candidate(raw, "manual")
        if candidate is None:
            raise ValueError(
                "--manual JSON needs a non-empty name and a valid "
                "0x contract address"
            )
        return candidate
    parts = text.split("|")
    if len(parts) not in (2, 3):
        raise ValueError(
            "--manual must be 'Name|0xContract' or "
            "'Name|0xContract|chainId' (or a JSON object)"
        )
    name, contract = parts[0].strip(), parts[1].strip()
    chain_id = 56
    if len(parts) == 3:
        try:
            chain_id = int(parts[2].strip())
        except ValueError as exc:
            raise ValueError(f"--manual chainId must be an integer: {parts[2]!r}") from exc
    candidate = normalize_candidate(
        {"name": name, "contract": contract, "chainId": chain_id},
        "manual",
    )
    if candidate is None:
        raise ValueError(
            f"--manual needs a non-empty name and a valid 0x contract "
            f"address, got name={name!r} contract={contract!r}"
        )
    return candidate


def load_static_scan_list(path: str) -> tuple[list[dict], list[str]]:
    """Load a static scan-list JSON file.

    Returns (candidates, warnings). The file must contain a JSON list;
    each entry is normalized, invalid entries are skipped with a
    warning. Raises OSError when the file cannot be read at all — an
    explicitly requested list file must exist.
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    warnings: list[str] = []
    if not isinstance(data, list):
        return [], [f"{path}: scan list must contain a JSON list"]
    candidates: list[dict] = []
    for index, raw in enumerate(data):
        candidate = normalize_candidate(raw, "static-list")
        if candidate is None:
            warnings.append(f"{path}: entry {index} skipped (bad name/contract)")
            continue
        candidates.append(candidate)
    return candidates, warnings


def merge_candidates(*lists: list[dict]) -> list[dict]:
    """Concatenate candidate lists, deduplicated by contract address.

    Comparison is case-insensitive; the first occurrence wins and the
    input order is preserved.
    """
    merged: list[dict] = []
    seen: set[str] = set()
    for candidates in lists:
        for cand in candidates:
            key = str(cand.get("contract", "")).lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(cand)
    return merged


def collect_candidates(
    candidates_file: str | None,
    static_list_path: str | None,
    manual_specs: list[str] | None,
) -> tuple[list[dict], list[str]]:
    """Gather candidates from every configured source.

    Returns (merged_candidates, warnings). Raises ValueError when no
    candidate could be loaded from any source, and OSError when an
    explicitly requested --static-list file cannot be read.
    """
    warnings: list[str] = []
    file_candidates: list[dict] = []
    static_candidates: list[dict] = []
    manual_candidates: list[dict] = []

    if candidates_file:
        try:
            with open(candidates_file, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            warnings.append(f"{candidates_file}: cannot load ({exc})")
            data = None
        if isinstance(data, list):
            for index, raw in enumerate(data):
                candidate = normalize_candidate(raw, "candidates-file")
                if candidate is None:
                    warnings.append(
                        f"{candidates_file}: entry {index} skipped "
                        "(bad name/contract)"
                    )
                    continue
                file_candidates.append(candidate)
        elif data is not None:
            warnings.append(f"{candidates_file}: must contain a JSON list")

    if static_list_path:
        static_candidates, static_warnings = load_static_scan_list(
            static_list_path
        )
        warnings.extend(static_warnings)

    for spec in manual_specs or []:
        manual_candidates.append(parse_manual_candidate(spec))

    merged = merge_candidates(
        file_candidates, static_candidates, manual_candidates
    )
    if not merged:
        detail = "; ".join(warnings) if warnings else "no sources given"
        raise ValueError(f"no candidates loaded: {detail}")
    return merged, warnings
