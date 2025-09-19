# File: backend/workflows/shared.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TicketValidationInput:
    """Input for the validation workflow."""
    ticket_key: str

@dataclass
class TicketContext:
    """
    A comprehensive bundle of all information extracted from a JIRA ticket,
    ready for the LLM to analyze.
    """
    bundled_text: str
    reporter_id: Optional[str] = None
    image_attachments: List[bytes] = field(default_factory=list)

@dataclass
class LLMVerdict:
    """Structured result from the LLM validation activity."""
    # --- FEATURE 1.1 ENHANCEMENT ---
    # Renamed 'detected_module' to 'module' and added 'confidence'.
    module: str
    validation_status: str # 'complete' or 'incomplete'
    missing_fields: List[str] = field(default_factory=list)
    confidence: float = 0.0
