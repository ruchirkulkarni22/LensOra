# File: backend/services/rag_service.py
from sqlalchemy.dialects.postgresql import insert
from sentence_transformers import SentenceTransformer
import pandas as pd
from .db_service import db_service
from backend.db.models import SolvedJiraTickets

class RAGService:
    """
    Handles Retrieval-Augmented Generation tasks, including processing,
    embedding, and storing knowledge from solved JIRA tickets.
    """
    def __init__(self):
        # Load a powerful, lightweight model for generating sentence embeddings.
        # The first time this runs, it will download the model.
        print("Loading sentence embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Sentence embedding model loaded.")

    def upsert_solved_tickets(self, df: pd.DataFrame) -> dict:
        """
        Processes a DataFrame of solved tickets, generates embeddings,
        and upserts them into the database.
        """
        db = db_service.SessionLocal()
        try:
            tickets_to_upsert = []
            
            # Prepare all tickets for processing
            for _, row in df.iterrows():
                # Combine the most important text fields for a rich embedding
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
                    "text_for_embedding": combined_text # Temporary field
                }
                tickets_to_upsert.append(ticket_data)

            if not tickets_to_upsert:
                return {"rows_upserted": 0, "errors": []}

            # Generate embeddings in a single, efficient batch
            texts = [ticket['text_for_embedding'] for ticket in tickets_to_upsert]
            print(f"Generating embeddings for {len(texts)} tickets...")
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            # Add embeddings to our ticket data
            for i, ticket in enumerate(tickets_to_upsert):
                ticket['embedding'] = embeddings[i]
                del ticket['text_for_embedding'] # Clean up temporary field

            # Perform a bulk "upsert" operation
            stmt = insert(SolvedJiraTickets).values(tickets_to_upsert)
            
            # On conflict (ticket_key already exists), update the existing record
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
