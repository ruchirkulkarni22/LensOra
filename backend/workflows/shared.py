# File: backend/workflows/shared.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TicketValidationInput:
    """Input for the validation workflow."""
    ticket_key: str

# --- FLAWLESS UPGRADE ---
# We are replacing the simple TextBundle with a more powerful context object.
# This will carry not just the text, but also any images for multimodal analysis.
@dataclass
class TicketContext:
    """
    A comprehensive bundle of all information extracted from a JIRA ticket,
    ready for the LLM to analyze.
    """
    bundled_text: str
    reporter_id: Optional[str] = None
    # This is the key addition: a list to hold the raw bytes of any image attachments.
    image_attachments: List[bytes] = field(default_factory=list)

@dataclass
class LLMVerdict:
    """Structured result from the LLM validation activity."""
    detected_module: str
    validation_status: str # 'complete' or 'incomplete'
    missing_fields: List[str] = field(default_factory=list)

