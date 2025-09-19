# File: backend/db/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Float, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, declarative_base

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
    module = relationship("ModulesTaxonomy", back_populates="mandatory_fields")

class JiraTickets(Base):
    __tablename__ = "jira_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, unique=True, index=True, nullable=False)
    summary = Column(String)
    description = Column(String)

class ValidationLog(Base):
    __tablename__ = "validations_log"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, index=True, nullable=False)
    module = Column(String, nullable=True)
    status = Column(String, nullable=False) # e.g., 'complete', 'incomplete'
    missing_fields = Column(JSON, nullable=True) # Stored as a JSON object/array
    confidence = Column(Float, nullable=True)
    llm_provider_model = Column(String, nullable=True, default="gemini-1.5-flash")
    validated_at = Column(DateTime(timezone=True), server_default=func.now())

class ActionsLog(Base):
    __tablename__ = "actions_log"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, index=True, nullable=False)
    action_type = Column(String, nullable=False) # e.g., 'comment', 'reassign'
    details = Column(String)

