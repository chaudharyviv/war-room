# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Strategic AI War Room is an enterprise incident management platform with AI-powered multi-agent coordination. It handles P0-P4 severity incidents across multiple teams using OpenAI GPT-4 for intelligent analysis and coordination.

## Development Commands

### Backend (FastAPI)
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Streamlit)
```bash
pip install -r frontend/requirements_frontend.txt
streamlit run frontend/app.py --server.enableCORS false --server.enableXsrfProtection false
```

### Required Environment Variables
- `OPENAI_API_KEY` — GPT-4 calls (all AI agents)
- `DATABASE_URL` — PostgreSQL connection string (asyncpg format)
- `BACKEND_URL` — Frontend uses this to call the API (default: `http://localhost:8000`)

## Architecture

### Backend (`backend/`)

| File | Role |
|------|------|
| `main.py` | FastAPI app, all REST endpoints |
| `models.py` | Pydantic v2 data models and enums |
| `db_models.py` | SQLAlchemy ORM models |
| `database.py` | Async PostgreSQL connection + schema migrations |
| `repository.py` | Data access layer (all CRUD) |
| `agents.py` | `OrchestratorAgent` — classifies engineer signals, triggers downstream agents |
| `strategic_commander.py` | `StrategicCommander` — analyzes findings, forms hypotheses, assigns actions |
| `agent_collaboration.py` | `SelectiveCollaboration` — focused 2–3 team dialogue workflow |
| `executive_summary.py` | `ExecutiveSummaryGenerator` — cached AI summaries (<120 words) |

### Agent Flow

1. Engineer posts a message → `POST /incidents/{id}/message`
2. `OrchestratorAgent` classifies the signal and updates team states
3. `POST /incidents/{id}/analyze` triggers `StrategicCommander`
4. `StrategicCommander` forms/updates hypotheses, assigns actions, detects blockers
5. `SelectiveCollaboration` fires only when 2–3 teams each have 3+ findings
6. `ExecutiveSummaryGenerator` produces a cached summary keyed on hypothesis version

### Data Models (key enums)
- `IncidentSeverity`: P0–P4
- `IncidentStatus`: active, investigating, mitigating, resolved
- `TeamStatus`: standby, investigating, blocked, found_issue
- `ActionStatus`: pending, in_progress, completed, blocked

### Database
PostgreSQL with JSONB columns for flexible fields (team states, timeline, actions, hypothesis, collaboration data). Tables: `incidents`, `messages`, `findings`. Schema migrations run automatically on startup via `database.py`.

### Frontend (`frontend/app.py`)
Single Streamlit file. Pages: Dashboard → Create Incident → Active Incidents → Resolved Incidents → Incident Details. Uses `httpx`/`requests` to call the backend API.

## Deployment
Render.com config is in `backend/render.yaml`. Backend runs as a Python web service; database is PostgreSQL (free tier).
