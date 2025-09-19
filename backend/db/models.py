# File: backend/db/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship, declarative_base
# --- FEATURE 2.2 ENHANCEMENT ---
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class ModulesTaxonomy(Base):
    __tablename__ = "modules_taxonomy"
    id = Column(Integer, primary_key=True, index=True)
    module_name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    mandatory_fields = relationship("MandatoryFieldTemplates", back_populates="module")

class MandatoryFieldTemplates(Base):
    __tablename__ = "mandatory_field_templates"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules_taxonomy.id"), nullable=False)
    field_name = Column(String, nullable=False)
    module = relationship("ModulesTaxonomy", back_populates="module")

# --- FEATURE 2.2 ENHANCEMENT ---
# New table to store the knowledge from previously solved JIRA tickets.
# This will be our internal RAG knowledge base.
class SolvedJiraTickets(Base):
    __tablename__ = "solved_jira_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, unique=True, index=True, nullable=False)
    summary = Column(Text)
    description = Column(Text)
    resolution = Column(Text)
    # The embedding is a 384-dimensional vector generated from the ticket's text.
    embedding = Column(Vector(384))


class ValidationsLog(Base):
    __tablename__ = "validations_log"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, index=True, nullable=False)
    module = Column(String)
    status = Column(String)
    missing_fields = Column(JSON)
    confidence = Column(String)
    llm_provider_model = Column(String)

