# File: backend/services/db_service.py
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.dialects.postgresql import insert
from backend.config import settings
from backend.db.models import (
    ModulesTaxonomy,
    MandatoryFieldTemplates,
    ValidationsLog,
    SolvedJiraTickets,
    ResolutionLog,
    Base
)
from backend.workflows.shared import LLMVerdict, SynthesizedSolution
import pandas as pd
from typing import List, Dict, Optional

class DatabaseService:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        # Ensure all declared ORM tables exist (non-destructive for existing schemas)
        try:
            Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            print(f"[Schema] Base metadata create_all failed (continuing): {e}")
        self._ensure_schema_extensions()

    def _ensure_schema_extensions(self):
        """Runtime DDL adjustments for priority & drafts (idempotent)."""
        with self.engine.connect() as conn:
            try:
                res = conn.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name='validations_log' AND column_name='priority'"))
                if res.first() is None:
                    conn.execute(text("ALTER TABLE validations_log ADD COLUMN priority VARCHAR(4)"))
            except Exception as e:
                print(f"[Schema] Priority column check failed: {e}")
            try:
                res = conn.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name='validations_log' AND column_name='duplicate_of'"))
                if res.first() is None:
                    conn.execute(text("ALTER TABLE validations_log ADD COLUMN duplicate_of VARCHAR"))
            except Exception as e:
                print(f"[Schema] duplicate_of column check failed: {e}")
            try:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS resolution_drafts (
                        id SERIAL PRIMARY KEY,
                        ticket_key VARCHAR NOT NULL,
                        draft_text TEXT NOT NULL,
                        author VARCHAR NULL,
                        created_at TIMESTAMP DEFAULT now(),
                        updated_at TIMESTAMP DEFAULT now()
                    )
                    """
                ))
            except Exception as e:
                print(f"[Schema] Drafts table create failed: {e}")
            # Timeline / events table
            try:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS ticket_events (
                        id SERIAL PRIMARY KEY,
                        ticket_key VARCHAR NOT NULL,
                        event_type VARCHAR NOT NULL,
                        message TEXT,
                        created_at TIMESTAMP DEFAULT now()
                    )
                    """
                ))
            except Exception as e:
                print(f"[Schema] Events table create failed: {e}")

    def get_all_modules_with_fields(self) -> dict:
        db = self.SessionLocal()
        try:
            stmt = select(ModulesTaxonomy).options(joinedload(ModulesTaxonomy.mandatory_fields))
            modules = db.execute(stmt).scalars().unique().all()
            knowledge_base = {}
            for module in modules:
                knowledge_base[module.module_name] = {
                    "description": module.description,
                    "mandatory_fields": [field.field_name for field in module.mandatory_fields]
                }
            return knowledge_base
        finally:
            db.close()

    def log_validation_result(self, ticket_key: str, verdict: LLMVerdict):
        db = self.SessionLocal()
        try:
            stmt = insert(ValidationsLog).values(
                ticket_key=ticket_key,
                module=verdict.module,
                status=verdict.validation_status,
                missing_fields=verdict.missing_fields,
                confidence=verdict.confidence,
                llm_provider_model=verdict.llm_provider_model,
                priority=getattr(verdict, 'priority', None),
                duplicate_of=getattr(verdict, 'duplicate_of', None)
            )
            # NOTE: SQLAlchemy's PostgreSQL dialect expects 'set_' param (not 'set')
            update_stmt = stmt.on_conflict_do_update(
                index_elements=['ticket_key'],
                set_={
                    'module': stmt.excluded.module,
                    'status': stmt.excluded.status,
                    'missing_fields': stmt.excluded.missing_fields,
                    'confidence': stmt.excluded.confidence,
                    'llm_provider_model': stmt.excluded.llm_provider_model,
                    'priority': stmt.excluded.priority,
                    'duplicate_of': stmt.excluded.duplicate_of,
                    'validated_at': text('now()')
                }
            )
            db.execute(update_stmt)
            db.commit()
            # Timeline event
            try:
                ev_type = 'validated_complete' if verdict.validation_status == 'complete' else 'validated_incomplete'
                self.add_event(ticket_key, ev_type, f"Validation status={verdict.validation_status}; missing={len(verdict.missing_fields)}")
            except Exception as _e:
                print(f"[Timeline] Failed to add validation event: {_e}")
        finally:
            db.close()
    def upsert_knowledge_from_dataframe(self, df: pd.DataFrame) -> dict:
        db = self.SessionLocal()
        processed_count = 0
        upserted_count = 0
        try:
            for _, row in df.iterrows():
                processed_count += 1
                module_name = row['module_name']
                field_name = row['field_name']
                module_stmt = select(ModulesTaxonomy).where(ModulesTaxonomy.module_name == module_name)
                module = db.execute(module_stmt).scalar_one_or_none()
                if not module:
                    module = ModulesTaxonomy(module_name=module_name, description=f"Module for {module_name}")
                    db.add(module)
                    db.commit()
                    db.refresh(module)
                    upserted_count += 1
                field_stmt = select(MandatoryFieldTemplates).where(
                    MandatoryFieldTemplates.module_id == module.id,
                    MandatoryFieldTemplates.field_name == field_name
                )
                field = db.execute(field_stmt).scalar_one_or_none()
                if not field:
                    new_field = MandatoryFieldTemplates(module_id=module.id, field_name=field_name)
                    db.add(new_field)
                    upserted_count += 1
            db.commit()
            return {"rows_processed": processed_count, "rows_upserted": upserted_count, "errors": []}
        except Exception as e:
            db.rollback()
            return {"rows_processed": 0, "rows_upserted": 0, "errors": [str(e)]}
        finally:
            db.close()

    def log_resolution(self, ticket_key: str, solution: SynthesizedSolution):
        db = self.SessionLocal()
        try:
            log_entry = ResolutionLog(
                ticket_key=ticket_key,
                solution_posted=solution.solution_text,
                llm_provider_model=solution.llm_provider_model,
                sources_json=solution.sources,
                reasoning_text=solution.reasoning
            )
            db.add(log_entry)
            db.commit()
        finally:
            db.close()

    def get_last_known_ticket_statuses(self, ticket_keys: List[str]) -> Dict[str, str]:
        if not ticket_keys:
            return {}
        
        db = self.SessionLocal()
        try:
            stmt = select(ValidationsLog.ticket_key, ValidationsLog.status).where(ValidationsLog.ticket_key.in_(ticket_keys))
            results = db.execute(stmt).all()
            return {row.ticket_key: row.status for row in results}
        finally:
            db.close()
    
    def get_last_validation_timestamp(self, ticket_key: str) -> Optional[str]:
        db = self.SessionLocal()
        try:
            stmt = select(ValidationsLog.validated_at).where(ValidationsLog.ticket_key == ticket_key)
            result = db.execute(stmt).scalar_one_or_none()
            if result:
                return result.isoformat()
            return None
        finally:
            db.close()
    
    def get_complete_tickets(self) -> List[Dict]:
        db = self.SessionLocal()
        try:
            stmt = select(ValidationsLog).where(ValidationsLog.status == "complete").order_by(ValidationsLog.validated_at.desc())
            results = db.execute(stmt).scalars().all()
            data = []
            for log in results:
                escalate = (log.confidence is not None and log.confidence < 0.2)
                data.append({
                    "ticket_key": log.ticket_key,
                    "module": log.module,
                    "confidence": log.confidence,
                    "priority": getattr(log, 'priority', None),
                    "duplicate_of": getattr(log, 'duplicate_of', None),
                    "escalate": escalate,
                    "validated_at": log.validated_at.isoformat() if log.validated_at else None
                })
            return data
        finally:
            db.close()

    # --- NEW METHOD FOR UI ENHANCEMENT ---
    def get_incomplete_tickets(self) -> List[Dict]:
        """
        Retrieves all tickets that have been validated as 'incomplete' for the UI.
        """
        db = self.SessionLocal()
        try:
            stmt = select(ValidationsLog).where(ValidationsLog.status == "incomplete").order_by(ValidationsLog.validated_at.desc())
            results = db.execute(stmt).scalars().all()
            return [{
                "ticket_key": log.ticket_key,
                "module": log.module,
                "missing_fields": log.missing_fields,
                "priority": getattr(log, 'priority', None),
                "duplicate_of": getattr(log, 'duplicate_of', None),
                "validated_at": log.validated_at.isoformat() if log.validated_at else None
            } for log in results]
        finally:
            db.close()

    def save_draft(self, ticket_key: str, draft_text: str, author: str | None = None) -> Dict:
        db = self.SessionLocal()
        try:
            result = db.execute(text(
                """INSERT INTO resolution_drafts (ticket_key, draft_text, author) VALUES (:t,:d,:a) RETURNING id, ticket_key, draft_text, author, created_at, updated_at"""
            ), {"t": ticket_key, "d": draft_text, "a": author})
            row = result.first()
            db.commit()
            return dict(row._mapping)
        finally:
            db.close()

    def list_drafts(self, ticket_key: str) -> List[Dict]:
        db = self.SessionLocal()
        try:
            res = db.execute(text(
                "SELECT id, ticket_key, draft_text, author, created_at, updated_at FROM resolution_drafts WHERE ticket_key=:k ORDER BY updated_at DESC"
            ), {"k": ticket_key})
            return [dict(r._mapping) for r in res.fetchall()]
        finally:
            db.close()

    def count_incomplete(self) -> int:
        db = self.SessionLocal()
        try:
            res = db.execute(text("SELECT COUNT(*) FROM validations_log WHERE status='incomplete'"))
            return res.scalar() or 0
        finally:
            db.close()

    # --- Impact Counters & Timeline ---
    def get_impact_counters(self) -> Dict:
        db = self.SessionLocal()
        try:
            total_validations = db.execute(text("SELECT COUNT(*) FROM validations_log" )).scalar() or 0
            duplicates_avoided = db.execute(text("SELECT COUNT(*) FROM validations_log WHERE duplicate_of IS NOT NULL" )).scalar() or 0
            solutions_posted = db.execute(text("SELECT COUNT(*) FROM resolution_log" )).scalar() or 0
            drafts_created = db.execute(text("SELECT COUNT(*) FROM resolution_drafts" )).scalar() or 0
            engineer_hours_saved = round(duplicates_avoided * 0.5, 2)  # 30 mins per duplicate
            return {
                "tickets_triaged": total_validations,
                "duplicates_avoided": duplicates_avoided,
                "engineer_hours_saved": engineer_hours_saved,
                "solutions_posted": solutions_posted,
                "drafts_created": drafts_created
            }
        finally:
            db.close()

    def add_event(self, ticket_key: str, event_type: str, message: str):
        db = self.SessionLocal()
        try:
            db.execute(text("INSERT INTO ticket_events (ticket_key, event_type, message) VALUES (:k,:e,:m)"), {"k": ticket_key, "e": event_type, "m": message})
            db.commit()
        finally:
            db.close()

    def get_timeline(self, ticket_key: str) -> List[Dict]:
        db = self.SessionLocal()
        try:
            res = db.execute(text("SELECT event_type, message, created_at FROM ticket_events WHERE ticket_key=:k ORDER BY created_at ASC"), {"k": ticket_key})
            return [{
                "event_type": r.event_type,
                "message": r.message,
                "timestamp": r.created_at.isoformat() if r.created_at else None
            } for r in res.fetchall()]
        finally:
            db.close()

    def get_validation_record(self, ticket_key: str) -> Optional[Dict]:
        db = self.SessionLocal()
        try:
            stmt = select(ValidationsLog).where(ValidationsLog.ticket_key == ticket_key)
            rec = db.execute(stmt).scalar_one_or_none()
            if not rec:
                return None
            return {
                'ticket_key': rec.ticket_key,
                'status': rec.status,
                'duplicate_of': getattr(rec, 'duplicate_of', None),
                'priority': getattr(rec, 'priority', None),
                'confidence': rec.confidence
            }
        finally:
            db.close()

    def get_solved_ticket(self, ticket_key: str) -> Optional[Dict]:
        db = self.SessionLocal()
        try:
            stmt = select(SolvedJiraTickets).where(SolvedJiraTickets.ticket_key == ticket_key)
            rec = db.execute(stmt).scalar_one_or_none()
            if not rec:
                return None
            return {
                'ticket_key': rec.ticket_key,
                'summary': rec.summary,
                'resolution': rec.resolution
            }
        finally:
            db.close()


db_service = DatabaseService()
