# ============================================================
# main.py — Enhanced War Room Backend API
# ============================================================

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
import logging
import traceback

from models import (
    Incident, CreateIncidentRequest, AddMessageRequest,
    UpdateActionRequest, TeamStatusUpdate, IncidentStatus,
    ActionStatus
)
from repository import Repository
from agents import OrchestratorAgent
from executive_summary import ExecutiveSummaryGenerator
from strategic_commander import StrategicCommander
from db_models import Base
from database import engine, run_schema_migrations

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Strategic AI War Room",
    description="Enterprise Incident Management System with AI Coordination",
    version="2.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repo = Repository()


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to return detailed errors"""
    logger.error(f"Global exception: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": exc.__class__.__name__,
            "message": "Internal server error occurred. Check server logs for details."
        }
    )


@app.on_event("startup")
async def startup():
    """Initialize database"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await run_schema_migrations()

        # Test database connection
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info(f"✅ Database connection successful: {result.scalar()}")

        logger.info("✅ War Room Backend initialized")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error(traceback.format_exc())


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "operational", "service": "war-room"}


# ─────────────────────────────────────────────
# INCIDENT MANAGEMENT
# ─────────────────────────────────────────────

@app.post("/incidents", response_model=Incident)
async def create_incident(request: CreateIncidentRequest):
    """Create new incident and initialize war room"""
    
    try:
        incident = Incident(
            id=str(uuid.uuid4()),
            title=request.title,
            description=request.description,
            severity=request.severity,
            affected_system=request.affected_system,
            incident_commander=request.incident_commander,
            impact=request.impact,
            status=IncidentStatus.DECLARED
        )

        await repo.create_incident(incident)
        await repo.initialize_war_room(incident)
        
        # Initial Strategic Commander analysis (non-blocking)
        try:
            commander = StrategicCommander(incident.id, repo)
            await commander.analyze_and_direct()
        except Exception as e:
            logger.error(f"Initial commander analysis failed: {e}")
            # Don't fail the incident creation if commander analysis fails
        
        logger.info(f"✅ Incident created: {incident.id}")
        return incident
        
    except Exception as e:
        logger.error(f"❌ Failed to create incident: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create incident: {str(e)}")


@app.get("/incidents")
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List all incidents with optional status filter"""
    try:
        incidents = await repo.list_incidents(status)
        return incidents
    except Exception as e:
        logger.error(f"❌ Failed to list incidents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve incidents")


@app.get("/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str):
    """Get full incident details"""
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        return incident
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve incident")


@app.delete("/incidents/{incident_id}")
async def delete_incident(incident_id: str):
    """Delete incident and all associated messages and findings"""
    try:
        deleted = await repo.delete_incident(incident_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete incident")
        return {"status": "deleted", "id": incident_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# MESSAGING & COMMUNICATION
# ─────────────────────────────────────────────

@app.post("/incidents/{incident_id}/message")
async def add_message(incident_id: str, request: AddMessageRequest):
    """Engineer posts update to thread"""
    
    try:
        orchestrator = OrchestratorAgent(incident_id, repo)
        result = await orchestrator.process_engineer_input(
            request.thread,
            request.engineer_name,
            request.content
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Incident not found")
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to add message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")


@app.get("/incidents/{incident_id}/threads/{thread}")
async def get_thread_messages(
    incident_id: str, 
    thread: str,
    limit: int = Query(100, ge=1, le=500)
):
    """Get messages from specific thread"""
    try:
        messages = await repo.get_messages(incident_id, thread, limit)
        return messages
    except Exception as e:
        logger.error(f"❌ Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")


@app.get("/incidents/{incident_id}/messages")
async def get_all_messages(incident_id: str):
    """Get all messages across all threads"""
    try:
        messages = await repo.get_all_messages(incident_id)
        return messages
    except Exception as e:
        logger.error(f"❌ Failed to get all messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")


# ─────────────────────────────────────────────
# FINDINGS & INVESTIGATION
# ─────────────────────────────────────────────

@app.get("/incidents/{incident_id}/findings")
async def get_findings(
    incident_id: str,
    thread: Optional[str] = Query(None, description="Filter by thread")
):
    """Get investigation findings"""
    try:
        findings = await repo.get_findings(incident_id, thread)
        return findings
    except Exception as e:
        logger.error(f"❌ Failed to get findings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve findings")


# ─────────────────────────────────────────────
# TEAM COORDINATION
# ─────────────────────────────────────────────

@app.get("/incidents/{incident_id}/team-states")
async def get_team_states(incident_id: str):
    """Get current state of all teams"""
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404)
        
        return incident.team_states
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get team states: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team states")


@app.post("/incidents/{incident_id}/team-status")
async def update_team_status(incident_id: str, request: TeamStatusUpdate):
    """Update team status (blocked, investigating, etc.)"""
    
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404)
        
        if request.team in incident.team_states:
            incident.team_states[request.team].status = request.status
            incident.team_states[request.team].blocked_reason = request.blocked_reason
            incident.team_states[request.team].needs_help_from = request.needs_help_from
            
            await repo.update_incident(incident)
            
            # Trigger commander if team is blocked (non-blocking)
            if request.status == "blocked":
                try:
                    commander = StrategicCommander(incident_id, repo)
                    await commander.analyze_and_direct()
                except Exception as e:
                    logger.error(f"Commander analysis failed after status update: {e}")
        
        return incident.team_states[request.team]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update team status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update team status")


# ─────────────────────────────────────────────
# ACTIONS & TASKS
# ─────────────────────────────────────────────

@app.get("/incidents/{incident_id}/actions")
async def get_actions(
    incident_id: str,
    status: Optional[str] = Query(None, description="Filter by status")
):
    """Get all actions for incident"""
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404)
        
        actions = incident.actions
        
        if status:
            actions = [a for a in actions if a.status.value == status]
        
        return actions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get actions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve actions")


@app.post("/incidents/{incident_id}/actions/{action_id}")
async def update_action(
    incident_id: str,
    action_id: str,
    request: UpdateActionRequest
):
    """Update action status"""
    
    try:
        orchestrator = OrchestratorAgent(incident_id, repo)
        result = await orchestrator.update_action_status(
            action_id,
            request.status,
            request.notes
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Action not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update action: {e}")
        raise HTTPException(status_code=500, detail="Failed to update action")


# ─────────────────────────────────────────────
# TIMELINE & HISTORY
# ─────────────────────────────────────────────

@app.get("/incidents/{incident_id}/timeline")
async def get_timeline(incident_id: str):
    """Get incident timeline"""
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404)
        return incident.timeline
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get timeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve timeline")


# ─────────────────────────────────────────────
# STRATEGIC COMMANDER
# ─────────────────────────────────────────────

@app.post("/incidents/{incident_id}/analyze")
async def trigger_analysis(incident_id: str):
    """Manually trigger Strategic Commander analysis"""
    try:
        commander = StrategicCommander(incident_id, repo)
        result = await commander.analyze_and_direct()
        
        if not result:
            raise HTTPException(status_code=500, detail="Analysis failed")
        
        return {"status": "analysis_complete", "result": result}
        
    except Exception as e:
        logger.error(f"❌ Failed to trigger analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/incidents/{incident_id}/hypothesis")
async def get_hypothesis(incident_id: str):
    """Get current hypothesis"""
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404)
        
        return incident.hypothesis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get hypothesis: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hypothesis")


# ─────────────────────────────────────────────
# EXECUTIVE SUMMARY
# ─────────────────────────────────────────────

@app.get("/incidents/{incident_id}/executive-summary")
async def get_executive_summary(incident_id: str):
    """Generate/get executive summary"""
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404)

        generator = ExecutiveSummaryGenerator()
        summary = await generator.generate(incident)
        await repo.update_incident(incident)

        return {"summary": summary}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to generate executive summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate executive summary")


# ─────────────────────────────────────────────
# INCIDENT LIFECYCLE
# ─────────────────────────────────────────────

@app.post("/incidents/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    resolution_summary: Optional[str] = None
):
    """Mark incident as resolved"""
    try:
        orchestrator = OrchestratorAgent(incident_id, repo)
        result = await orchestrator.resolve_incident(resolution_summary)
        
        if not result:
            raise HTTPException(status_code=404)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to resolve incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve incident")


@app.post("/incidents/{incident_id}/escalate")
async def escalate_incident(
    incident_id: str,
    reason: str,
    escalate_to: str = "vendor"
):
    """Escalate incident"""
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404)
        
        if escalate_to == "vendor":
            incident.escalated_to_vendor = True
            if "vendor" not in incident.threads:
                incident.threads.insert(len(incident.threads) - 1, "vendor")
        
        await repo.update_incident(incident)
        
        # Trigger commander to handle escalation (non-blocking)
        try:
            commander = StrategicCommander(incident_id, repo)
            await commander.analyze_and_direct()
        except Exception as e:
            logger.error(f"Commander analysis failed after escalation: {e}")
        
        return {"status": "escalated", "escalate_to": escalate_to}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to escalate incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to escalate incident")


# ─────────────────────────────────────────────
# STATISTICS & METRICS
# ─────────────────────────────────────────────

@app.get("/incidents/{incident_id}/stats")
async def get_incident_stats(incident_id: str):
    """Get incident statistics"""
    try:
        incident = await repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404)
        
        findings = await repo.get_findings(incident_id)
        messages = await repo.get_all_messages(incident_id)
        
        # Calculate stats
        teams_active = sum(1 for ts in incident.team_states.values() 
                          if ts.status != "standby")
        
        teams_blocked = sum(1 for ts in incident.team_states.values() 
                           if ts.status == "blocked")
        
        actions_pending = sum(1 for a in incident.actions 
                             if a.status == ActionStatus.PENDING)
        
        actions_completed = sum(1 for a in incident.actions 
                               if a.status == ActionStatus.COMPLETED)
        
        return {
            "total_findings": len(findings),
            "total_messages": len(messages),
            "teams_active": teams_active,
            "teams_blocked": teams_blocked,
            "actions_pending": actions_pending,
            "actions_completed": actions_completed,
            "hypothesis_confidence": incident.hypothesis.confidence if incident.hypothesis else 0,
            "timeline_events": len(incident.timeline)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get incident stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve incident statistics")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)