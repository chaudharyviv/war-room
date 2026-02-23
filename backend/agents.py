# ============================================================
# agents.py — Enhanced Multi-Agent System
# ============================================================

import os
import json
import re
from openai import AsyncOpenAI
from models import (
    Message, Finding, TeamStatus, MessagePriority,
    TimelineEvent, ActionStatus
)
from strategic_commander import StrategicCommander

MODEL = "gpt-4o"
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def safe_llm_call(messages, response_format=None, max_tokens=500):
    """Safe LLM call with error handling"""
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=max_tokens,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM call error: {e}")
        return None


class OrchestratorAgent:
    """
    Main orchestrator that:
    - Processes engineer inputs
    - Classifies signal types
    - Triggers Strategic Commander when needed
    - Manages team states
    """

    def __init__(self, incident_id, repo):
        self.incident_id = incident_id
        self.repo = repo

    async def process_engineer_input(self, thread, engineer_name, content):
        """Process input from an engineer"""
        
        incident = await self.repo.get_incident(self.incident_id)
        if not incident:
            return {"error": "Incident not found"}
        
        # Classify the signal
        classification = await self._classify_signal(content, thread, incident)
        
        if not classification:
            # Default classification
            classification = {
                "signal_type": "info",
                "confidence": 0.5,
                "entities": {},
                "should_trigger_commander": False
            }
        
        # Create finding
        finding = Finding(
            thread=thread,
            engineer=engineer_name,
            raw_text=content,
            signal_type=classification["signal_type"],
            confidence=classification["confidence"],
            entities=classification.get("entities", {})
        )
        
        await self.repo.add_finding(self.incident_id, finding)
        
        # Update team state
        if thread in incident.team_states:
            incident.team_states[thread].findings_count += 1
            incident.team_states[thread].last_update = finding.timestamp
            
            # Update engineers list
            if engineer_name not in incident.team_states[thread].assigned_engineers:
                incident.team_states[thread].assigned_engineers.append(engineer_name)
            
            # Update status based on signal type
            current_status = incident.team_states[thread].status
            current_status_val = current_status.value if hasattr(current_status, 'value') else current_status
            if classification["signal_type"] == "blocker":
                incident.team_states[thread].status = TeamStatus.BLOCKED
                incident.team_states[thread].blocked_reason = content[:100]
            elif classification["signal_type"] == "root_cause_candidate":
                incident.team_states[thread].status = TeamStatus.FOUND_ISSUE
            elif current_status_val == TeamStatus.STANDBY.value:
                incident.team_states[thread].status = TeamStatus.INVESTIGATING
        
        # Add to timeline
        timeline_event = TimelineEvent(
            event_type="finding",
            description=f"[{thread.upper()}] {engineer_name}: {content[:80]}...",
            team=thread,
            severity="high" if classification["signal_type"] in ["root_cause_candidate", "blocker"] else "normal"
        )
        incident.timeline.append(timeline_event)
        
        await self.repo.update_incident(incident)
        
        # Generate agent response
        agent_response = await self._generate_agent_response(
            content, classification, thread, incident
        )
        
        # Create agent reply message
        reply = Message(
            incident_id=self.incident_id,
            thread=thread,
            sender=f"{thread.title()} Agent",
            sender_type="agent",
            content=agent_response,
            priority=MessagePriority.HIGH if classification["signal_type"] in ["root_cause_candidate", "blocker"] else MessagePriority.NORMAL
        )
        
        await self.repo.add_message(reply)
        
        # Trigger Strategic Commander if needed
        should_trigger = (
            classification.get("should_trigger_commander", False) or
            classification["signal_type"] in ["root_cause_candidate", "blocker"] or
            incident.team_states[thread].findings_count % 3 == 0  # Periodic review
        )
        
        if should_trigger:
            commander = StrategicCommander(self.incident_id, self.repo)
            await commander.analyze_and_direct()
        
        return {
            "agent_reply": reply,
            "finding": finding,
            "triggered_commander": should_trigger
        }

    async def _classify_signal(self, content, thread, incident):
        """Classify the type of signal from engineer input"""
        
        severity_str = incident.severity.value if hasattr(incident.severity, 'value') else incident.severity
        prompt = f"""You are analyzing an engineer's update during a P{severity_str[-1]} incident.

INCIDENT: {incident.title}
AFFECTED SYSTEM: {incident.affected_system}
TEAM: {thread}
ENGINEER UPDATE: {content}

Classify this update. Return STRICT JSON:

{{
  "signal_type": "info|warning|root_cause_candidate|blocker|resolution|request_help",
  "confidence": 0.0-1.0,
  "entities": {{
    "systems": ["system1", "system2"],
    "errors": ["error1"],
    "metrics": {{"metric": "value"}},
    "timestamps": ["time1"]
  }},
  "should_trigger_commander": true/false,
  "summary": "One sentence summary"
}}

Signal Types:
- info: General investigation update
- warning: Concerning finding but not blocking
- root_cause_candidate: Likely found the root cause
- blocker: Team is blocked and needs help
- resolution: Team has found a fix
- request_help: Explicitly asking for help from another team

Trigger commander if:
- Root cause candidate found
- Team is blocked
- Multiple teams need coordination
- Critical finding
"""

        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500
            )
            
            raw = response.choices[0].message.content or ""
            raw = raw.strip()
            if raw.startswith("```"):
                import re
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                raw = raw.strip()
            if not raw:
                return None
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"Classification JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"Classification error: {e}")
            return None

    async def _generate_agent_response(self, content, classification, thread, incident):
        """Generate intelligent agent response"""
        
        signal_type = classification["signal_type"]
        
        if signal_type == "root_cause_candidate":
            return (
                f"🎯 Excellent finding! This could be the root cause.\n\n"
                f"I'm alerting the Strategic Commander to analyze this across all teams.\n\n"
                f"Continue gathering evidence to support this hypothesis."
            )
        
        elif signal_type == "blocker":
            needs_help = self._suggest_help_team(content, thread)
            return (
                f"⚠️ Blocker identified.\n\n"
                f"I'm alerting the Strategic Commander for coordination.\n\n"
                f"{'Suggested: Check with ' + needs_help + ' team.' if needs_help else 'Documenting blocker.'}"
            )
        
        elif signal_type == "resolution":
            return (
                f"✅ Great progress!\n\n"
                f"Document the resolution steps and test thoroughly.\n\n"
                f"I'll update the Strategic Commander."
            )
        
        elif signal_type == "warning":
            return (
                f"⚠️ Noted. Continue investigating this path.\n\n"
                f"Keep the team updated on your findings."
            )
        
        elif signal_type == "request_help":
            return (
                f"🤝 Help request acknowledged.\n\n"
                f"I'm coordinating with the Strategic Commander to assign resources."
            )
        
        else:  # info
            return (
                f"✓ Update received. Continue investigation.\n\n"
                f"{classification.get('summary', 'Keep sharing your findings.')}"
            )

    def _suggest_help_team(self, content, current_thread):
        """Suggest which team might help with a blocker"""
        
        content_lower = content.lower()
        
        suggestions = {
            "database": ["query", "sql", "table", "index", "connection pool", "deadlock"],
            "network": ["network", "dns", "tcp", "latency", "timeout", "firewall", "routing"],
            "application": ["code", "application", "service", "api", "endpoint"],
            "cloud": ["aws", "azure", "gcp", "cloud", "s3", "ec2", "lambda"],
            "security": ["security", "auth", "permission", "certificate", "ssl", "tls"],
            "unix": ["linux", "unix", "disk", "memory", "cpu", "process"],
            "windows": ["windows", "iis", ".net", "active directory"],
            "middleware": ["kafka", "rabbitmq", "redis", "cache", "message queue"],
        }
        
        for team, keywords in suggestions.items():
            if team != current_thread and any(kw in content_lower for kw in keywords):
                return team
        
        return None

    async def resolve_incident(self, resolution_summary=None):
        """Mark incident as resolved"""
        
        incident = await self.repo.get_incident(self.incident_id)
        if not incident:
            return None
        
        incident.status = "resolved"
        incident.resolved_at = incident.timeline[-1].timestamp if incident.timeline else None
        
        # Update all team states
        for team_state in incident.team_states.values():
            team_state.status = TeamStatus.RESOLVED
        
        # Complete all pending actions
        for action in incident.actions:
            action_status = action.status.value if hasattr(action.status, 'value') else action.status
            if action_status != ActionStatus.COMPLETED.value:
                action.status = ActionStatus.COMPLETED
                action.completed_at = incident.resolved_at
        
        summary = (
            incident.hypothesis.root_cause
            if incident.hypothesis else "Root cause under investigation"
        )
        
        if resolution_summary:
            summary = resolution_summary
        
        incident.timeline.append(
            TimelineEvent(
                event_type="resolution",
                description=f"Incident resolved. Root cause: {summary}",
                severity="critical"
            )
        )
        
        await self.repo.update_incident(incident)
        
        # Post resolution message
        msg = Message(
            incident_id=self.incident_id,
            thread="summary",
            sender="Incident Commander",
            sender_type="system",
            content=(
                f"✅ INCIDENT RESOLVED\n\n"
                f"Root Cause:\n{summary}\n\n"
                f"All teams: Begin documenting lessons learned for postmortem."
            ),
            priority=MessagePriority.CRITICAL,
            is_critical=True
        )
        
        await self.repo.add_message(msg)
        
        return msg

    async def update_action_status(self, action_id, status, notes=None):
        """Update status of an action"""
        
        incident = await self.repo.get_incident(self.incident_id)
        if not incident:
            return None
        
        action = next((a for a in incident.actions if a.id == action_id), None)
        if not action:
            return None
        
        old_status = action.status
        action.status = status
        
        if status == ActionStatus.COMPLETED:
            action.completed_at = incident.timeline[-1].timestamp if incident.timeline else None
        
        incident.timeline.append(
            TimelineEvent(
                event_type="action_update",
                description=f"{action.assigned_to.upper()}: Action {status.value if hasattr(status, 'value') else status} - {action.description[:50]}",
                team=action.assigned_to,
                metadata={"action_id": action_id, "notes": notes}
            )
        )
        
        await self.repo.update_incident(incident)
        
        # Notify team
        msg = Message(
            incident_id=self.incident_id,
            thread=action.assigned_to,
            sender="Strategic Commander",
            sender_type="commander",
            content=f"📋 Action updated: {old_status.value if hasattr(old_status, 'value') else old_status} → {status.value if hasattr(status, 'value') else status}\n{action.description}\n{notes or ''}",
            priority=MessagePriority.NORMAL
        )
        
        await self.repo.add_message(msg)
        
        return action