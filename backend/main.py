from fastapi import FastAPI, HTTPException
from models import Incident
from repository import Repository
from agents import OrchestratorAgent
from executive_summary import ExecutiveSummaryGenerator
from db_models import Base
from database import engine
import uuid

app = FastAPI(title="Strategic AI War Room")
repo = Repository()


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/incidents")
async def create_incident(payload: dict):
    incident = Incident(
        id=str(uuid.uuid4()),
        title=payload["title"],
        description=payload["description"],
        severity=payload.get("severity", "P1"),
        affected_system=payload["affected_system"]
    )
    await repo.create_incident(incident)
    return incident


@app.get("/incidents")
async def list_incidents():
    return await repo.list_incidents()


@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    incident = await repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(404)
    return incident


@app.post("/incidents/{incident_id}/message")
async def add_message(incident_id: str, payload: dict):
    orchestrator = OrchestratorAgent(incident_id, repo)
    return await orchestrator.process_engineer_input(
        payload["thread"],
        payload["engineer_name"],
        payload["content"]
    )


@app.get("/incidents/{incident_id}/threads/{thread}")
async def get_thread_messages(incident_id: str, thread: str):
    return await repo.get_messages(incident_id, thread)


@app.get("/incidents/{incident_id}/findings")
async def get_findings(incident_id: str):
    return await repo.get_findings(incident_id)


@app.get("/incidents/{incident_id}/timeline")
async def get_timeline(incident_id: str):
    incident = await repo.get_incident(incident_id)
    return incident.timeline if incident else []


@app.get("/incidents/{incident_id}/executive-summary")
async def executive_summary(incident_id: str):
    incident = await repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(404)

    generator = ExecutiveSummaryGenerator()
    summary = await generator.generate(incident)
    await repo.update_incident(incident)

    return {"summary": summary}


@app.post("/incidents/{incident_id}/resolve")
async def resolve(incident_id: str):
    orchestrator = OrchestratorAgent(incident_id, repo)
    return await orchestrator.resolve_incident()