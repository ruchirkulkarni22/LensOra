# File: backend/api/schemas.py
from pydantic import BaseModel
from typing import List, Optional

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
