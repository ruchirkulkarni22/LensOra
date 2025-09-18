# File: backend/workflows/shared.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TicketValidationInput:
    """Input for the validation workflow."""
    ticket_key: str

@dataclass
class TextBundle:
    """Result of the text fetching and bundling activity."""
    bundled_text: str
    # --- FLAWLESS FIX ---
    # Changed from reporter_name to reporter_id to reflect the JIRA API change.
    reporter_id: str

@dataclass
class LLMVerdict:
    """Structured result from the LLM validation activity."""
    detected_module: str
    validation_status: str # 'complete' or 'incomplete'
    missing_fields: Optional[List[str]] = None

