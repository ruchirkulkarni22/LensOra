"""Post-generation guardrails for LLM-produced solutions.

Validations performed:
1. Citation coverage: every non-empty paragraph should reference an internal or external source.
2. Source whitelist: all cited INT/WEB references must exist in provided lists.
3. Unsafe command filtering: strip or flag paragraphs containing dangerous patterns.
4. Field sanity: (placeholder) optionally ensure referenced mandatory fields actually exist (extension point).

If a solution fails hard rules it is either cleaned or marked invalid for regeneration.
"""
from __future__ import annotations
from typing import List, Dict, Tuple
import re
from backend.services.constants import (
    INTERNAL_MARKER, EXTERNAL_MARKER, MIN_CITATION_PER_PARAGRAPH,
    UNSAFE_COMMAND_PATTERNS
)

CITATION_PATTERN = re.compile(r"\[(INT|WEB):[^\]]+\]")

class ValidationIssue:
    def __init__(self, severity: str, message: str, paragraph_index: int | None = None):
        self.severity = severity
        self.message = message
        self.paragraph_index = paragraph_index

    def to_dict(self):
        return {
            "severity": self.severity,
            "message": self.message,
            "paragraph_index": self.paragraph_index
        }

def _extract_citations(text: str) -> List[str]:
    return CITATION_PATTERN.findall(text)  # returns list of tuples (INT|WEB, ...)

def validate_solution(
    solution_text: str,
    allowed_internal: List[str],
    allowed_external_indices: List[str]
) -> Tuple[str, List[ValidationIssue], bool]:
    """Validate and optionally mutate a solution text.

    Returns (possibly_cleaned_text, issues, is_valid)
    """
    paragraphs = [p.strip() for p in solution_text.split('\n')]
    issues: List[ValidationIssue] = []
    allowed_web_tags = {f"WEB:{idx}" for idx in allowed_external_indices}
    allowed_internal_tags = {f"INT:{k}" for k in allowed_internal}

    cleaned_paragraphs: List[str] = []
    for i, para in enumerate(paragraphs):
        if not para:
            cleaned_paragraphs.append(para)
            continue
        citations = CITATION_PATTERN.findall(para)
        # Flatten like [('INT','ABC-1')] => tokens we reconstruct from raw bracket content
        bracket_tokens = re.findall(r"\[(INT|WEB:[^\]]+)\]", para)
        # 1. Citation coverage
        if not bracket_tokens and len(para.split()) > 4:
            issues.append(ValidationIssue("warning", "Paragraph lacks citations", i))
        # 2. Check whitelist
        for raw in re.findall(r"\[(INT:[^\]]+|WEB:[^\]]+)\]", para):
            if raw.startswith("INT:") and raw not in allowed_internal_tags:
                issues.append(ValidationIssue("error", f"Unknown internal citation {raw}", i))
            if raw.startswith("WEB:") and raw not in allowed_web_tags:
                issues.append(ValidationIssue("error", f"Unknown external citation {raw}", i))
        # 3. Unsafe pattern filtering
        unsafe_hits = [pat for pat in UNSAFE_COMMAND_PATTERNS if pat.lower() in para.lower()]
        if unsafe_hits:
            issues.append(ValidationIssue("error", f"Unsafe command pattern(s): {', '.join(unsafe_hits)}", i))
            # Strip the paragraph entirely
            continue
        cleaned_paragraphs.append(para)

    is_valid = not any(iss.severity == "error" for iss in issues)
    cleaned_text = '\n'.join(cleaned_paragraphs)
    return cleaned_text, issues, is_valid
