# File: backend/api/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class KnowledgeUploadResponse(BaseModel):
    """
    Defines the response structure after a knowledge file upload attempt.
    """
    filename: str
    status: str
    message: str
    rows_processed: int
    rows_upserted: int
    errors: List[str] = []

# --- FEATURE 2.2 ENHANCEMENT ---
# New response model for the solved tickets upload endpoint.
class SolvedTicketsUploadResponse(BaseModel):
    filename: str
    status: str
    message: str
    rows_processed: int
    rows_upserted: int
    errors: List[str] = []


class JiraIssue(BaseModel):
    key: str

class JiraWebhookPayload(BaseModel):
    issue: JiraIssue
    webhook_event: Optional[str] = Field(None, alias='webhookEvent')
    user: Optional[Dict[str, Any]] = None
    comment: Optional[Dict[str, Any]] = None

