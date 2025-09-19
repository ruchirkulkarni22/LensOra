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
    # --- FINAL FEATURE ---
    # Import the new ResolutionLog model
    ResolutionLog
)
from backend.workflows.shared import LLMVerdict, SynthesizedSolution
import pandas as pd
from typing import List, Dict

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
            log_entry = ValidationsLog(
                ticket_key=ticket_key,
                module=verdict.module,
                status=verdict.validation_status,
                missing_fields=verdict.missing_fields,
                confidence=str(verdict.confidence),
                llm_provider_model=verdict.llm_provider_model,
            )
            db.add(log_entry)
            db.commit()
        finally:
            db.close()

    def process_knowledge_upload(self, df: pd.DataFrame) -> dict:
        db = self.SessionLocal()
        try:
            processed_count = 0
            upserted_count = 0
            
            for _, row in df.iterrows():
                module_name = row['module_name']
                field_name = row['field_name']
                processed_count += 1

                module_stmt = select(ModulesTaxonomy).where(ModulesTaxonomy.module_name == module_name)
                module = db.execute(module_stmt).scalar_one_or_none()
                if not module:
                    print(f"Creating new module: {module_name}")
                    module = ModulesTaxonomy(module_name=module_name, description=f"{module_name} process")
                    db.add(module)
                    db.flush() 

                field_stmt = select(MandatoryFieldTemplates).where(
                    MandatoryFieldTemplates.module_id == module.id,
                    MandatoryFieldTemplates.field_name == field_name
                )
                field = db.execute(field_stmt).scalar_one_or_none()
                if not field:
                    print(f"Creating new field '{field_name}' for module '{module_name}'")
                    new_field = MandatoryFieldTemplates(module_id=module.id, field_name=field_name)
                    db.add(new_field)
                    upserted_count += 1
            
            db.commit()
            print("Knowledge base update committed successfully.")
            return {"rows_processed": processed_count, "rows_upserted": upserted_count, "errors": []}
        except Exception as e:
            db.rollback()
            return {"rows_processed": 0, "rows_upserted": 0, "errors": [str(e)]}
        finally:
            db.close()

    # --- FINAL FEATURE ---
    # New method to log the successful resolution.
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


db_service = DatabaseService()

