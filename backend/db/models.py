# File: backend/db/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Text, Float
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

