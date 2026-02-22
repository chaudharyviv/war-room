# ============================================================
# models.py — Enhanced Enterprise War Room Models
# ============================================================

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────
# Enums for Type Safety
# ─────────────────────────────────────────────

class IncidentSeverity(str, Enum):
    P0 = "P0"  # Critical - System Down
    P1 = "P1"  # High - Major Feature Broken
    P2 = "P2"  # Medium - Degraded Performance
    P3 = "P3"  # Low - Minor Issue
    P4 = "P4"  # Informational


class IncidentStatus(str, Enum):
    DECLARED = "declared"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    POSTMORTEM = "postmortem"


class TeamStatus(str, Enum):
    STANDBY = "standby"
    INVESTIGATING = "investigating"
    BLOCKED = "blocked"
    FOUND_ISSUE = "found_issue"
    RESOLVED = "resolved"


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


# ─────────────────────────────────────────────
# Core Models
# ─────────────────────────────────────────────

class TeamState(BaseModel):
    """Real-time state of each team"""
    name: str
    status: TeamStatus = TeamStatus.STANDBY
    assigned_engineers: List[str] = Field(default_factory=list)
    active_tasks: List[str] = Field(default_factory=list)
    findings_count: int = 0
    last_update: datetime = Field(default_factory=datetime.utcnow)
    blocked_reason: Optional[str] = None
    needs_help_from: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            TeamStatus: lambda v: v.value if hasattr(v, 'value') else v,
        }


class Action(BaseModel):
    """Actionable task assigned to teams"""
    id: str
    assigned_to: str  # team name
    description: str
    priority: MessagePriority = MessagePriority.NORMAL
    status: ActionStatus = ActionStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: str = "Strategic Commander"
    completed_at: Optional[datetime] = None
    blocking_issues: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            MessagePriority: lambda v: v.value if hasattr(v, 'value') else v,
            ActionStatus: lambda v: v.value if hasattr(v, 'value') else v,
        }


class Hypothesis(BaseModel):
    """Current understanding of root cause"""
    root_cause: str
    confidence: float  # 0.0 to 1.0
    supporting_evidence: List[str] = Field(default_factory=list)
    version: int = 1
    proposed_by: str = "Strategic Commander"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class TimelineEvent(BaseModel):
    """Event in incident timeline"""
    event_type: str  # detection, escalation, finding, action, resolution
    description: str
    team: Optional[str] = None
    severity: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class Impact(BaseModel):
    """Business impact tracking"""
    affected_users: Optional[int] = None
    affected_services: List[str] = Field(default_factory=list)
    revenue_impact: Optional[str] = None
    customer_complaints: int = 0
    sla_breach: bool = False


class Incident(BaseModel):
    """Main incident model"""
    id: str
    title: str
    description: str
    severity: IncidentSeverity
    affected_system: str
    status: IncidentStatus = IncidentStatus.DECLARED
    
    # Team coordination
    threads: List[str] = Field(
        default_factory=lambda: [
            "unix", "windows", "network",
            "database", "application",
            "middleware", "cloud",
            "security", "storage",
            "summary"
        ]
    )
    team_states: Dict[str, TeamState] = Field(default_factory=dict)
    
    # Investigation state
    hypothesis: Optional[Hypothesis] = None
    timeline: List[TimelineEvent] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    
    # Impact
    impact: Optional[Impact] = None
    
    # Metadata
    declared_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    incident_commander: Optional[str] = None
    escalated_to_vendor: bool = False
    
    # Executive summary
    executive_summary: Optional[str] = None
    executive_summary_version: float = 0.0

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            IncidentSeverity: lambda v: v.value if hasattr(v, 'value') else v,
            IncidentStatus: lambda v: v.value if hasattr(v, 'value') else v,
            TeamStatus: lambda v: v.value if hasattr(v, 'value') else v,
            MessagePriority: lambda v: v.value if hasattr(v, 'value') else v,
            ActionStatus: lambda v: v.value if hasattr(v, 'value') else v,
        }


class Message(BaseModel):
    """Communication message"""
    incident_id: str
    thread: str
    sender: str
    sender_type: str  # engineer, agent, system, commander
    content: str
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mentions: List[str] = Field(default_factory=list)  # @team mentions
    attachments: List[str] = Field(default_factory=list)
    is_critical: bool = False

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            MessagePriority: lambda v: v.value if hasattr(v, 'value') else v,
        }


class Finding(BaseModel):
    """Investigation finding"""
    thread: str
    engineer: str
    raw_text: str
    signal_type: str  # info, warning, root_cause_candidate, blocker, resolution
    entities: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    related_actions: List[str] = Field(default_factory=list)
    validated: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


# ─────────────────────────────────────────────
# API Request/Response Models
# ─────────────────────────────────────────────

class CreateIncidentRequest(BaseModel):
    title: str
    description: str
    severity: IncidentSeverity
    affected_system: str
    impact: Optional[Impact] = None
    incident_commander: Optional[str] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            IncidentSeverity: lambda v: v.value if hasattr(v, 'value') else v,
        }


class AddMessageRequest(BaseModel):
    thread: str
    engineer_name: str
    content: str
    priority: MessagePriority = MessagePriority.NORMAL

    class Config:
        use_enum_values = True
        json_encoders = {
            MessagePriority: lambda v: v.value if hasattr(v, 'value') else v,
        }


class UpdateActionRequest(BaseModel):
    action_id: str
    status: ActionStatus
    notes: Optional[str] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            ActionStatus: lambda v: v.value if hasattr(v, 'value') else v,
        }


class TeamStatusUpdate(BaseModel):
    team: str
    status: TeamStatus
    blocked_reason: Optional[str] = None
    needs_help_from: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True
        json_encoders = {
            TeamStatus: lambda v: v.value if hasattr(v, 'value') else v,
        }