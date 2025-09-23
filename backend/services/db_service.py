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
    ResolutionLog
)
from backend.workflows.shared import LLMVerdict, SynthesizedSolution
import pandas as pd
from typing import List, Dict, Optional

class DatabaseService:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

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
                llm_provider_model=verdict.llm_provider_model
            )
            
            update_stmt = stmt.on_conflict_do_update(
                index_elements=['ticket_key'],
                set_={
                    'module': stmt.excluded.module,
                    'status': stmt.excluded.status,
                    'missing_fields': stmt.excluded.missing_fields,
                    'confidence': stmt.excluded.confidence,
                    'llm_provider_model': stmt.excluded.llm_provider_model,
                    'validated_at': text('now()') 
                }
            )
            db.execute(update_stmt)
            db.commit()
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
                llm_provider_model=solution.llm_provider_model
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
            return [
                {
                    "ticket_key": log.ticket_key,
                    "module": log.module,
                    "confidence": log.confidence,
                    "validated_at": log.validated_at.isoformat() if log.validated_at else None
                }
                for log in results
            ]
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
            return [
                {
                    "ticket_key": log.ticket_key,
                    "module": log.module,
                    "missing_fields": log.missing_fields,
                    "validated_at": log.validated_at.isoformat() if log.validated_at else None,
                    "llm_provider_model": log.llm_provider_model
                }
                for log in results
            ]
        finally:
            db.close()


db_service = DatabaseService()
