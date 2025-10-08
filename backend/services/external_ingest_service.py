# File: backend/services/external_ingest_service.py
"""Ingest external (or heuristic) documents, cache & embed them."""
from backend.services.db_service import db_service
from backend.db.models import ExternalDocs
from sqlalchemy import select
from datetime import datetime, timedelta
import hashlib
from typing import List, Dict
from backend.services.rag_service import rag_service

DEFAULT_TTL_DAYS = 7

class ExternalIngestService:
    def __init__(self):
        self.ttl_days = DEFAULT_TTL_DAYS

    def _upsert_doc(self, url: str, title: str, content_text: str) -> ExternalDocs:
        db = db_service.SessionLocal()
        try:
            content_hash = hashlib.sha256(content_text.encode()).hexdigest()
            stmt = select(ExternalDocs).where(ExternalDocs.url == url)
            existing = db.execute(stmt).scalar_one_or_none()
            now = datetime.utcnow()
            expires_at = now + timedelta(days=self.ttl_days)
            if existing:
                # Refresh if content changed
                if existing.content_hash != content_hash:
                    existing.content_text = content_text
                    existing.content_hash = content_hash
                    existing.title = title
                    existing.expires_at = expires_at
                    # regenerate embedding
                    rag_service._ensure_model()
                    existing.embedding = rag_service.embedding_model.encode(content_text)
                    db.commit()
                return existing
            # New row
            rag_service._ensure_model()
            embedding = rag_service.embedding_model.encode(content_text)
            doc = ExternalDocs(
                url=url,
                domain=url.split('/')[2] if '://' in url else None,
                title=title,
                content_text=content_text,
                content_hash=content_hash,
                embedding=embedding,
                expires_at=expires_at
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc
        finally:
            db.close()

    def ingest_results(self, raw_results: List[Dict]) -> List[Dict]:
        ingested = []
        for r in raw_results:
            # For heuristic mode, use snippet as stand-in content
            content_text = r.get('full_content') or r.get('snippet') or r.get('title') or 'No content.'
            doc = self._upsert_doc(r['url'], r.get('title', 'Untitled'), content_text)
            ingested.append({
                "source_type": "external",
                "url": doc.url,
                "title": doc.title,
                "resolution": doc.content_text[:1500],  # trimmed
                "summary": doc.title or doc.url,
                "ticket_key": None,
                "distance": None
            })
        return ingested

external_ingest_service = ExternalIngestService()
