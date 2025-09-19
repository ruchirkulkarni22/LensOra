# File: backend/services/db_service.py
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, joinedload
from backend.config import settings
from backend.db.models import ModulesTaxonomy, ValidationLog
from backend.workflows.shared import LLMVerdict

class DatabaseService:
    """
    A service to interact with the application's PostgreSQL database.
    """
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def log_validation_verdict(self, ticket_key: str, verdict: LLMVerdict):
        """
        Inserts a record of the validation attempt into the validations_log table.
        """
        db = self.SessionLocal()
        try:
            log_entry = ValidationLog(
                ticket_key=ticket_key,
                module=verdict.module,
                status=verdict.validation_status,
                missing_fields=verdict.missing_fields,
                confidence=verdict.confidence,
                # --- FEATURE 1.1.3 ENHANCEMENT ---
                # This is now dynamic, taken directly from the verdict object.
                llm_provider_model=verdict.llm_provider_model
            )
            db.add(log_entry)
            db.commit()
            print(f"Successfully logged validation verdict for {ticket_key} using model {verdict.llm_provider_model}.")
        except Exception as e:
            print(f"Error logging validation verdict for {ticket_key}: {e}")
            db.rollback()
        finally:
            db.close()

    def get_all_modules_with_fields(self) -> dict:
        """
        Fetches all modules and their associated mandatory fields from the database.
        This provides the "knowledge" for the LLM.
        """
        db = self.SessionLocal()
        try:
            stmt = (
                select(ModulesTaxonomy)
                .options(joinedload(ModulesTaxonomy.mandatory_fields))
            )
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

db_service = DatabaseService()

