# ============================================================
# repository.py — Data Layer
# ============================================================

from sqlalchemy import select, desc
from database import AsyncSessionLocal
from db_models import IncidentDB, MessageDB, FindingDB
from models import (
    Incident, Message, Finding, Hypothesis, TimelineEvent,
    TeamState, Action, Impact, TeamStatus
)
from datetime import datetime
from typing import List, Optional


class Repository:
    """Data access layer for war room"""

    # ─────────────────────────────────────────────
    # INCIDENT OPERATIONS
    # ─────────────────────────────────────────────

    async def create_incident(self, incident: Incident):
        """Create new incident"""
        async with AsyncSessionLocal() as session:
            
            # Initialize team states for all threads
            team_states = {}
            for thread in incident.threads:
                if thread != "summary":
                    team_states[thread] = TeamState(
                        name=thread,
                        status=TeamStatus.STANDBY
                    ).dict()
            
            db_inc = IncidentDB(
                id=incident.id,
                title=incident.title,
                description=incident.description,
                severity=incident.severity.value,
                affected_system=incident.affected_system,
                status=incident.status.value,
                incident_commander=incident.incident_commander,
                threads=incident.threads,
                team_states=team_states,
                timeline=[],
                actions=[],
                hypothesis=None,
                impact=incident.impact.dict() if incident.impact else None,
                executive_summary=None,
                executive_summary_version=0
            )

            session.add(db_inc)
            await session.commit()

    async def initialize_war_room(self, incident: Incident):
        """Initialize war room with activation messages"""
        
        async with AsyncSessionLocal() as session:
            
            # Opening message
            opening_message = MessageDB(
                incident_id=incident.id,
                thread="summary",
                sender="War Room System",
                sender_type="system",
                content=(
                    f"🚨 {'CRITICAL ' if incident.severity.value == 'P0' else ''}INCIDENT DECLARED\n\n"
                    f"**{incident.title}**\n\n"
                    f"Severity: {incident.severity.value}\n"
                    f"Affected System: {incident.affected_system}\n"
                    f"Commander: {incident.incident_commander or 'TBD'}\n\n"
                    f"{incident.description}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"All teams: Begin immediate investigation.\n"
                    f"Strategic Commander AI is monitoring."
                ),
                priority="critical",
                is_critical=True
            )
            
            session.add(opening_message)
            
            # Activate each technical team
            for thread in incident.threads:
                if thread == "summary":
                    continue
                
                team_msg = MessageDB(
                    incident_id=incident.id,
                    thread=thread,
                    sender="War Room System",
                    sender_type="system",
                    content=(
                        f"🎯 {thread.upper()} TEAM ACTIVATED\n\n"
                        f"Incident: {incident.title}\n"
                        f"Your Focus: Investigate {thread}-specific aspects\n\n"
                        f"Report all findings immediately."
                    ),
                    priority="high"
                )
                
                session.add(team_msg)
            
            await session.commit()

    async def list_incidents(self, status_filter: Optional[str] = None) -> List[dict]:
        """List all incidents with optional status filter"""
        async with AsyncSessionLocal() as session:
            query = select(IncidentDB).order_by(desc(IncidentDB.declared_at))
            
            if status_filter:
                query = query.where(IncidentDB.status == status_filter)
            
            result = await session.execute(query)
            rows = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "status": r.status,
                    "severity": r.severity,
                    "affected_system": r.affected_system,
                    "declared_at": r.declared_at.isoformat() if r.declared_at else None,
                    "incident_commander": r.incident_commander
                }
                for r in rows
            ]

    async def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get incident by ID with full details"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(IncidentDB).where(IncidentDB.id == incident_id)
            )
            row = result.scalar_one_or_none()

            if not row:
                return None

            # Reconstruct team states
            team_states = {}
            for team_name, state_data in (row.team_states or {}).items():
                team_states[team_name] = TeamState(**state_data)

            # Reconstruct hypothesis
            hypothesis = (
                Hypothesis(**row.hypothesis)
                if row.hypothesis else None
            )

            # Reconstruct timeline
            timeline = [
                TimelineEvent(**event)
                for event in (row.timeline or [])
            ]

            # Reconstruct actions
            actions = [
                Action(**action)
                for action in (row.actions or [])
            ]

            # Reconstruct impact
            impact = Impact(**row.impact) if row.impact else None

            return Incident(
                id=row.id,
                title=row.title,
                description=row.description,
                severity=row.severity,
                affected_system=row.affected_system,
                status=row.status,
                incident_commander=row.incident_commander,
                escalated_to_vendor=row.escalated_to_vendor,
                declared_at=row.declared_at,
                resolved_at=row.resolved_at,
                threads=row.threads,
                team_states=team_states,
                hypothesis=hypothesis,
                timeline=timeline,
                actions=actions,
                impact=impact,
                executive_summary=row.executive_summary,
                executive_summary_version=row.executive_summary_version
            )

    async def update_incident(self, incident: Incident):
        """Update incident with all changes"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(IncidentDB).where(IncidentDB.id == incident.id)
            )
            db_inc = result.scalar_one_or_none()

            if not db_inc:
                return

            # Update fields
            db_inc.status = incident.status.value if hasattr(incident.status, 'value') else incident.status
            db_inc.incident_commander = incident.incident_commander
            db_inc.escalated_to_vendor = incident.escalated_to_vendor
            db_inc.resolved_at = incident.resolved_at

            # Update team states
            db_inc.team_states = {
                name: state.dict()
                for name, state in incident.team_states.items()
            }

            # Update hypothesis
            db_inc.hypothesis = (
                incident.hypothesis.dict()
                if incident.hypothesis else None
            )

            # Update timeline
            db_inc.timeline = [
                event.dict()
                for event in incident.timeline
            ]

            # Update actions
            db_inc.actions = [
                action.dict()
                for action in incident.actions
            ]

            # Update impact
            db_inc.impact = incident.impact.dict() if incident.impact else None

            # Update executive summary
            db_inc.executive_summary = incident.executive_summary
            db_inc.executive_summary_version = incident.executive_summary_version

            await session.commit()

    # ─────────────────────────────────────────────
    # MESSAGE OPERATIONS
    # ─────────────────────────────────────────────

    async def add_message(self, msg: Message):
        """Add message to thread"""
        async with AsyncSessionLocal() as session:
            session.add(
                MessageDB(
                    incident_id=msg.incident_id,
                    thread=msg.thread,
                    sender=msg.sender,
                    sender_type=msg.sender_type,
                    content=msg.content,
                    priority=msg.priority.value if hasattr(msg.priority, 'value') else msg.priority,
                    is_critical=msg.is_critical,
                    mentions=msg.mentions,
                    attachments=msg.attachments,
                    timestamp=msg.timestamp
                )
            )
            await session.commit()

    async def get_messages(
        self, 
        incident_id: str, 
        thread: str, 
        limit: int = 100
    ) -> List[Message]:
        """Get messages for a thread"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MessageDB)
                .where(MessageDB.incident_id == incident_id)
                .where(MessageDB.thread == thread)
                .order_by(MessageDB.timestamp)
                .limit(limit)
            )

            rows = result.scalars().all()

            return [
                Message(
                    incident_id=r.incident_id,
                    thread=r.thread,
                    sender=r.sender,
                    sender_type=r.sender_type,
                    content=r.content,
                    priority=r.priority,
                    is_critical=r.is_critical,
                    mentions=r.mentions,
                    attachments=r.attachments,
                    timestamp=r.timestamp
                )
                for r in rows
            ]

    async def get_all_messages(self, incident_id: str) -> List[Message]:
        """Get all messages across all threads"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MessageDB)
                .where(MessageDB.incident_id == incident_id)
                .order_by(MessageDB.timestamp)
            )

            rows = result.scalars().all()

            return [
                Message(
                    incident_id=r.incident_id,
                    thread=r.thread,
                    sender=r.sender,
                    sender_type=r.sender_type,
                    content=r.content,
                    priority=r.priority,
                    is_critical=r.is_critical,
                    mentions=r.mentions,
                    attachments=r.attachments,
                    timestamp=r.timestamp
                )
                for r in rows
            ]

    # ─────────────────────────────────────────────
    # FINDING OPERATIONS
    # ─────────────────────────────────────────────

    async def add_finding(self, incident_id: str, finding: Finding):
        """Add investigation finding"""
        async with AsyncSessionLocal() as session:
            session.add(
                FindingDB(
                    incident_id=incident_id,
                    thread=finding.thread,
                    engineer=finding.engineer,
                    raw_text=finding.raw_text,
                    signal_type=finding.signal_type,
                    entities=finding.entities,
                    confidence=finding.confidence,
                    validated=finding.validated,
                    related_actions=finding.related_actions,
                    timestamp=finding.timestamp
                )
            )
            await session.commit()

    async def get_findings(
        self, 
        incident_id: str, 
        thread: Optional[str] = None
    ) -> List[Finding]:
        """Get findings for incident, optionally filtered by thread"""
        async with AsyncSessionLocal() as session:
            query = select(FindingDB).where(
                FindingDB.incident_id == incident_id
            ).order_by(FindingDB.timestamp)
            
            if thread:
                query = query.where(FindingDB.thread == thread)
            
            result = await session.execute(query)
            rows = result.scalars().all()

            return [
                Finding(
                    thread=r.thread,
                    engineer=r.engineer,
                    raw_text=r.raw_text,
                    signal_type=r.signal_type,
                    entities=r.entities,
                    confidence=r.confidence,
                    validated=r.validated,
                    related_actions=r.related_actions,
                    timestamp=r.timestamp
                )
                for r in rows
            ]