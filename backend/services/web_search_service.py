"""Web search abstraction with Tavily integration + heuristic fallback."""
import os, hashlib, re, time, requests
from typing import List, Dict
from backend.config import settings
from backend.services.db_service import db_service
from backend.db.models import ExternalSearchAudit
from sqlalchemy import insert

class WebSearchService:
    def __init__(self):
        self.enabled = os.getenv("ENABLE_WEB_SEARCH", "1") == "1"
        self.provider = "tavily" if settings.TAVILY_API_KEY else "heuristic"

    def _audit(self, query: str, norm_hash: str, provider: str, count: int):
        try:
            db = db_service.SessionLocal()
            stmt = insert(ExternalSearchAudit).values(
                query_text=query,
                normalized_query_hash=norm_hash,
                provider_used=provider,
                result_count=count
            )
            db.execute(stmt)
            db.commit()
        except Exception as e:
            print(f"Audit insert failed: {e}")
        finally:
            try:
                db.close()
            except Exception:
                pass

    def normalize_query(self, text: str) -> str:
        # Basic normalization for audit hashing
        return re.sub(r"\s+", " ", text.strip().lower())[:500]

    def search(self, ticket_text: str, max_results: int = 5) -> List[Dict]:
        if not self.enabled:
            return []
        query = ticket_text.strip()[:8000]
        normalized = self.normalize_query(query)
        norm_hash = hashlib.sha256(normalized.encode()).hexdigest()
        # Tavily path
        if self.provider == "tavily":
            try:
                start = time.time()
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "advanced"
                    }, timeout=25
                )
                resp.raise_for_status()
                data = resp.json()
                raw = data.get("results", [])
                shaped = [{
                    "url": r.get("url"),
                    "title": r.get("title") or "Untitled",
                    "snippet": (r.get("content") or "")[:600]
                } for r in raw[:max_results]]
                self._audit(query, norm_hash, self.provider, len(shaped))
                print(f"Tavily returned {len(shaped)} results")
                if shaped:
                    return shaped
            except Exception as e:
                print(f"Tavily failure: {e}; falling back to heuristic")
        # Heuristic fallback
        lines = [l.strip() for l in ticket_text.splitlines() if l.strip()]
        ranked = sorted(lines, key=len, reverse=True)[:max_results]
        faux = []
        for i, line in enumerate(ranked):
            h = hashlib.sha256(line.encode()).hexdigest()
            faux.append({
                "url": f"https://assistiq.local/faux/{h[:10]}",
                "title": f"Heuristic Context {i+1}",
                "snippet": line[:180]
            })
        self._audit(query, norm_hash, "heuristic", len(faux))
        return faux

web_search_service = WebSearchService()
