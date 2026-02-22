# ============================================================
# models.py —  
# ============================================================

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


# ─────────────────────────────────────────────
# Hypothesis
# ─────────────────────────────────────────────

class Hypothesis(BaseModel):
    root_cause: str
    confidence: float
    version: int = 1


# ─────────────────────────────────────────────
# Timeline Event
# ─────────────────────────────────────────────

class TimelineEvent(BaseModel):
    event_type: str
    description: str
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


# ─────────────────────────────────────────────
# Incident
# ─────────────────────────────────────────────

class Incident(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    affected_system: str
    status: str = "open"

    # Default enterprise threads
    threads: List[str] = Field(
        default_factory=lambda: [
            "unix", "windows", "network",
            "database", "application",
            "middleware", "cloud",
            "security", "storage",
            "summary"
        ]
    )

    hypothesis: Optional[Hypothesis] = None
    timeline: List[TimelineEvent] = Field(default_factory=list)

    executive_summary: Optional[str] = None
    executive_summary_version: float = 0.0


# ─────────────────────────────────────────────
# Message
# ─────────────────────────────────────────────

class Message(BaseModel):
    incident_id: str
    thread: str
    sender: str
    sender_type: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# Finding
# ─────────────────────────────────────────────

class Finding(BaseModel):
    thread: str
    engineer: str
    raw_text: str
    signal_type: str
    entities: Optional[Dict[str, Any]] = None
    confidence: float = 0.0