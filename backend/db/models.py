# File: backend/db/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Text, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, declarative_base
import pgvector.sqlalchemy
from pgvector.sqlalchemy import VECTOR

Base = declarative_base()

class ModulesTaxonomy(Base):
    __tablename__ = "modules_taxonomy"
    id = Column(Integer, primary_key=True, index=True)
    module_name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    mandatory_fields = relationship("MandatoryFieldTemplates", back_populates="module", cascade="all, delete-orphan")

class MandatoryFieldTemplates(Base):
    __tablename__ = "mandatory_field_templates"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules_taxonomy.id"), nullable=False)
    field_name = Column(String, nullable=False)
    module = relationship("ModulesTaxonomy", back_populates="mandatory_fields")

class ValidationsLog(Base):
    __tablename__ = "validations_log"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, index=True, nullable=False)
    module = Column(String, nullable=False)
    status = Column(String, nullable=False)
    missing_fields = Column(JSON)
    confidence = Column(Float)
    llm_provider_model = Column(String)
    validated_at = Column(DateTime, server_default=func.now())
    # Optional runtime-added columns (may not exist in initial migration)
    # Use reflection-safe access; migrations should eventually formalize these.
    # They are declared here for ORM attribute convenience.
    # The actual DDL is executed at runtime in db_service._ensure_schema_extensions
    # so absence in DB initially should be handled gracefully.
    # NOTE: Some DBs may require Alembic migration for production.
    duplicate_of = Column(String, nullable=True)
    priority = Column(String, nullable=True)

class SolvedJiraTickets(Base):
    __tablename__ = "solved_jira_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, unique=True, index=True, nullable=False)
    summary = Column(Text)
    description = Column(Text)
    resolution = Column(Text, nullable=False)
    embedding = Column(VECTOR(384))

# --- FINAL FEATURE ---
# New table to log every successful resolution.
class ResolutionLog(Base):
    __tablename__ = "resolution_log"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, index=True, nullable=False)
    solution_posted = Column(Text, nullable=False)
    llm_provider_model = Column(String)
    resolved_at = Column(DateTime, server_default=func.now())
    sources_json = Column(JSON)
    reasoning_text = Column(Text)
    # optional draft linkage
    draft_id = Column(Integer, nullable=True)

# --- External Web Search Augmentation ---
class ExternalDocs(Base):
    __tablename__ = "external_docs"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, unique=True, nullable=False, index=True)
    domain = Column(String, index=True)
    title = Column(Text)
    content_text = Column(Text, nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)
    embedding = Column(VECTOR(384))
    fetched_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)

class ExternalSearchAudit(Base):
    __tablename__ = "external_search_audit"
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    normalized_query_hash = Column(String(64), index=True, nullable=False)
    provider_used = Column(String(50))
    result_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())

