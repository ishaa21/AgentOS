# AgentOS — Multi-Agent Task Management System

> An orchestrator-based AI system where a single natural-language request triggers coordinated, multi-step workflows across Task, Calendar, and Notes agents — powered by Google Gemini 2.5 Flash and FastAPI.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-agentos--hkc4.onrender.com-blue?style=flat-square)](https://agentos-hkc4.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-8E44AD?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

---

## What is AgentOS?

Most traditional AI assistants operate as single agents — processing one prompt and returning a text response. **AgentOS** introduces an orchestrator architecture that bridges natural language with multi-domain actions.

A **Primary Orchestrator Agent** (powered by **Google Gemini 2.5 Flash**) receives user requests, parses intent, and orchestrates actions across three specialized sub-agents: **Task Agent**, **Calendar Agent**, and **Notes Agent**. Each sub-agent is equipped with dedicated **Model Context Protocol (MCP)** tools. All agent activities synchronize across a shared database and log transparently in real time.

---

## Architecture

```
User (Natural Language Prompt)
              │
              ▼
┌─────────────────────────────┐
│  Primary Orchestrator Agent  │  ← Google Gemini 2.5 Flash
└────────┬──────────┬──────────┘  └─ Orchestrates 11 MCP Tools
         │          │          │
         ▼          ▼          ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │Task Agent│ │Calendar  │ │ Notes    │
   │  (MCP)   │ │Agent(MCP)│ │Agent(MCP)│
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
              ┌───────▼────────┐
              │   SQL Database │
              │ tasks | events │
              │ notes | logs   │
              └────────────────┘
```

### Specialized Agents & MCP Tools

| Agent | Responsibility | MCP Tools |
|-------|----------------|-----------|
| **Primary Orchestrator** | Intent parsing, workflow planning, tool routing, response aggregation | `route_to_agent`, `aggregate_results` |
| **Task Agent** | Task creation, status updates, deletion, priority filtering | `create_task`, `list_tasks`, `update_task`, `delete_task` |
| **Calendar Agent** | Meeting scheduling, event listing, availability & conflict checking | `create_event`, `list_events`, `check_availability`, `delete_event` |
| **Notes Agent** | Knowledge base creation, keyword searching, tagging | `create_note`, `list_notes`, `delete_note` |

---

## Multi-Step Workflow Example

**User Input:**
> *"Set up project kickoff for next Monday — schedule a 2hr meeting, create prep tasks, and save an agenda note."*

**Execution via `/api/chat`:**

| Step | Executing Agent | MCP Tool | Action Detail |
|------|-----------------|----------|---------------|
| 1 | **Calendar Agent** | `check_availability` | Checks scheduled events for time conflicts |
| 2 | **Calendar Agent** | `create_event` | Schedules 2-hour "Project Kickoff" meeting |
| 3 | **Task Agent** | `create_task` | Creates high-priority preparation tasks |
| 4 | **Notes Agent** | `create_note` | Saves meeting agenda note in knowledge base |

Everything executes in a single coordinated request without manual tool switching.

---

## Website Features & Navigation

AgentOS provides a full web interface served directly by FastAPI:

- **Dashboard**: Real-time summary displaying active tasks, events scheduled today, note counts, and total system agent execution logs via `/api/stats`.
- **AI Chat**: Conversational interface with live execution traces showing which agents and MCP tools were triggered.
- **Task Management**: Interactive task board with filtering by status (`pending`, `in_progress`, `done`) and priority (`low`, `medium`, `high`).
- **Calendar & Scheduling**: View scheduled events, date filters, attendee lists, and event details.
- **Notes / Knowledge Base**: Searchable note vault with tag indexing.
- **Agent Registry**: Inspect active agents, their assigned models, roles, and connected MCP tools.
- **System Execution Logs**: Full log viewer tracing every tool invocation, action payload, and status.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Engine** | Google Gemini 2.5 Flash (`gemini-2.5-flash`) |
| **Protocol** | Model Context Protocol (11 MCP Tools) |
| **Backend** | FastAPI, Python 3.10+, Pydantic v2, `python-dotenv` |
| **Database & ORM** | SQLAlchemy, SQLite (bundled `agentOS.db`), PostgreSQL / AlloyDB ready |
| **Frontend** | Vanilla JS Dashboard (CSS variables, FontAwesome, Google Fonts) |
| **Deployment & DevOps** | Docker, Render Blueprint (`render.yaml`), Uvicorn |

---

## Quick Start

### 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/ishaa21/AgentOS.git
cd AgentOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
PORT=8000
# DATABASE_URL=postgresql://user:password@localhost/agentos_db # Optional
```

### 3. Run the Backend

```bash
uvicorn multi_agent_backend:app --reload --port 8000
```

Open **http://localhost:8000** in your browser to access the dashboard.  
Interactive API docs are available at **http://localhost:8000/docs** (Swagger UI) and **http://localhost:8000/redoc**.

---

## Deployment

### Docker

```bash
# Build Docker image
docker build -t agentos .

# Run container
docker run -p 8000:8000 -e GOOGLE_API_KEY="your_api_key_here" agentos
```

### Render Blueprint

AgentOS includes a `render.yaml` specification for zero-config Render deployment:

1. Connect your repository to **Render**.
2. Render will automatically detect `render.yaml`.
3. Set your `GOOGLE_API_KEY` under Environment Variables in the Render dashboard.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Main orchestrator — processes natural language & coordinates agents |
| `GET` | `/api/stats` | System statistics overview (task, event, note, log counts) |
| `GET / POST / PUT / DELETE` | `/api/tasks` | Task CRUD endpoints (`status`, `priority`, `due_date`) |
| `GET / POST / DELETE` | `/api/events` | Calendar CRUD endpoints (`date`, `time`, `attendees`) |
| `GET / POST / DELETE` | `/api/notes` | Notes CRUD endpoints with keyword and tag search |
| `GET` | `/api/logs` | Fetch execution logs for agent activity tracing |
| `GET` | `/api/agents` | Fetch registered agents, capabilities, and MCP tool specifications |
| `GET` | `/health` | Health check endpoint returning active sub-agent status |

---

## Live Demo

**[https://agentos-hkc4.onrender.com](https://agentos-hkc4.onrender.com)**

> *Note: Hosted on Render free tier — initial load may take ~30 seconds if instance is spinning up.*

---

## Author

**Isha Zalavadia** — B.Tech Computer Engineering, BVM | Diploma in CE, AVPTI  
[GitHub](https://github.com/ishaa21) · [LinkedIn](https://linkedin.com/in/isha-zalavadia)
