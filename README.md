# AgentOS — Multi-Agent Task Management System

A fully implemented multi-agent AI system built with FastAPI, SQLAlchemy, and Claude.

## Architecture

```
User
 │
 ▼
Primary Orchestrator Agent (Claude)
 │           │           │
 ▼           ▼           ▼
Task Agent  Calendar    Notes Agent
(MCP)       Agent (MCP) (MCP)
 │           │           │
 ▼           ▼           ▼
 ──────── SQLite DB ────────
  tasks | events | notes | agent_logs
```

## Core Requirements — All Fulfilled

| Requirement | Implementation |
|---|---|
| Primary agent + sub-agents | Orchestrator coordinates Task, Calendar, Notes agents |
| Structured database | SQLite via SQLAlchemy — 4 tables |
| MCP tool integration | 11 MCP tools across 3 agents |
| Multi-step workflows | Agentic loop with tool chaining |
| API-based deployment | FastAPI REST API on port 8000 |

## Quick Start

```bash
# 1. Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic anthropic python-dateutil

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run the server
python multi_agent_backend.py

# 4. Open API docs
open http://localhost:8000/docs
```

## API Endpoints

### Orchestrator
```
POST /api/chat
Body: { "message": "Schedule a standup tomorrow at 9am and create a prep task" }
```

### Tasks
```
GET    /api/tasks           — List all tasks
POST   /api/tasks           — Create task
PUT    /api/tasks/{id}      — Update task
DELETE /api/tasks/{id}      — Delete task
```

### Calendar
```
GET    /api/events          — List events
POST   /api/events          — Create event
DELETE /api/events/{id}     — Delete event
```

### Notes
```
GET    /api/notes           — List/search notes
POST   /api/notes           — Create note
DELETE /api/notes/{id}      — Delete note
```

### System
```
GET /api/logs    — Agent execution logs
GET /api/agents  — Agent registry
GET /api/stats   — System statistics
GET /health      — Health check
```

## MCP Tools (11 total)

### Task Agent
- `create_task(title, priority, due_date, status)`
- `list_tasks(status, priority)`
- `update_task(task_id, ...fields)`
- `delete_task(task_id)`

### Calendar Agent
- `create_event(title, date, time, duration_minutes, attendees)`
- `list_events(date, start_date, end_date)`
- `check_availability(date, time, duration_minutes)`
- `delete_event(event_id)`

### Notes Agent
- `create_note(title, content, tags)`
- `list_notes(search, tag)`
- `delete_note(note_id)`

## Database Schema

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title VARCHAR(500),
    priority VARCHAR(20),   -- low | medium | high
    due_date VARCHAR(20),
    status VARCHAR(20),     -- pending | in_progress | done
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    title VARCHAR(500),
    date VARCHAR(20),
    time VARCHAR(10),
    duration_minutes INTEGER,
    attendees TEXT,
    notes TEXT,
    created_at DATETIME
);

CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    title VARCHAR(500),
    content TEXT,
    tags VARCHAR(500),
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE agent_logs (
    id INTEGER PRIMARY KEY,
    agent VARCHAR(100),
    action VARCHAR(200),
    detail TEXT,
    status VARCHAR(20),
    created_at DATETIME
);
```

## Example Multi-Step Workflow

**User:** "Set up project kickoff for next Monday — schedule a 2hr meeting, create prep tasks, and save an agenda note"

**Orchestrator flow:**
1. `check_availability(date="2026-04-06", time="10:00", duration=120)` → Calendar Agent
2. `create_event(title="Project Kickoff", date="2026-04-06", time="10:00", duration_minutes=120)` → Calendar Agent
3. `create_task(title="Prepare kickoff deck", priority="high", due_date="2026-04-05")` → Task Agent
4. `create_task(title="Send meeting invites", priority="medium", due_date="2026-04-04")` → Task Agent
5. `create_note(title="Kickoff Agenda", content="1. Intro 2. Goals 3. Timeline 4. Q&A")` → Notes Agent

All 5 tool calls happen in a single `/api/chat` request, with the Orchestrator coordinating the full workflow.
