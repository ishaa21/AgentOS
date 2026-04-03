# AgentOS — Multi-Agent Task Management System

A fully implemented multi-agent AI system built with FastAPI, SQLAlchemy, and Google Gemini. Features a REST API and a frontend dashboard.

## Architecture

```text
User
 │
 ▼
Primary Orchestrator Agent (Gemini)
 │           │           │
 ▼           ▼           ▼
Task Agent  Calendar    Notes Agent
(MCP)       Agent (MCP) (MCP)
 │           │           │
 ▼           ▼           ▼
 ──────── SQLite DB ────────
  tasks | events | notes | agent_logs
```

## Features
- **Orchestrator Agent**: Coordinates Task, Calendar, and Notes sub-agents via 11 specialized MCP tools.
- **Frontend Dashboard**: Interactive UI served seamlessly from the FastAPI backend.
- **Database**: Bundled SQLite locally, easily configurable for PostgreSQL in production.
- **Multi-step Workflows**: Agents chain multiple tool calls autonomously in a single request.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Google Gemini API key
export GOOGLE_API_KEY="your_api_key_here"

# 3. Run the server
uvicorn multi_agent_backend:app --reload --port 8000

# 4. Open the application
# App Dashboard: http://localhost:8000
# API Swagger Docs: http://localhost:8000/docs
```

## Docker Deployment

```bash
docker build -t agentos .
docker run -p 8080:8080 -e GOOGLE_API_KEY="your_api_key_here" -e PORT=8080 agentos
```
*(Note: Cloud Run utilizes the `PORT` environment variable which defaults to 8080)*

## API Endpoints Summary

- **POST /api/chat** — Main orchestrator natural language processing
- **GET, POST, PUT, DELETE /api/tasks** — Task management
- **GET, POST, DELETE /api/events** — Calendar scheduling
- **GET, POST, DELETE /api/notes** — Knowledge base
- **GET /api/logs** — Agent execution tracing
- **GET /health** — System health check

## Example Multi-Step Workflow

**User:** *"Set up project kickoff for next Monday — schedule a 2hr meeting, create prep tasks, and save an agenda note"*

**Orchestrator Flow:**
1. Checks calendar with `check_availability`.
2. Schedules the meeting with `create_event`.
3. Sets up prep duties using `create_task`.
4. Saves an agenda using `create_note`.

All operations occur in a single `/api/chat` request via the orchestrator coordinating the workflow.

**Link : **https://agentos-api-929901262447.us-central1.run.app/
