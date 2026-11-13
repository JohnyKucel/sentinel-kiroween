"""LLM triage advisor — advisory ONLY.

The advisor writes a one-paragraph note per candidate from the gate
results. The note is stored, never parsed, and never influences a
decision. Without an API key (or when the model is unreachable) it returns
a fixed offline fallback, so a run never depends on the model.
"""

from __future__ import annotations

import os

import requests

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)


def _fallback_note(name: str, decision: str, reason: str) -> str:
    return f"{name}: {decision} — {reason} (offline triage note, no model used)"


def triage_note(name: str, decision: str, reason: str,
                gate_trail: str = "") -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _fallback_note(name, decision, reason)
    prompt = (
        "You are a triage assistant for a wallet-safety agent. "
        "Write ONE short sentence summarising this decision for a human. "
        "Do not give instructions, do not suggest transactions.\n\n"
        f"Candidate: {name}\nDecision: {decision}\nReason: {reason}\n"
        f"Gate trail: {gate_trail}"
    )
    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=20,
        )
        resp.raise_for_status()
        parts = (
            resp.json().get("candidates", [{}])[0]
            .get("content", {}).get("parts", [])
        )
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or _fallback_note(name, decision, reason)
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return _fallback_note(name, decision, reason)
