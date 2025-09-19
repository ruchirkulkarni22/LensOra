# File: backend/services/db_service.py
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, joinedload
from backend.config import settings
# --- FEATURE 1.1.4 ENHANCEMENT ---
# Import MandatoryFieldTemplates for the upsert logic
from backend.db.models import ModulesTaxonomy, MandatoryFieldTemplates, ValidationLog
from backend.workflows.shared import LLMVerdict
import pandas as pd
from typing import Dict, Any

class DatabaseService:
    """
    A service to interact with the application's PostgreSQL database.
    """
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def upsert_module_knowledge(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Upserts module and mandatory field knowledge from a DataFrame into the database.
        It updates existing entries or creates new ones.
        """
        db = self.SessionLocal()
        upserted_count = 0
        errors = []
        try:
            for index, row in df.iterrows():
                try:
                    module_name = row['module_name']
                    field_name = row['field_name']
                    
                    # Find or create the module
                    stmt = select(ModulesTaxonomy).where(ModulesTaxonomy.module_name == module_name)
                    module = db.execute(stmt).scalars().first()
                    if not module:
                        print(f"Creating new module: {module_name}")
                        module = ModulesTaxonomy(module_name=module_name, description=f"{module_name} process")
                        db.add(module)
                        db.flush() # Flush to get the new module ID
                    
                    # Find or create the mandatory field for that module
                    stmt_field = select(MandatoryFieldTemplates).where(
                        MandatoryFieldTemplates.module_id == module.id,
                        MandatoryFieldTemplates.field_name == field_name
                    )
                    field = db.execute(stmt_field).scalars().first()
                    
                    if not field:
                        print(f"Creating new field '{field_name}' for module '{module_name}'")
                        new_field = MandatoryFieldTemplates(module_id=module.id, field_name=field_name)
                        db.add(new_field)
                        upserted_count += 1
                    else:
                        print(f"Field '{field_name}' for module '{module_name}' already exists. Skipping.")

                except KeyError as e:
                    error_msg = f"Row {index + 2}: Missing required column: {e}"
                    errors.append(error_msg)
                    print(error_msg)
                    # Skip this row and continue with others
                    continue
            
            if not errors:
                db.commit()
                print("Knowledge base update committed successfully.")
            else:
                db.rollback()
                print("Rolling back due to errors.")
            
            return {"rows_upserted": upserted_count, "errors": errors}

        except Exception as e:
            db.rollback()
            print(f"A critical error occurred during upsert: {e}")
            return {"rows_upserted": 0, "errors": [str(e)]}
        finally:
            db.close()

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

