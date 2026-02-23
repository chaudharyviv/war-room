import os
from openai import AsyncOpenAI

MODEL = "gpt-4o"
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ExecutiveSummaryGenerator:

    async def generate(self, incident):

        if (
            incident.hypothesis
            and incident.executive_summary
            and incident.executive_summary_version == incident.hypothesis.version
        ):
            return incident.executive_summary

        prompt = f"""
Generate executive update under 120 words.

Incident: {incident.title}
Severity: {incident.severity}
System: {incident.affected_system}
Root Cause: {incident.hypothesis.root_cause if incident.hypothesis else "Investigating"}
Confidence: {incident.hypothesis.confidence if incident.hypothesis else 0}
Status: {incident.status}
"""

        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300
            )
            summary = response.choices[0].message.content
        except Exception as e:
            # Return cached summary if AI call fails
            if incident.executive_summary:
                return incident.executive_summary
            raise RuntimeError(f"Failed to generate executive summary: {e}")

        incident.executive_summary = summary
        incident.executive_summary_version = float(incident.hypothesis.version) if incident.hypothesis else 0.0

        return summary