# File: backend/services/db_service.py
import json
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.dialects.postgresql import insert
from backend.config import settings
# --- FLAWLESS FIX ---
# Corrected the import from ValidationLog to ValidationsLog to match the model class name.
from backend.db.models import ModulesTaxonomy, MandatoryFieldTemplates, ValidationsLog
from backend.workflows.shared import LLMVerdict
import pandas as pd

class DatabaseService:
    """
    A service to interact with the application's PostgreSQL database.
    """
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

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

    def log_validation_result(self, ticket_key: str, verdict: LLMVerdict):
        """
        Logs the result of a ticket validation to the ValidationsLog table.
        """
        db = self.SessionLocal()
        try:
            log_entry = ValidationsLog(
                ticket_key=ticket_key,
                module=verdict.module,
                status=verdict.validation_status,
                missing_fields=verdict.missing_fields,
                confidence=str(verdict.confidence), # Store as string for flexibility
                llm_provider_model=verdict.llm_provider_model
            )
            db.add(log_entry)
            db.commit()
            print(f"Successfully logged validation verdict for {ticket_key} using model {verdict.llm_provider_model}.")
        except Exception as e:
            db.rollback()
            print(f"Failed to log validation verdict for {ticket_key}. Error: {e}")
        finally:
            db.close()
            
    def upsert_module_knowledge(self, df: pd.DataFrame) -> dict:
        """
        Processes a DataFrame and upserts module and mandatory field knowledge.
        - Creates new modules if they don't exist.
        - Adds new mandatory fields to existing or new modules.
        - Skips duplicates gracefully.
        """
        db = self.SessionLocal()
        processed_count = 0
        upserted_count = 0
        errors = []

        try:
            # Group by module to handle them transactionally
            for module_name, group in df.groupby('module_name'):
                # 1. Upsert the module itself
                module_stmt = insert(ModulesTaxonomy).values(
                    module_name=module_name,
                    description=f"{module_name} process" # Default description
                ).on_conflict_do_nothing(
                    index_elements=['module_name']
                )
                db.execute(module_stmt)

                # Get the module ID, whether it was new or existing
                module = db.query(ModulesTaxonomy).filter(ModulesTaxonomy.module_name == module_name).one()

                # 2. Upsert the mandatory fields for this module
                for _, row in group.iterrows():
                    processed_count += 1
                    field_name = row['field_name']

                    # Check if this field already exists for this module
                    exists = db.query(MandatoryFieldTemplates).filter_by(
                        module_id=module.id,
                        field_name=field_name
                    ).first()

                    if not exists:
                        new_field = MandatoryFieldTemplates(
                            module_id=module.id,
                            field_name=field_name
                        )
                        db.add(new_field)
                        upserted_count += 1
                        print(f"Creating new field '{field_name}' for module '{module_name}'")
            
            db.commit()
            print("Knowledge base update committed successfully.")
            
        except Exception as e:
            db.rollback()
            errors.append(str(e))
            print(f"An error occurred during knowledge upsert: {e}")
        finally:
            db.close()
        
        return {"rows_processed": processed_count, "rows_upserted": upserted_count, "errors": errors}


db_service = DatabaseService()

