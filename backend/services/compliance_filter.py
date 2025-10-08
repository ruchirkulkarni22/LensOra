"""Compliance filter to scrub sensitive tokens before LLM usage.

This performs fast regex-based redactions for:
 - Emails
 - Potential API keys (patterns like sk-... or long mixed strings)
 - Long hex / base64-like blobs
 - Potential JWTs (three dot-separated base64url segments)
"""
import re
from typing import Tuple

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
API_KEY_RE = re.compile(r"\b(?:sk|api|key)[_-][A-Za-z0-9]{8,}\b", re.IGNORECASE)
HEX_LONG_RE = re.compile(r"\b[a-f0-9]{32,}\b", re.IGNORECASE)
BASE64ISH_RE = re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")
JWT_RE = re.compile(r"\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b")

REDACTION_TOKEN = "[REDACTED]"

PATTERNS = [EMAIL_RE, API_KEY_RE, HEX_LONG_RE, BASE64ISH_RE, JWT_RE]

def scrub(text: str) -> Tuple[str, int]:
    """Return redacted text and number of redactions applied."""
    redactions = 0
    for pat in PATTERNS:
        def _sub(match):
            nonlocal redactions
            redactions += 1
            return REDACTION_TOKEN
        text = pat.sub(_sub, text)
    return text, redactions
