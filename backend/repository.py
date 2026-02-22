# ============================================================
# repository.py — Production Safe Version
# ============================================================

from sqlalchemy import select
from database import AsyncSessionLocal
from db_models import IncidentDB, MessageDB, FindingDB
from models import Incident, Message, Finding, Hypothesis, TimelineEvent
from datetime import datetime


class Repository:

    # ─────────────────────────────────────────────
    # INCIDENT OPERATIONS
    # ─────────────────────────────────────────────

    async def create_incident(self, incident: Incident):
        async with AsyncSessionLocal() as session:

            db_inc = IncidentDB(
                id=incident.id,
                title=incident.title,
                description=incident.description,
                severity=incident.severity,
                affected_system=incident.affected_system,
                status="active",
                threads=incident.threads,
                timeline=[],
                hypothesis=None,
                executive_summary=None,
                executive_summary_version=0
            )

            session.add(db_inc)
            await session.commit()

    async def initialize_war_room(self, incident: Incident):
        """
        Auto-post system activation messages when incident is created.
        """

        async with AsyncSessionLocal() as session:

            # Opening summary message
            opening_message = MessageDB(
                incident_id=incident.id,
                thread="summary",
                sender="WarRoom Bot",
                sender_type="system",
                content=(
                    f"🚨 INCIDENT DECLARED\n\n"
                    f"Title: {incident.title}\n"
                    f"Severity: {incident.severity}\n"
                    f"Affected System: {incident.affected_system}\n\n"
                    f"{incident.description}\n\n"
                    f"All teams begin investigation immediately."
                )
            )

            session.add(opening_message)

            # Activate each team thread
            for thread in incident.threads:
                if thread == "summary":
                    continue

                team_msg = MessageDB(
                    incident_id=incident.id,
                    thread=thread,
                    sender="WarRoom Bot",
                    sender_type="system",
                    content=f"{thread.upper()} TEAM ACTIVATED. Begin investigation."
                )

                session.add(team_msg)

            await session.commit()

    async def list_incidents(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(IncidentDB))
            rows = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "status": r.status,
                    "severity": r.severity
                }
                for r in rows
            ]

    async def get_incident(self, incident_id: str):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(IncidentDB).where(IncidentDB.id == incident_id)
            )
            row = result.scalar_one_or_none()

            if not row:
                return None

            hypothesis = (
                Hypothesis(**row.hypothesis)
                if row.hypothesis else None
            )

            timeline = [
                TimelineEvent(**event)
                for event in (row.timeline or [])
            ]

            return Incident(
                id=row.id,
                title=row.title,
                description=row.description,
                severity=row.severity,
                affected_system=row.affected_system,
                status=row.status,
                threads=row.threads,
                hypothesis=hypothesis,
                timeline=timeline,
                executive_summary=row.executive_summary,
                executive_summary_version=row.executive_summary_version
            )

    async def update_incident(self, incident: Incident):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(IncidentDB).where(IncidentDB.id == incident.id)
            )
            db_inc = result.scalar_one_or_none()

            if not db_inc:
                return

            db_inc.status = incident.status

            db_inc.hypothesis = (
                incident.hypothesis.dict()
                if incident.hypothesis else None
            )

            db_inc.timeline = [
                event.dict()
                for event in incident.timeline
            ]

            db_inc.executive_summary = incident.executive_summary
            db_inc.executive_summary_version = incident.executive_summary_version

            await session.commit()

    # ─────────────────────────────────────────────
    # MESSAGE OPERATIONS
    # ─────────────────────────────────────────────

    async def add_message(self, msg: Message):
        async with AsyncSessionLocal() as session:
            session.add(
                MessageDB(
                    incident_id=msg.incident_id,
                    thread=msg.thread,
                    sender=msg.sender,
                    sender_type=msg.sender_type,
                    content=msg.content,
                    timestamp=msg.timestamp
                )
            )
            await session.commit()

    async def get_messages(self, incident_id: str, thread: str):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MessageDB)
                .where(MessageDB.incident_id == incident_id)
                .where(MessageDB.thread == thread)
            )

            rows = result.scalars().all()

            return [
                Message(
                    incident_id=r.incident_id,
                    thread=r.thread,
                    sender=r.sender,
                    sender_type=r.sender_type,
                    content=r.content,
                    timestamp=r.timestamp
                )
                for r in rows
            ]

    # ─────────────────────────────────────────────
    # FINDING OPERATIONS
    # ─────────────────────────────────────────────

    async def add_finding(self, incident_id: str, finding: Finding):
        async with AsyncSessionLocal() as session:
            session.add(
                FindingDB(
                    incident_id=incident_id,
                    thread=finding.thread,
                    engineer=finding.engineer,
                    raw_text=finding.raw_text,
                    signal_type=finding.signal_type,
                    entities=finding.entities,
                    confidence=finding.confidence
                )
            )
            await session.commit()

    async def get_findings(self, incident_id: str):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FindingDB)
                .where(FindingDB.incident_id == incident_id)
            )

            rows = result.scalars().all()

            return [
                Finding(
                    thread=r.thread,
                    engineer=r.engineer,
                    raw_text=r.raw_text,
                    signal_type=r.signal_type,
                    entities=r.entities,
                    confidence=r.confidence
                )
                for r in rows
            ]