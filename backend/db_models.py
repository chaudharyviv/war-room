# ============================================================
# db_models.py
# ============================================================

from sqlalchemy import Column, String, Text, Float, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class IncidentDB(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True)
    title = Column(Text)
    description = Column(Text)
    severity = Column(String)
    affected_system = Column(Text)
    opened_at = Column(TIMESTAMP, default=datetime.utcnow)
    resolved_at = Column(TIMESTAMP, nullable=True)
    status = Column(String)

    threads = Column(JSONB)
    hypothesis = Column(JSONB, nullable=True)
    timeline = Column(JSONB, nullable=True)

    executive_summary = Column(Text, nullable=True)
    executive_summary_version = Column(Float, default=0)


class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String)
    thread = Column(String)
    sender = Column(String)
    sender_type = Column(String)
    content = Column(Text)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)


class FindingDB(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String)
    thread = Column(String)
    engineer = Column(String)
    raw_text = Column(Text)
    signal_type = Column(String)
    entities = Column(JSONB)
    confidence = Column(Float)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)