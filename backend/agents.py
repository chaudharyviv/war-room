# ============================================================
# agents.py
# ============================================================

import os
import json
from openai import AsyncOpenAI
from models import Message, Finding
from strategic_commander import StrategicCommander

MODEL = "gpt-4o"
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def safe_llm_call(messages, response_format=None, max_tokens=500):
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=max_tokens,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()
    except:
        return None


class OrchestratorAgent:

    def __init__(self, incident_id, repo):
        self.incident_id = incident_id
        self.repo = repo

    async def process_engineer_input(self, thread, engineer_name, content):

        signal_type = "new_finding"
        confidence = 0.6

        finding = Finding(
            thread=thread,
            engineer=engineer_name,
            raw_text=content,
            signal_type=signal_type,
            confidence=confidence
        )

        await self.repo.add_finding(self.incident_id, finding)

        if signal_type in ["root_cause_candidate", "blocker"]:
            commander = StrategicCommander(self.incident_id, self.repo)
            await commander.analyze_and_direct()

        reply = Message(
            incident_id=self.incident_id,
            thread=thread,
            sender=f"{thread.title()} Agent",
            sender_type="agent",
            content="Update received. Continue investigation."
        )

        await self.repo.add_message(reply)

        return {"agent_reply": reply}

    async def resolve_incident(self):

        incident = await self.repo.get_incident(self.incident_id)
        incident.status = "resolved"

        summary = (
            incident.hypothesis.root_cause
            if incident.hypothesis else "Under investigation"
        )

        await self.repo.update_incident(incident)

        return Message(
            incident_id=self.incident_id,
            thread="summary",
            sender="WarRoom Bot",
            sender_type="orchestrator",
            content=f"Incident resolved.\n\nRoot Cause:\n{summary}"
        )