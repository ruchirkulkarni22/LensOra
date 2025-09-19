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

# --- FEATURE 1.1.5 ENHANCEMENT ---
# Define the structure of the incoming JIRA webhook payload.
# We only care about the 'issue' and its 'key'.
class JiraIssue(BaseModel):
    key: str

class JiraWebhookPayload(BaseModel):
    issue: JiraIssue
    # We use a 'catch-all' for other fields we don't need to parse.
    webhook_event: Optional[str] = Field(None, alias='webhookEvent')
    user: Optional[Dict[str, Any]] = None
    comment: Optional[Dict[str, Any]] = None

