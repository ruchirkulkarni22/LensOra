# File: backend/services/db_service.py
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, joinedload
from backend.config import settings
from backend.db.models import ModulesTaxonomy

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

db_service = DatabaseService()
