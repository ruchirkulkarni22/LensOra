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
    module: str
    validation_status: str # 'complete' or 'incomplete'
    missing_fields: List[str] = field(default_factory=list)
    confidence: float = 0.0
    # --- FEATURE 1.1.3 ENHANCEMENT ---
    # This field will store the name of the model that successfully returned a verdict.
    llm_provider_model: Optional[str] = None

