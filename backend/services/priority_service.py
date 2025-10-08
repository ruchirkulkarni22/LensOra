"""Derive ticket priority heuristically from text content.

Priority scale: P1 (critical), P2 (elevated), P3 (normal)
Heuristics are keyword based; can be replaced by ML later.
"""
from typing import Tuple
import re

P1_KEYWORDS = ["production down", "system down", "cannot login", "data loss", "critical", "outage"]
P2_KEYWORDS = ["slow", "performance", "failed", "error", "timeout", "degraded"]

def classify_priority(summary: str | None, description: str | None) -> Tuple[str, str]:
    text = f"{summary or ''}\n{description or ''}".lower()
    for kw in P1_KEYWORDS:
        if kw in text:
            return "P1", f"Matched critical keyword '{kw}'"
    for kw in P2_KEYWORDS:
        if kw in text:
            return "P2", f"Matched elevated keyword '{kw}'"
    # Numeric error codes maybe escalate to P2
    if re.search(r"error\s+\d{3,}", text):
        return "P2", "Found numeric error code"
    return "P3", "No priority keywords found"
