"""
Multi-Agent AI Task Management System — Backend
================================================
FastAPI + SQLAlchemy + Google Gemini

Architecture:
  Primary Orchestrator Agent  ──► Task Sub-Agent    (MCP: task_manager)
                              ──► Calendar Sub-Agent (MCP: calendar)
                              ──► Notes Sub-Agent    (MCP: notes)

Run:
  pip install fastapi uvicorn sqlalchemy pydantic google-generativeai python-dateutil
  uvicorn multi_agent_backend:app --reload --port 8000

API Endpoints:
  POST /api/chat          — Main orchestrator endpoint
  GET  /api/tasks         — List all tasks
  POST /api/tasks         — Create a task
  PUT  /api/tasks/{id}    — Update a task
  DELETE /api/tasks/{id}  — Delete a task
  GET  /api/events        — List all events
  POST /api/events        — Create an event
  DELETE /api/events/{id} — Delete an event
  GET  /api/notes         — List all notes
  POST /api/notes         — Create a note
  DELETE /api/notes/{id}  — Delete a note
  GET  /api/logs          — Agent execution logs
  GET  /api/agents        — Agent registry
  GET  /health            — Health check
"""

import asyncio
import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional

import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import (Column, DateTime, Integer, String, Text,
                        create_engine, func)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ─────────────────────────────────────────────
# Google Gemini LLM
# ─────────────────────────────────────────────

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


def call_gemini(prompt: str, system_instruction: str = None) -> str:
    if not GOOGLE_API_KEY:
        return "Google Gemini API key missing. Please set GOOGLE_API_KEY environment variable."

    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI error: {str(e)}"


# ─────────────────────────────────────────────
# Database Setup
# ─────────────────────────────────────────────
# Defaults to bundled SQLite (agentOS.db) for local dev.
# Set DATABASE_URL env var for PostgreSQL/AlloyDB in production.

# Default: use bundled SQLite for zero-config local dev.
# Override via DATABASE_URL env var for PostgreSQL/AlloyDB in production.
_DEFAULT_DB = f"sqlite:///{Path(__file__).parent / 'agentOS.db'}"
DATABASE_URL = os.environ.get("DATABASE_URL", _DEFAULT_DB)

# SQLite settings for local dev; PostgreSQL connection pool for production
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
else:
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    priority = Column(String(20), default="medium")
    due_date = Column(String(20), nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EventModel(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    date = Column(String(20), nullable=False)
    time = Column(String(10), nullable=True)
    duration_minutes = Column(Integer, default=60)
    attendees = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NoteModel(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentLogModel(Base):
    __tablename__ = "agent_logs"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String(100), nullable=False)
    action = Column(String(200), nullable=False)
    detail = Column(Text, nullable=True)
    status = Column(String(20), default="success")
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    priority: str = "medium"
    due_date: Optional[str] = None
    status: str = "pending"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None


class EventCreate(BaseModel):
    title: str
    date: str
    time: Optional[str] = None
    duration_minutes: int = 60
    attendees: Optional[str] = None
    notes: Optional[str] = None


class NoteCreate(BaseModel):
    title: str
    content: Optional[str] = None
    tags: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


# ─────────────────────────────────────────────
# MCP Tool Definitions
# ─────────────────────────────────────────────

MCP_TOOLS = [
    # ── Task Agent Tools ──
    {
        "name": "create_task",
        "description": "Task Agent: Create a new task in the database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                "status": {"type": "string", "enum": ["pending", "in_progress", "done"]}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_tasks",
        "description": "Task Agent: List all tasks, optionally filtered by status or priority.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending", "in_progress", "done", "all"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "all"]}
            }
        }
    },
    {
        "name": "update_task",
        "description": "Task Agent: Update an existing task by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "title": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                "due_date": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "in_progress", "done"]}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "delete_task",
        "description": "Task Agent: Delete a task by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"]
        }
    },
    # ── Calendar Agent Tools ──
    {
        "name": "create_event",
        "description": "Calendar Agent: Schedule a new calendar event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Time in HH:MM format"},
                "duration_minutes": {"type": "integer", "default": 60},
                "attendees": {"type": "string"},
                "notes": {"type": "string"}
            },
            "required": ["title", "date"]
        }
    },
    {
        "name": "list_events",
        "description": "Calendar Agent: List all events, optionally for a specific date or date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            }
        }
    },
    {
        "name": "check_availability",
        "description": "Calendar Agent: Check if a specific time slot is available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "time": {"type": "string"},
                "duration_minutes": {"type": "integer"}
            },
            "required": ["date", "time"]
        }
    },
    {
        "name": "delete_event",
        "description": "Calendar Agent: Delete an event by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "integer"}},
            "required": ["event_id"]
        }
    },
    # ── Notes Agent Tools ──
    {
        "name": "create_note",
        "description": "Notes Agent: Save a new note to the knowledge base.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "string", "description": "Comma-separated tags"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_notes",
        "description": "Notes Agent: List all notes or search by keyword.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search keyword"},
                "tag": {"type": "string"}
            }
        }
    },
    {
        "name": "delete_note",
        "description": "Notes Agent: Delete a note by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"note_id": {"type": "integer"}},
            "required": ["note_id"]
        }
    }
]


# ─────────────────────────────────────────────
# Tool Executor (MCP Handler)
# ─────────────────────────────────────────────

class MCPToolExecutor:
    """Executes MCP tool calls and interacts with the database."""

    def __init__(self, db: Session):
        self.db = db

    def log(self, agent: str, action: str, detail: str, status: str = "success"):
        log_entry = AgentLogModel(agent=agent, action=action, detail=detail, status=status)
        self.db.add(log_entry)
        self.db.commit()

    def execute(self, tool_name: str, tool_input: dict) -> dict:
        """Route tool call to the correct sub-agent handler."""
        handlers = {
            "create_task": self._create_task,
            "list_tasks": self._list_tasks,
            "update_task": self._update_task,
            "delete_task": self._delete_task,
            "create_event": self._create_event,
            "list_events": self._list_events,
            "check_availability": self._check_availability,
            "delete_event": self._delete_event,
            "create_note": self._create_note,
            "list_notes": self._list_notes,
            "delete_note": self._delete_note,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return handler(tool_input)
        except Exception as e:
            self.log("System", f"tool_error:{tool_name}", str(e), "error")
            return {"error": str(e)}

    # ── Task Agent ──

    def _create_task(self, inp: dict) -> dict:
        task = TaskModel(
            title=inp["title"],
            priority=inp.get("priority", "medium"),
            due_date=inp.get("due_date"),
            status=inp.get("status", "pending")
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self.log("Task Agent", "create_task", f'Created task #{task.id}: "{task.title}"')
        return {"success": True, "task_id": task.id, "title": task.title}

    def _list_tasks(self, inp: dict) -> dict:
        q = self.db.query(TaskModel)
        if inp.get("status") and inp["status"] != "all":
            q = q.filter(TaskModel.status == inp["status"])
        if inp.get("priority") and inp["priority"] != "all":
            q = q.filter(TaskModel.priority == inp["priority"])
        tasks = q.order_by(TaskModel.created_at.desc()).all()
        self.log("Task Agent", "list_tasks", f"Retrieved {len(tasks)} tasks")
        return {"tasks": [{"id": t.id, "title": t.title, "priority": t.priority,
                           "due_date": t.due_date, "status": t.status,
                           "created_at": str(t.created_at)} for t in tasks]}

    def _update_task(self, inp: dict) -> dict:
        task = self.db.query(TaskModel).filter(TaskModel.id == inp["task_id"]).first()
        if not task:
            return {"error": f"Task #{inp['task_id']} not found"}
        for field in ["title", "priority", "due_date", "status"]:
            if inp.get(field):
                setattr(task, field, inp[field])
        task.updated_at = datetime.utcnow()
        self.db.commit()
        self.log("Task Agent", "update_task", f'Updated task #{task.id}: "{task.title}"')
        return {"success": True, "task_id": task.id}

    def _delete_task(self, inp: dict) -> dict:
        task = self.db.query(TaskModel).filter(TaskModel.id == inp["task_id"]).first()
        if not task:
            return {"error": f"Task #{inp['task_id']} not found"}
        self.db.delete(task)
        self.db.commit()
        self.log("Task Agent", "delete_task", f'Deleted task #{inp["task_id"]}')
        return {"success": True}

    # ── Calendar Agent ──

    def _create_event(self, inp: dict) -> dict:
        event = EventModel(
            title=inp["title"],
            date=inp["date"],
            time=inp.get("time"),
            duration_minutes=inp.get("duration_minutes", 60),
            attendees=inp.get("attendees"),
            notes=inp.get("notes")
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        self.log("Calendar Agent", "create_event", f'Scheduled "{event.title}" on {event.date}')
        return {"success": True, "event_id": event.id, "title": event.title, "date": event.date}

    def _list_events(self, inp: dict) -> dict:
        q = self.db.query(EventModel)
        if inp.get("date"):
            q = q.filter(EventModel.date == inp["date"])
        elif inp.get("start_date") and inp.get("end_date"):
            q = q.filter(EventModel.date >= inp["start_date"], EventModel.date <= inp["end_date"])
        events = q.order_by(EventModel.date, EventModel.time).all()
        self.log("Calendar Agent", "list_events", f"Retrieved {len(events)} events")
        return {"events": [{"id": e.id, "title": e.title, "date": e.date,
                            "time": e.time, "duration_minutes": e.duration_minutes,
                            "attendees": e.attendees} for e in events]}

    def _check_availability(self, inp: dict) -> dict:
        conflicts = self.db.query(EventModel).filter(
            EventModel.date == inp["date"],
            EventModel.time == inp.get("time")
        ).all()
        available = len(conflicts) == 0
        self.log("Calendar Agent", "check_availability",
                 f"{inp['date']} {inp.get('time')} → {'available' if available else 'conflict'}")
        return {"available": available, "conflicts": [c.title for c in conflicts]}

    def _delete_event(self, inp: dict) -> dict:
        event = self.db.query(EventModel).filter(EventModel.id == inp["event_id"]).first()
        if not event:
            return {"error": f"Event #{inp['event_id']} not found"}
        self.db.delete(event)
        self.db.commit()
        self.log("Calendar Agent", "delete_event", f'Deleted event #{inp["event_id"]}')
        return {"success": True}

    # ── Notes Agent ──

    def _create_note(self, inp: dict) -> dict:
        note = NoteModel(title=inp["title"], content=inp.get("content"), tags=inp.get("tags"))
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        self.log("Notes Agent", "create_note", f'Saved note #{note.id}: "{note.title}"')
        return {"success": True, "note_id": note.id, "title": note.title}

    def _list_notes(self, inp: dict) -> dict:
        q = self.db.query(NoteModel)
        if inp.get("search"):
            kw = f"%{inp['search']}%"
            q = q.filter((NoteModel.title.ilike(kw)) | (NoteModel.content.ilike(kw)))
        if inp.get("tag"):
            q = q.filter(NoteModel.tags.ilike(f"%{inp['tag']}%"))
        notes = q.order_by(NoteModel.created_at.desc()).all()
        self.log("Notes Agent", "list_notes", f"Retrieved {len(notes)} notes")
        return {"notes": [{"id": n.id, "title": n.title,
                           "content": n.content, "tags": n.tags,
                           "created_at": str(n.created_at)} for n in notes]}

    def _delete_note(self, inp: dict) -> dict:
        note = self.db.query(NoteModel).filter(NoteModel.id == inp["note_id"]).first()
        if not note:
            return {"error": f"Note #{inp['note_id']} not found"}
        self.db.delete(note)
        self.db.commit()
        self.log("Notes Agent", "delete_note", f'Deleted note #{inp["note_id"]}')
        return {"success": True}


# ─────────────────────────────────────────────
# Primary Orchestrator Agent
# ─────────────────────────────────────────────

ORCHESTRATOR_SYSTEM = """You are the Primary Orchestrator Agent of AgentOS, a multi-agent task management system.

You coordinate three specialized sub-agents via MCP tools:
- Task Agent: create_task, list_tasks, update_task, delete_task
- Calendar Agent: create_event, list_events, check_availability, delete_event
- Notes Agent: create_note, list_notes, delete_note

Your responsibilities:
1. Parse user intent from natural language
2. Identify which tools/agents are needed (may be multiple)
3. Execute multi-step workflows — e.g., "schedule meeting + create prep task + save agenda note"
4. Handle ambiguity by making reasonable assumptions
5. Aggregate results from multiple agents into a coherent response
6. Always be proactive: if the user asks to schedule a meeting, also offer to create a prep task

Today's date: {today}

You have access to the following tools:
{tools}

IMPORTANT: To use tools, output a JSON block containing an array of tool calls. Example format:
```json
[
  {{"tool": "create_task", "input": {{"title": "Review presentation", "priority": "high"}}}},
  {{"tool": "create_event", "input": {{"title": "Team Sync", "date": "2023-11-15", "time": "14:00"}}}}
]
```
If you don't need to use any tools, simply output your natural language response.
"""


async def run_orchestrator(message: str, conversation_history: list, db: Session) -> dict:
    """
    Primary Agent: Uses Google Gemini to process user requests and execute tools.
    """
    executor = MCPToolExecutor(db)
    
    tools_str = json.dumps(MCP_TOOLS, indent=2)
    system_prompt = ORCHESTRATOR_SYSTEM.format(
        today=datetime.now().strftime('%Y-%m-%d'),
        tools=tools_str
    )
    
    history_str = ""
    for msg in conversation_history[-5:]:
        history_str += f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}\n"
        
    prompt = f"Conversation History:\n{history_str}\nUser: {message}"
    
    response_text = call_gemini(prompt, system_instruction=system_prompt)
    
    workflow = []
    agents_involved = set(["Orchestrator"])
    
    if "```json" in response_text:
        try:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
            tool_calls = json.loads(json_str)
            
            tool_results = []
            for call in tool_calls:
                tool_name = call.get("tool")
                tool_input = call.get("input", {})
                
                result = executor.execute(tool_name, tool_input)
                tool_results.append({"tool": tool_name, "result": result})
                
                if "task" in tool_name:
                    agent_name = "Task Agent"
                elif "event" in tool_name or "availability" in tool_name:
                    agent_name = "Calendar Agent"
                else:
                    agent_name = "Notes Agent"
                    
                agents_involved.add(agent_name)
                workflow.append({"agent": agent_name, "step": f"Executed {tool_name}"})
            
            summary_prompt = f"User Request: {message}\n\nTool Execution Results:\n{json.dumps(tool_results, indent=2)}\n\nPlease provide a friendly, natural language response summarizing these results to the user. Do NOT output JSON."
            final_response = call_gemini(summary_prompt, system_instruction=system_prompt)
            response_text = final_response.replace("```json", "").replace("```", "").strip()
            
        except Exception as e:
            response_text = f"I tried to perform the action but encountered an error processing tools: {str(e)}"

    return {
        "response": response_text,
        "workflow": workflow,
        "agents_involved": list(agents_involved),
        "tool_calls": len(workflow)
    }


# ─────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────

app = FastAPI(
    title="AgentOS — Multi-Agent Task Management API",
    description="Primary agent + sub-agents with MCP tool integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
def health():
    return {"status": "healthy", "agents": ["orchestrator", "task", "calendar", "notes"]}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Main orchestrator endpoint — processes natural language and coordinates agents."""
    db = SessionLocal()
    try:
        result = await run_orchestrator(req.message, req.conversation_history, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ── Task CRUD ──

@app.get("/api/tasks")
def get_tasks(status: str = "all", priority: str = "all"):
    db = SessionLocal()
    try:
        q = db.query(TaskModel)
        if status != "all":
            q = q.filter(TaskModel.status == status)
        if priority != "all":
            q = q.filter(TaskModel.priority == priority)
        tasks = q.order_by(TaskModel.created_at.desc()).all()
        return [{"id": t.id, "title": t.title, "priority": t.priority,
                 "due_date": t.due_date, "status": t.status,
                 "created_at": str(t.created_at)} for t in tasks]
    finally:
        db.close()


@app.post("/api/tasks", status_code=201)
def create_task(task: TaskCreate):
    db = SessionLocal()
    try:
        t = TaskModel(**task.model_dump())
        db.add(t)
        db.commit()
        db.refresh(t)
        return {"id": t.id, "title": t.title, "priority": t.priority, "status": t.status}
    finally:
        db.close()


@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Task not found")
        for field, val in update.model_dump(exclude_none=True).items():
            setattr(t, field, val)
        t.updated_at = datetime.utcnow()
        db.commit()
        return {"success": True, "id": task_id}
    finally:
        db.close()


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Task not found")
        db.delete(t)
        db.commit()
        return {"success": True}
    finally:
        db.close()


# ── Calendar CRUD ──

@app.get("/api/events")
def get_events(date: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(EventModel)
        if date:
            q = q.filter(EventModel.date == date)
        events = q.order_by(EventModel.date, EventModel.time).all()
        return [{"id": e.id, "title": e.title, "date": e.date, "time": e.time,
                 "duration_minutes": e.duration_minutes, "attendees": e.attendees} for e in events]
    finally:
        db.close()


@app.post("/api/events", status_code=201)
def create_event(event: EventCreate):
    db = SessionLocal()
    try:
        e = EventModel(**event.model_dump())
        db.add(e)
        db.commit()
        db.refresh(e)
        return {"id": e.id, "title": e.title, "date": e.date}
    finally:
        db.close()


@app.delete("/api/events/{event_id}")
def delete_event(event_id: int):
    db = SessionLocal()
    try:
        e = db.query(EventModel).filter(EventModel.id == event_id).first()
        if not e:
            raise HTTPException(status_code=404, detail="Event not found")
        db.delete(e)
        db.commit()
        return {"success": True}
    finally:
        db.close()


# ── Notes CRUD ──

@app.get("/api/notes")
def get_notes(search: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(NoteModel)
        if search:
            kw = f"%{search}%"
            q = q.filter((NoteModel.title.ilike(kw)) | (NoteModel.content.ilike(kw)))
        notes = q.order_by(NoteModel.created_at.desc()).all()
        return [{"id": n.id, "title": n.title, "content": n.content,
                 "tags": n.tags, "created_at": str(n.created_at)} for n in notes]
    finally:
        db.close()


@app.post("/api/notes", status_code=201)
def create_note(note: NoteCreate):
    db = SessionLocal()
    try:
        n = NoteModel(**note.model_dump())
        db.add(n)
        db.commit()
        db.refresh(n)
        return {"id": n.id, "title": n.title}
    finally:
        db.close()


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int):
    db = SessionLocal()
    try:
        n = db.query(NoteModel).filter(NoteModel.id == note_id).first()
        if not n:
            raise HTTPException(status_code=404, detail="Note not found")
        db.delete(n)
        db.commit()
        return {"success": True}
    finally:
        db.close()


# ── Logs & Registry ──

@app.get("/api/logs")
def get_logs(limit: int = 50):
    db = SessionLocal()
    try:
        logs = db.query(AgentLogModel).order_by(
            AgentLogModel.created_at.desc()
        ).limit(limit).all()
        return [{"id": l.id, "agent": l.agent, "action": l.action,
                 "detail": l.detail, "status": l.status,
                 "created_at": str(l.created_at)} for l in logs]
    finally:
        db.close()


@app.get("/api/agents")
def get_agents():
    return {
        "agents": [
            {
                "name": "Primary Orchestrator",
                "role": "Coordinates all sub-agents, parses user intent, manages multi-step workflows",
                "model": "gemini-2.5-flash",
                "tools": ["route_to_agent", "aggregate_results", "all MCP tools"],
                "status": "active"
            },
            {
                "name": "Task Agent",
                "role": "Task creation, updates, deletion, priority management",
                "mcp_tools": ["create_task", "list_tasks", "update_task", "delete_task"],
                "db_table": "tasks",
                "status": "active"
            },
            {
                "name": "Calendar Agent",
                "role": "Event scheduling, availability checking, conflict resolution",
                "mcp_tools": ["create_event", "list_events", "check_availability", "delete_event"],
                "db_table": "events",
                "status": "active"
            },
            {
                "name": "Notes Agent",
                "role": "Note creation, search, summarization, action-item extraction",
                "mcp_tools": ["create_note", "list_notes", "delete_note"],
                "db_table": "notes",
                "status": "active"
            }
        ]
    }


@app.get("/api/stats")
def get_stats():
    db = SessionLocal()
    try:
        today = date.today().isoformat()
        return {
            "total_tasks": db.query(TaskModel).count(),
            "pending_tasks": db.query(TaskModel).filter(TaskModel.status == "pending").count(),
            "events_today": db.query(EventModel).filter(EventModel.date == today).count(),
            "total_events": db.query(EventModel).count(),
            "total_notes": db.query(NoteModel).count(),
            "total_agent_actions": db.query(AgentLogModel).count(),
        }
    finally:
        db.close()


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("Starting AgentOS Multi-Agent System...")
    print("Set GOOGLE_API_KEY environment variable before starting.")
    print("API docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
