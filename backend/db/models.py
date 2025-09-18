# File: backend/db/models.py
from sqlalchemy import Column, Integer, String, ForeignKey
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

# The following models are placeholders for future features (Agent 2 and logging)
# and are not actively used in the initial validation agent but are good to define.
class JiraTickets(Base):
    __tablename__ = "jira_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, unique=True, index=True, nullable=False)
    summary = Column(String)
    description = Column(String)
    # Storing embeddings would require pgvector specific types, handled separately
    # embedding = Column(Vector(384)) 

class Validations(Base):
    __tablename__ = "validations"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False) # e.g., 'complete', 'incomplete'
    missing_fields = Column(String) # Stored as a JSON string

class ActionsLog(Base):
    __tablename__ = "actions_log"
    id = Column(Integer, primary_key=True, index=True)
    ticket_key = Column(String, index=True, nullable=False)
    action_type = Column(String, nullable=False) # e.g., 'comment', 'reassign'
    details = Column(String)
