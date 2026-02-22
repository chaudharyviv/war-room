# ============================================================
# strategic_commander.py — Enhanced Multi-Team Coordinator
# ============================================================

import os
import json
import uuid
from typing import List, Dict
from openai import AsyncOpenAI
from models import (
    Hypothesis, TimelineEvent, Action, TeamState, TeamStatus,
    MessagePriority, ActionStatus, Message
)
from datetime import datetime

MODEL = "gpt-4o"
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class StrategicCommander:
    """
    Intelligent incident commander that:
    - Analyzes findings across all teams
    - Forms and updates hypotheses
    - Assigns targeted actions to specific teams
    - Detects blockers and coordinates help
    - Escalates when needed
    """

    def __init__(self, incident_id, repo):
        self.incident_id = incident_id
        self.repo = repo

    async def analyze_and_direct(self):
        """Main coordination loop"""
        
        incident = await self.repo.get_incident(self.incident_id)
        if not incident:
            return None

        findings = await self.repo.get_findings(self.incident_id)
        
        # Get current state
        analysis = await self._analyze_situation(incident, findings)
        
        if not analysis:
            return None

        # Apply updates
        await self._update_hypothesis(incident, analysis)
        await self._assign_actions(incident, analysis)
        await self._coordinate_teams(incident, analysis)
        await self._check_escalation(incident, analysis)
        
        # Add timeline event
        incident.timeline.append(
            TimelineEvent(
                event_type="strategic_analysis",
                description="Strategic Commander analyzed situation and updated directives"
            )
        )
        
        await self.repo.update_incident(incident)
        
        # Post summary to war room
        await self._broadcast_update(incident, analysis)
        
        return analysis

    async def _analyze_situation(self, incident, findings):
        """Get LLM analysis of current situation"""
        
        # Prepare context
        findings_by_team = {}
        for f in findings[-30:]:  # Recent findings
            if f.thread not in findings_by_team:
                findings_by_team[f.thread] = []
            findings_by_team[f.thread].append(f)
        
        findings_summary = ""
        for team, team_findings in findings_by_team.items():
            findings_summary += f"\n{team.upper()} TEAM:\n"
            for f in team_findings[-5:]:
                findings_summary += f"  - [{f.engineer}] {f.raw_text}\n"
        
        current_hypothesis = (
            f"Root Cause: {incident.hypothesis.root_cause}\n"
            f"Confidence: {incident.hypothesis.confidence}\n"
            f"Evidence: {', '.join(incident.hypothesis.supporting_evidence)}"
            if incident.hypothesis else "No hypothesis yet"
        )
        
        active_actions = [a for a in incident.actions if a.status != ActionStatus.COMPLETED]
        actions_summary = "\n".join([
            f"  - [{a.assigned_to}] {a.description} ({a.status.value})"
            for a in active_actions
        ]) if active_actions else "No active actions"
        
        # Team states
        team_status = ""
        for team_name, state in incident.team_states.items():
            team_status += f"  {team_name}: {state.status.value}"
            if state.blocked_reason:
                team_status += f" (BLOCKED: {state.blocked_reason})"
            team_status += "\n"

        prompt = f"""You are an elite Incident Commander managing a P{incident.severity.value[-1]} incident.

INCIDENT: {incident.title}
SYSTEM: {incident.affected_system}
DESCRIPTION: {incident.description}
STATUS: {incident.status.value}

CURRENT HYPOTHESIS:
{current_hypothesis}

TEAM STATUS:
{team_status}

ACTIVE ACTIONS:
{actions_summary}

RECENT FINDINGS:
{findings_summary}

Analyze the situation and provide strategic direction. Return STRICT JSON:

{{
  "updated_hypothesis": {{
    "root_cause": "Clear, technical root cause or null if not ready to update",
    "confidence": 0.0-1.0,
    "supporting_evidence": ["evidence1", "evidence2"]
  }},
  "new_actions": [
    {{
      "team": "team_name",
      "description": "Specific, actionable task",
      "priority": "critical|high|normal|low",
      "reasoning": "Why this action is needed"
    }}
  ],
  "team_coordination": [
    {{
      "source_team": "team_name",
      "target_team": "team_name",
      "request": "What help is needed"
    }}
  ],
  "escalation_needed": {{
    "escalate": true/false,
    "reason": "Why escalation is needed",
    "escalate_to": "vendor|management|security"
  }},
  "critical_blockers": ["blocker1", "blocker2"],
  "next_steps_summary": "Brief summary of strategic direction"
}}

RULES:
- Only update hypothesis if you have strong evidence (confidence > 0.6)
- Assign specific, actionable tasks, not vague instructions
- Coordinate teams when one team needs help from another
- Identify blockers that prevent progress
- Escalate only when teams are stuck or external help is needed
"""

        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Commander analysis error: {e}")
            return None

    async def _update_hypothesis(self, incident, analysis):
        """Update incident hypothesis based on analysis"""
        
        hyp_data = analysis.get("updated_hypothesis")
        if not hyp_data or not hyp_data.get("root_cause"):
            return
        
        # Only update if confidence is reasonable
        if hyp_data.get("confidence", 0) < 0.5:
            return
        
        if not incident.hypothesis:
            incident.hypothesis = Hypothesis(
                root_cause=hyp_data["root_cause"],
                confidence=hyp_data["confidence"],
                supporting_evidence=hyp_data.get("supporting_evidence", []),
                version=1
            )
            
            incident.timeline.append(
                TimelineEvent(
                    event_type="hypothesis_formed",
                    description=f"Initial hypothesis formed: {hyp_data['root_cause']}",
                    severity="high"
                )
            )
        else:
            # Update existing hypothesis
            old_cause = incident.hypothesis.root_cause
            incident.hypothesis.version += 1
            incident.hypothesis.root_cause = hyp_data["root_cause"]
            incident.hypothesis.confidence = hyp_data["confidence"]
            incident.hypothesis.supporting_evidence = hyp_data.get("supporting_evidence", [])
            incident.hypothesis.timestamp = datetime.utcnow()
            
            incident.timeline.append(
                TimelineEvent(
                    event_type="hypothesis_updated",
                    description=f"Hypothesis evolved (v{incident.hypothesis.version}): {hyp_data['root_cause']}",
                    severity="high",
                    metadata={"previous": old_cause}
                )
            )

    async def _assign_actions(self, incident, analysis):
        """Assign new actions to teams"""
        
        new_actions = analysis.get("new_actions", [])
        
        for action_data in new_actions:
            team = action_data.get("team")
            description = action_data.get("description")
            
            if not team or not description:
                continue
            
            # Create action
            action = Action(
                id=str(uuid.uuid4()),
                assigned_to=team,
                description=description,
                priority=MessagePriority(action_data.get("priority", "normal")),
                status=ActionStatus.PENDING
            )
            
            incident.actions.append(action)
            
            # Update team state
            if team in incident.team_states:
                incident.team_states[team].active_tasks.append(action.id)
                if incident.team_states[team].status == TeamStatus.STANDBY:
                    incident.team_states[team].status = TeamStatus.INVESTIGATING
            
            # Add to timeline
            incident.timeline.append(
                TimelineEvent(
                    event_type="action_assigned",
                    description=f"Action assigned to {team.upper()}: {description}",
                    team=team,
                    severity="normal" if action.priority == MessagePriority.NORMAL else "high"
                )
            )
            
            # Send message to team thread
            msg = Message(
                incident_id=incident.id,
                thread=team,
                sender="Strategic Commander",
                sender_type="commander",
                content=f"🎯 NEW ACTION [{action.priority.value.upper()}]:\n{description}\n\nReasoning: {action_data.get('reasoning', 'Investigation needed')}",
                priority=action.priority,
                is_critical=action.priority in [MessagePriority.CRITICAL, MessagePriority.HIGH]
            )
            
            await self.repo.add_message(msg)

    async def _coordinate_teams(self, incident, analysis):
        """Coordinate help between teams"""
        
        coordination = analysis.get("team_coordination", [])
        
        for coord in coordination:
            source = coord.get("source_team")
            target = coord.get("target_team")
            request = coord.get("request")
            
            if not all([source, target, request]):
                continue
            
            # Update team states
            if source in incident.team_states:
                if target not in incident.team_states[source].needs_help_from:
                    incident.team_states[source].needs_help_from.append(target)
            
            # Send coordination message
            msg_source = Message(
                incident_id=incident.id,
                thread=source,
                sender="Strategic Commander",
                sender_type="commander",
                content=f"🤝 Coordination Request: Awaiting input from {target.upper()} team.\n{request}",
                priority=MessagePriority.HIGH,
                mentions=[target]
            )
            
            msg_target = Message(
                incident_id=incident.id,
                thread=target,
                sender="Strategic Commander",
                sender_type="commander",
                content=f"🤝 {source.upper()} team needs your help:\n{request}",
                priority=MessagePriority.HIGH,
                mentions=[source],
                is_critical=True
            )
            
            await self.repo.add_message(msg_source)
            await self.repo.add_message(msg_target)
            
            incident.timeline.append(
                TimelineEvent(
                    event_type="team_coordination",
                    description=f"{source.upper()} requested help from {target.upper()}: {request}",
                    team=source,
                    metadata={"target_team": target}
                )
            )

    async def _check_escalation(self, incident, analysis):
        """Check if escalation is needed"""
        
        escalation = analysis.get("escalation_needed", {})
        
        if not escalation.get("escalate"):
            return
        
        reason = escalation.get("reason", "Unknown")
        escalate_to = escalation.get("escalate_to", "management")
        
        if escalate_to == "vendor" and not incident.escalated_to_vendor:
            incident.escalated_to_vendor = True
            
            # Add vendor thread if not exists
            if "vendor" not in incident.threads:
                idx = incident.threads.index("summary") if "summary" in incident.threads else len(incident.threads)
                incident.threads.insert(idx, "vendor")
                incident.team_states["vendor"] = TeamState(
                    name="vendor",
                    status=TeamStatus.INVESTIGATING
                )
            
            incident.timeline.append(
                TimelineEvent(
                    event_type="escalation",
                    description=f"Escalated to VENDOR: {reason}",
                    severity="critical"
                )
            )
            
            # Broadcast escalation
            msg = Message(
                incident_id=incident.id,
                thread="summary",
                sender="Strategic Commander",
                sender_type="commander",
                content=f"🚨 ESCALATION TO VENDOR\n\nReason: {reason}\n\nVendor team activated.",
                priority=MessagePriority.CRITICAL,
                is_critical=True
            )
            await self.repo.add_message(msg)

    async def _broadcast_update(self, incident, analysis):
        """Broadcast strategic update to summary thread"""
        
        summary = analysis.get("next_steps_summary", "Analysis complete")
        blockers = analysis.get("critical_blockers", [])
        
        content = f"📊 STRATEGIC UPDATE\n\n{summary}"
        
        if blockers:
            content += f"\n\n⚠️ Critical Blockers:\n" + "\n".join(f"  • {b}" for b in blockers)
        
        if incident.hypothesis:
            content += f"\n\n💡 Current Hypothesis (v{incident.hypothesis.version}):\n{incident.hypothesis.root_cause}\nConfidence: {incident.hypothesis.confidence:.0%}"
        
        msg = Message(
            incident_id=incident.id,
            thread="summary",
            sender="Strategic Commander",
            sender_type="commander",
            content=content,
            priority=MessagePriority.HIGH
        )
        
        await self.repo.add_message(msg)