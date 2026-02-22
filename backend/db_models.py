# ============================================================
# db_models.py — Enhanced Database Schema
# ============================================================

from sqlalchemy import Column, String, Text, Float, TIMESTAMP, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class IncidentDB(Base):
    """Main incident table"""
    __tablename__ = "incidents"

    id = Column(String, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    severity = Column(String, nullable=False)
    affected_system = Column(Text)
    status = Column(String, default="declared")
    
    # Timestamps
    declared_at = Column(TIMESTAMP, default=datetime.utcnow)
    resolved_at = Column(TIMESTAMP, nullable=True)
    
    # Leadership
    incident_commander = Column(String, nullable=True)
    escalated_to_vendor = Column(Boolean, default=False)
    
    # Team coordination (JSONB for flexibility)
    threads = Column(JSONB, default=list)
    team_states = Column(JSONB, default=dict)
    
    # Investigation
    hypothesis = Column(JSONB, nullable=True)
    timeline = Column(JSONB, default=list)
    actions = Column(JSONB, default=list)
    
    # Impact tracking
    impact = Column(JSONB, nullable=True)
    
    # Executive summary
    executive_summary = Column(Text, nullable=True)
    executive_summary_version = Column(Float, default=0.0)


class MessageDB(Base):
    """Messages in war room threads"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False, index=True)
    thread = Column(String, nullable=False, index=True)
    sender = Column(String, nullable=False)
    sender_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String, default="normal")
    is_critical = Column(Boolean, default=False)
    mentions = Column(JSONB, default=list)
    attachments = Column(JSONB, default=list)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, index=True)


class FindingDB(Base):
    """Investigation findings"""
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False, index=True)
    thread = Column(String, nullable=False, index=True)
    engineer = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    signal_type = Column(String, nullable=False)
    entities = Column(JSONB, default=dict)
    confidence = Column(Float, default=0.0)
    validated = Column(Boolean, default=False)
    related_actions = Column(JSONB, default=list)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, index=True)