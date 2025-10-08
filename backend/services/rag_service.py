# File: backend/services/rag_service.py
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, text
from sentence_transformers import SentenceTransformer
import pandas as pd
from .db_service import db_service
from backend.db.models import SolvedJiraTickets
from typing import List, Dict

class RAGService:
    """
    Handles Retrieval-Augmented Generation tasks, including processing,
    embedding, storing, and retrieving knowledge from solved JIRA tickets.
    """
    def __init__(self):
        # Defer heavy model load until first use to speed API startup (prevents frontend proxy 502 windows)
        self.embedding_model = None
        self._model_name = 'all-MiniLM-L6-v2'
        print("RAGService initialized. Embedding model will be loaded lazily on first request.")

    def _ensure_model(self):
        if self.embedding_model is None:
            print(f"Loading sentence embedding model '{self._model_name}' (lazy)...")
            self.embedding_model = SentenceTransformer(self._model_name)
            print("Sentence embedding model loaded.")

    # --- FEATURE 2.3 ENHANCEMENT ---
    # New method to find the most relevant past solutions.
    def find_similar_solutions(self, query_text: str, top_k: int = 3, max_distance: float | None = 1.2) -> List[Dict]:
        """
        Generates an embedding for the query text and finds the 'top_k' most
        similar tickets from the database using vector similarity search.
        """
        db = db_service.SessionLocal()
        try:
            print(f"Generating embedding for query: '{query_text[:100]}...'")
            self._ensure_model()
            query_embedding = self.embedding_model.encode(query_text)

            # pgvector provides the L2 distance operator (<->) for similarity search.
            # We find the tickets with the smallest distance to our query embedding.
            stmt = (
                select(
                    SolvedJiraTickets.ticket_key,
                    SolvedJiraTickets.summary,
                    SolvedJiraTickets.resolution,
                    SolvedJiraTickets.embedding.l2_distance(query_embedding).label('distance')
                )
                .order_by(text('distance'))
                .limit(top_k)
            )

            results = db.execute(stmt).fetchall()

            similar_tickets: List[Dict] = []
            for row in results:
                # Filter out semantically far tickets if threshold provided
                if max_distance is not None and row.distance is not None and row.distance > max_distance:
                    continue
                similar_tickets.append({
                    "ticket_key": row.ticket_key,
                    "summary": row.summary,
                    "resolution": row.resolution,
                    "distance": row.distance
                })
            print(f"Found {len(similar_tickets)} similar tickets in the database.")
            return similar_tickets

        finally:
            db.close()

    def find_potential_duplicate(self, query_text: str, threshold: float = 0.35) -> dict | None:
        """Return a potential duplicate solved ticket if distance below threshold."""
        db = db_service.SessionLocal()
        try:
            self._ensure_model()
            emb = self.embedding_model.encode(query_text)
            stmt = (
                select(
                    SolvedJiraTickets.ticket_key,
                    SolvedJiraTickets.summary,
                    SolvedJiraTickets.resolution,
                    SolvedJiraTickets.embedding.l2_distance(emb).label('distance')
                )
                .order_by(text('distance'))
                .limit(1)
            )
            row = db.execute(stmt).first()
            if row and row.distance is not None and row.distance < threshold:
                return {
                    "ticket_key": row.ticket_key,
                    "summary": row.summary,
                    "resolution": row.resolution,
                    "distance": row.distance
                }
            return None
        finally:
            db.close()

    def upsert_solved_tickets(self, df: pd.DataFrame) -> dict:
        """
        Processes a DataFrame of solved tickets, generates embeddings,
        and upserts them into the database.
        """
        db = db_service.SessionLocal()
        try:
            tickets_to_upsert = []
            
            for _, row in df.iterrows():
                combined_text = (
                    f"Ticket: {row['ticket_key']}\n"
                    f"Summary: {row['summary']}\n"
                    f"Description: {row.get('description', '')}\n"
                    f"Resolution: {row['resolution']}"
                )
                
                ticket_data = {
                    "ticket_key": row['ticket_key'],
                    "summary": row['summary'],
                    "description": row.get('description'),
                    "resolution": row['resolution'],
                    "text_for_embedding": combined_text
                }
                tickets_to_upsert.append(ticket_data)

            if not tickets_to_upsert:
                return {"rows_upserted": 0, "errors": []}

            texts = [ticket['text_for_embedding'] for ticket in tickets_to_upsert]
            print(f"Generating embeddings for {len(texts)} tickets...")
            self._ensure_model()
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            for i, ticket in enumerate(tickets_to_upsert):
                ticket['embedding'] = embeddings[i]
                del ticket['text_for_embedding']

            stmt = insert(SolvedJiraTickets).values(tickets_to_upsert)
            
            update_stmt = stmt.on_conflict_do_update(
                index_elements=['ticket_key'],
                set_={
                    'summary': stmt.excluded.summary,
                    'description': stmt.excluded.description,
                    'resolution': stmt.excluded.resolution,
                    'embedding': stmt.excluded.embedding,
                }
            )
            
            db.execute(update_stmt)
            db.commit()
            
            return {"rows_upserted": len(tickets_to_upsert), "errors": []}

        except Exception as e:
            db.rollback()
            print(f"Error in RAG service: {e}")
            return {"rows_upserted": 0, "errors": [str(e)]}
        finally:
            db.close()

rag_service = RAGService()

