# ============================================================
# agent_collaboration.py — Selective Multi-Agent Dialogue
# ============================================================

import os
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from openai import AsyncOpenAI
from models import Message, MessagePriority, TimelineEvent

logger = logging.getLogger(__name__)

MODEL = "gpt-4o"
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None


class CollaborationDialogue:
    """Represents a message in the team debate"""
    def __init__(
        self, 
        team: str, 
        message_type: str,  # position, critique, response, consensus
        content: str, 
        confidence: float = 0.0
    ):
        self.team = team
        self.message_type = message_type
        self.content = content
        self.confidence = confidence
        self.timestamp = datetime.utcnow()


class SelectiveCollaboration:
    """
    Manages focused collaboration between 2-3 key stakeholder teams.
    
    Only triggers when:
    - 2-3 teams have significant findings
    - Their hypotheses conflict or overlap
    - Commander detects need for discussion
    
    Workflow:
    1. Commander identifies key stakeholder teams
    2. Teams present positions
    3. Teams critique each other
    4. Teams respond and revise
    5. Commander facilitates consensus
    """
    
    def __init__(self, incident_id: str, repo):
        self.incident_id = incident_id
        self.repo = repo
        self.dialogue_messages: List[CollaborationDialogue] = []
        self.participating_teams: List[str] = []
        self.consensus_reached = False
        self.final_consensus: Optional[Dict] = None
        
    async def should_trigger_collaboration(
        self, 
        incident, 
        findings_by_team: Dict[str, List]
    ) -> Optional[List[str]]:
        """
        Determine if collaboration is needed and which teams should participate.
        
        Returns:
            List of 2-3 team names that should collaborate, or None if not needed
        """
        
        if not client:
            return None
        
        # Filter teams with significant findings (3+ findings)
        active_teams = {
            team: findings 
            for team, findings in findings_by_team.items() 
            if len(findings) >= 3 and team != "summary"
        }
        
        # Need at least 2 teams with findings
        if len(active_teams) < 2:
            logger.info("Not enough active teams for collaboration")
            return None
        
        # Ask AI to identify key stakeholders
        teams_summary = "\n".join([
            f"{team.upper()}: {len(findings)} findings, "
            f"Latest: {findings[-1].raw_text[:80]}..."
            for team, findings in active_teams.items()
        ])
        
        prompt = f"""You are analyzing an incident to determine if team collaboration is needed.

INCIDENT: {incident.title}
SYSTEM: {incident.affected_system}

ACTIVE TEAMS AND THEIR FINDINGS:
{teams_summary}

Determine if 2-3 specific teams should collaborate because:
- Their findings overlap or conflict
- They're investigating the same component
- One team's findings affect another's area

Return STRICT JSON:
{{
  "collaboration_needed": true/false,
  "participating_teams": ["team1", "team2", "team3"] or [],
  "reason": "Why these teams should collaborate",
  "conflict_area": "What they're conflicting about"
}}

Only recommend collaboration if there's genuine overlap or conflict.
Maximum 3 teams to keep discussion focused.
"""
        
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if result.get("collaboration_needed") and result.get("participating_teams"):
                teams = result["participating_teams"][:3]  # Max 3 teams
                
                if len(teams) >= 2:
                    logger.info(f"🤝 Collaboration recommended for teams: {teams}")
                    logger.info(f"Reason: {result.get('reason')}")
                    return teams
            
            return None
            
        except Exception as e:
            logger.error(f"Error determining collaboration need: {e}")
            return None
    
    async def conduct_collaboration(
        self, 
        incident, 
        participating_teams: List[str],
        findings_by_team: Dict[str, List]
    ) -> Optional[Dict[str, Any]]:
        """
        Conduct focused collaboration between selected teams.
        
        Args:
            participating_teams: List of 2-3 team names
            findings_by_team: Findings for all teams
            
        Returns:
            Collaboration result with consensus
        """
        
        if not client:
            return None
        
        self.participating_teams = participating_teams
        
        logger.info(f"🤝 Starting collaboration: {', '.join(participating_teams)}")
        
        # Announce collaboration start
        await self._announce_collaboration_start(incident, participating_teams)
        
        # Round 1: Get initial positions
        positions = await self._gather_positions(incident, participating_teams, findings_by_team)
        
        if not positions or len(positions) < 2:
            logger.warning("Failed to gather positions")
            return None
        
        # Round 2: Teams critique each other
        critiques = await self._exchange_critiques(incident, positions)
        
        # Round 3: Teams respond and revise
        revisions = await self._gather_responses(incident, positions, critiques)
        
        # Final: Commander evaluates and reaches consensus
        consensus = await self._reach_consensus(incident, positions, revisions)
        
        if consensus:
            self.consensus_reached = True
            self.final_consensus = consensus
            
            # Announce consensus
            await self._announce_consensus(incident, consensus)
        
        return consensus
    
    async def _gather_positions(
        self, 
        incident, 
        teams: List[str], 
        findings_by_team: Dict[str, List]
    ) -> List[Dict[str, Any]]:
        """Each participating team states their position"""
        
        positions = []
        
        for team in teams:
            findings = findings_by_team.get(team, [])
            if not findings:
                continue
            
            position = await self._get_team_position(incident, team, findings)
            
            if position:
                positions.append(position)
                
                # Record in dialogue
                self.dialogue_messages.append(
                    CollaborationDialogue(
                        team=team,
                        message_type="position",
                        content=position["hypothesis"],
                        confidence=position["confidence"]
                    )
                )
                
                # Post to team thread
                await self._post_to_thread(
                    team, 
                    f"🧠 **MY POSITION:**\n\n{position['hypothesis']}\n\n"
                    f"**Confidence:** {position['confidence']:.0%}\n\n"
                    f"**Key Evidence:**\n" + "\n".join(f"  • {e}" for e in position['evidence'])
                )
        
        return positions
    
    async def _get_team_position(
        self, 
        incident, 
        team: str, 
        findings: List
    ) -> Optional[Dict[str, Any]]:
        """Get a team's initial hypothesis"""
        
        findings_text = "\n".join([
            f"  [{f.engineer}] {f.raw_text}"
            for f in findings[-5:]
        ])
        
        prompt = f"""You are the {team.upper()} team agent in a collaborative dialogue.

INCIDENT: {incident.title}

YOUR FINDINGS:
{findings_text}

State your position on the root cause. Return STRICT JSON:

{{
  "hypothesis": "Your specific hypothesis",
  "confidence": 0.0-1.0,
  "evidence": ["key evidence 1", "key evidence 2"],
  "reasoning": "Why you believe this"
}}

Be specific and evidence-based.
"""
        
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=500
            )
            
            position = json.loads(response.choices[0].message.content)
            position["team"] = team
            
            return position
            
        except Exception as e:
            logger.error(f"Error getting position from {team}: {e}")
            return None
    
    async def _exchange_critiques(
        self, 
        incident, 
        positions: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Teams critique each other's positions"""
        
        critiques = []
        
        # Each team critiques others
        for i, position in enumerate(positions):
            other_positions = [p for j, p in enumerate(positions) if j != i]
            
            critique = await self._get_critique(incident, position, other_positions)
            
            if critique:
                critiques.append(critique)
                
                # Record in dialogue
                self.dialogue_messages.append(
                    CollaborationDialogue(
                        team=position["team"],
                        message_type="critique",
                        content=critique["critique_text"]
                    )
                )
                
                # Post to threads
                await self._post_to_thread(
                    position["team"],
                    f"💬 **CRITIQUE OF OTHER POSITIONS:**\n\n{critique['critique_text']}"
                )
        
        return critiques
    
    async def _get_critique(
        self, 
        incident, 
        own_position: Dict, 
        other_positions: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Team critiques other positions"""
        
        others_summary = "\n\n".join([
            f"{p['team'].upper()}:\n{p['hypothesis']}\nConfidence: {p['confidence']}"
            for p in other_positions
        ])
        
        prompt = f"""You are the {own_position['team'].upper()} team.

YOUR HYPOTHESIS: {own_position['hypothesis']}

OTHER TEAMS' HYPOTHESES:
{others_summary}

Critique the other positions. Return STRICT JSON:

{{
  "critique_text": "Your technical critique",
  "agreements": ["points where you agree"],
  "disagreements": ["specific conflicts with your findings"],
  "questions": ["questions for other teams"]
}}

Be constructive and specific.
"""
        
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            
            critique = json.loads(response.choices[0].message.content)
            critique["from_team"] = own_position["team"]
            
            return critique
            
        except Exception as e:
            logger.error(f"Error getting critique: {e}")
            return None
    
    async def _gather_responses(
        self, 
        incident, 
        positions: List[Dict], 
        critiques: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Teams respond to critiques and revise if needed"""
        
        revisions = []
        
        for position in positions:
            # Get critiques from other teams
            relevant_critiques = [
                c for c in critiques 
                if c.get("from_team") != position["team"]
            ]
            
            if not relevant_critiques:
                continue
            
            revision = await self._get_revision(incident, position, relevant_critiques)
            
            if revision:
                revisions.append(revision)
                
                # Record in dialogue
                self.dialogue_messages.append(
                    CollaborationDialogue(
                        team=position["team"],
                        message_type="response",
                        content=revision["revised_hypothesis"],
                        confidence=revision["revised_confidence"]
                    )
                )
                
                # Post to thread
                await self._post_to_thread(
                    position["team"],
                    f"🔄 **MY RESPONSE:**\n\n"
                    f"**Revised Hypothesis:** {revision['revised_hypothesis']}\n\n"
                    f"**Revised Confidence:** {revision['revised_confidence']:.0%}\n\n"
                    f"**Response:** {revision['response_text']}"
                )
        
        return revisions
    
    async def _get_revision(
        self, 
        incident, 
        position: Dict, 
        critiques: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Team revises position based on critiques"""
        
        critiques_text = "\n\n".join([
            f"CRITIQUE:\n{c['critique_text']}"
            for c in critiques
        ])
        
        prompt = f"""You are the {position['team'].upper()} team.

YOUR ORIGINAL HYPOTHESIS: {position['hypothesis']}
YOUR CONFIDENCE: {position['confidence']}

CRITIQUES FROM OTHER TEAMS:
{critiques_text}

Respond and revise if needed. Return STRICT JSON:

{{
  "response_text": "Your response to critiques",
  "revised_hypothesis": "Updated hypothesis (or same if unchanged)",
  "revised_confidence": 0.0-1.0,
  "changed": true/false,
  "reason_for_change": "Why you revised or why you maintained position"
}}

Be honest - revise if critiques are valid, defend if not.
"""
        
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            revision = json.loads(response.choices[0].message.content)
            revision["team"] = position["team"]
            
            return revision
            
        except Exception as e:
            logger.error(f"Error getting revision: {e}")
            return None
    
    async def _reach_consensus(
        self, 
        incident, 
        positions: List[Dict], 
        revisions: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Commander evaluates dialogue and reaches consensus"""
        
        positions_text = "\n\n".join([
            f"{p['team'].upper()} (Initial):\n{p['hypothesis']}\nConfidence: {p['confidence']}"
            for p in positions
        ])
        
        revisions_text = "\n\n".join([
            f"{r['team'].upper()} (Revised):\n{r['revised_hypothesis']}\n"
            f"Confidence: {r['revised_confidence']}\nChanged: {r['changed']}"
            for r in revisions
        ]) if revisions else "No revisions made"
        
        prompt = f"""You are the Strategic Commander evaluating team collaboration.

INITIAL POSITIONS:
{positions_text}

REVISED POSITIONS:
{revisions_text}

Reach a consensus. Return STRICT JSON:

{{
  "consensus_hypothesis": "Final agreed-upon root cause",
  "confidence": 0.0-1.0,
  "supporting_teams": ["team1", "team2"],
  "key_evidence": ["evidence supporting consensus"],
  "consensus_type": "unanimous|majority|commander_decision",
  "reasoning": "How you reached this consensus"
}}

Favor unanimous agreement. If teams converged, use their shared hypothesis.
If still divergent, make best judgment based on evidence.
"""
        
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600
            )
            
            consensus = json.loads(response.choices[0].message.content)
            consensus["participating_teams"] = self.participating_teams
            
            return consensus
            
        except Exception as e:
            logger.error(f"Error reaching consensus: {e}")
            return None
    
    # ─────────────────────────────────────────────
    # Messaging Methods
    # ─────────────────────────────────────────────
    
    async def _announce_collaboration_start(self, incident, teams: List[str]):
        """Announce collaboration is starting"""
        
        msg = Message(
            incident_id=self.incident_id,
            thread="summary",
            sender="Strategic Commander",
            sender_type="commander",
            content=(
                f"🤝 **TEAM COLLABORATION INITIATED**\n\n"
                f"Teams {', '.join([t.upper() for t in teams])} have been identified as key stakeholders.\n\n"
                f"These teams will engage in collaborative dialogue to reach consensus on the root cause.\n\n"
                f"**Process:**\n"
                f"1. Each team presents their hypothesis\n"
                f"2. Teams critique each other's positions\n"
                f"3. Teams respond and revise\n"
                f"4. Commander facilitates consensus\n\n"
                f"View the **Team Debate** tab to follow the discussion."
            ),
            priority=MessagePriority.CRITICAL,
            is_critical=True
        )
        
        await self.repo.add_message(msg)
        
        # Add timeline event
        incident.timeline.append(
            TimelineEvent(
                event_type="collaboration_started",
                description=f"Team collaboration initiated: {', '.join(teams)}",
                severity="high",
                metadata={"teams": teams}
            )
        )
    
    async def _post_to_thread(self, team: str, content: str):
        """Post message to team thread"""
        
        msg = Message(
            incident_id=self.incident_id,
            thread=team,
            sender=f"{team.title()} Agent",
            sender_type="agent",
            content=content,
            priority=MessagePriority.HIGH
        )
        
        await self.repo.add_message(msg)
    
    async def _announce_consensus(self, incident, consensus: Dict):
        """Announce consensus has been reached"""
        
        consensus_type_emoji = {
            "unanimous": "✅",
            "majority": "🤝",
            "commander_decision": "⚖️"
        }
        
        emoji = consensus_type_emoji.get(consensus.get("consensus_type"), "✅")
        
        msg = Message(
            incident_id=self.incident_id,
            thread="summary",
            sender="Strategic Commander",
            sender_type="commander",
            content=(
                f"{emoji} **CONSENSUS REACHED**\n\n"
                f"**Root Cause:**\n{consensus['consensus_hypothesis']}\n\n"
                f"**Confidence:** {consensus['confidence']:.0%}\n\n"
                f"**Supporting Teams:** {', '.join([t.upper() for t in consensus['supporting_teams']])}\n\n"
                f"**Type:** {consensus['consensus_type'].replace('_', ' ').title()}\n\n"
                f"**Reasoning:**\n{consensus['reasoning']}"
            ),
            priority=MessagePriority.CRITICAL,
            is_critical=True
        )
        
        await self.repo.add_message(msg)
        
        # Add timeline event
        incident.timeline.append(
            TimelineEvent(
                event_type="consensus_reached",
                description=f"Team consensus: {consensus['consensus_hypothesis'][:100]}...",
                severity="critical",
                metadata={"confidence": consensus['confidence'], "teams": consensus['supporting_teams']}
            )
        )
    
    def get_dialogue_history(self) -> List[Dict[str, Any]]:
        """Get dialogue history for frontend display"""
        
        return [
            {
                "team": msg.team,
                "type": msg.message_type,
                "content": msg.content,
                "confidence": msg.confidence,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in self.dialogue_messages
        ]