from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class Hypothesis(BaseModel):
    root_cause: str
    confidence: float
    version: int = 1

class TimelineEvent(BaseModel):
    event_type: str
    description: str
    timestamp: Optional[str] = None

class Incident(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    affected_system: str
    status: str = "open"
    threads: List[str] = Field(default_factory=lambda: ["investigation", "summary"])
    hypothesis: Optional[Hypothesis] = None
    timeline: List[TimelineEvent] = Field(default_factory=list)
    executive_summary: Optional[str] = None
    executive_summary_version: float = 0.0

class Message(BaseModel):
    incident_id: str
    thread: str
    sender: str
    sender_type: str
    content: str
    timestamp: Optional[datetime] = None

class Finding(BaseModel):
    thread: str
    engineer: str
    raw_text: str
    signal_type: str
    entities: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
