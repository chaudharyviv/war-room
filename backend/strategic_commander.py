# ============================================================
# strategic_commander.py — Strategic Version
# ============================================================

import os
import json
from openai import AsyncOpenAI
from models import Hypothesis, TimelineEvent

MODEL = "gpt-4o"
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class StrategicCommander:

    def __init__(self, incident_id, state):
        self.incident_id = incident_id
        self.state = state

    async def analyze_and_direct(self):

        incident = await self.state.get_incident(self.incident_id)
        findings = await self.state.get_findings(self.incident_id)

        if not incident:
            return None

        findings_text = "\n".join([
            f"[{f.thread}] {f.engineer}: {f.raw_text}"
            for f in findings[-20:]
        ])

        hypothesis_text = (
            incident.hypothesis.root_cause
            if incident.hypothesis else "None"
        )

        prompt = f"""
You are an enterprise Incident Commander.

Incident: {incident.title}
System: {incident.affected_system}
Severity: {incident.severity}

Current Hypothesis: {hypothesis_text}

Recent Findings:
{findings_text}

Return STRICT JSON:

{{
  "updated_hypothesis": "string or null",
  "confidence": 0.0-1.0,
  "directives": [
      {{"team": "database", "instruction": "string"}}
  ],
  "escalate": true/false
}}
"""

        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=700
        )

        try:
            parsed = json.loads(response.choices[0].message.content)
        except:
            return None

        await self._apply(parsed, incident)

    async def _apply(self, result, incident):

        if result.get("updated_hypothesis"):
            if not incident.hypothesis:
                incident.hypothesis = Hypothesis(
                    root_cause=result["updated_hypothesis"],
                    confidence=result.get("confidence", 0.5)
                )
            else:
                incident.hypothesis.version += 1
                incident.hypothesis.root_cause = result["updated_hypothesis"]
                incident.hypothesis.confidence = result.get("confidence", 0.5)

        for directive in result.get("directives", []):
            incident.timeline.append(
                TimelineEvent(
                    event_type="action",
                    description=f"{directive['team'].upper()}: {directive['instruction']}"
                )
            )

        if result.get("escalate"):
            if "vendor" not in incident.threads:
                idx = incident.threads.index("summary")
                incident.threads.insert(idx, "vendor")

        await self.state.update_incident(incident)