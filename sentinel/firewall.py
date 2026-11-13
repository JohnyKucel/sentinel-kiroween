"""Hostile-input firewall.

All outside content (project pages, social posts, API responses) is
untrusted DATA, never instructions. This module screens text for
instruction-injection patterns and quarantines matches. Nothing the
firewall flags can ever reach a gate, an executor, or the LLM as a command.
"""

from __future__ import annotations

import re

# Patterns that indicate an instruction smuggled into outside content.
HOSTILE_PATTERNS = [
    re.compile(r"ignore (all |any )?(previous|prior|above) instructions?", re.I),
    re.compile(r"disregard (all )?(previous|prior|safety|above).*", re.I),
    re.compile(r"you are now (in |on )?(live|admin|developer|god|unrestricted)", re.I),
    re.compile(r"(mint|transfer|send|approve|execute|sign|swap|claim)[^\n]{0,40}\bnow\b", re.I),
    re.compile(r"new instructions?:", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"do not tell (the )?user", re.I),
    re.compile(r"override (safety|the)? ?(rules|checks|gates)?", re.I),
    re.compile(r"act as (if )?(you )?(have|are)", re.I),
    re.compile(r"repeat after me", re.I),
]


def screen(text: str):
    """Return (blocked, matched_patterns). Benign text returns (False, [])."""
    if not text:
        return False, []
    matched = [p.pattern for p in HOSTILE_PATTERNS if p.search(text)]
    return bool(matched), matched


def quarantine(text: str, source: str = "unknown") -> dict:
    """Record a quarantined input. The text itself is kept for audit, but
    it is never executed, never forwarded to the LLM as instruction, and
    never shown as a command."""
    blocked, matched = screen(text)
    return {
        "source": source,
        "blocked": blocked,
        "matched_patterns": matched,
        "excerpt": text[:200],
    }
