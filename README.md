# AgentOS — Multi-Agent Task Management System

> An orchestrator-based AI system where a single natural-language request triggers coordinated, multi-step workflows across Task, Calendar, and Notes agents — powered by Google Gemini and FastAPI.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-agentos--hkc4.onrender.com-blue?style=flat-square)](https://agentos-hkc4.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

---
<img width="1358" height="600" alt="Screenshot 2026-05-17 094451" src="https://github.com/user-attachments/assets/52a7f88a-a861-43dc-9c4e-e70be1413a00" />
<img width="1364" height="599" alt="Screenshot 2026-05-17 094506" src="https://github.com/user-attachments/assets/f01aabcf-b268-4442-8ac7-46f363101c0f" />
<img width="1364" height="602" alt="Screenshot 2026-05-17 094522" src="https://github.com/user-attachments/assets/9aae92eb-08fc-48c4-96da-5d3de3df2c5a" />
<img width="1363" height="599" alt="Screenshot 2026-05-17 094535" src="https://github.com/user-attachments/assets/571759c7-2c5c-4c24-a81f-1c60f93d6fae" />
<img width="1365" height="601" alt="Screenshot 2026-05-17 094609" src="https://github.com/user-attachments/assets/66d0740f-7092-4770-a45c-ab86ad083265" />
<img width="1365" height="600" alt="Screenshot 2026-05-17 094628" src="https://github.com/user-attachments/assets/d1b651d3-e2a0-41c2-92fd-02b42b0f1900" />
<img width="1365" height="598" alt="Screenshot 2026-05-17 094640" src="https://github.com/user-attachments/assets/517c5d13-18cd-4d20-9f47-b6385b33a18c" />



## What is AgentOS?

Most "AI assistants" are single-agent — one LLM, one response. AgentOS is different.

A **Primary Orchestrator Agent** (Gemini) receives your natural-language request and breaks it into sub-tasks. It then routes each sub-task to the right specialist agent — Task, Calendar, or Notes — each equipped with its own set of MCP tools. All agents write to a shared SQLite database, and every action is logged for full traceability.

The result: one message → a coordinated, multi-step workflow, executed autonomously.

---

## Architecture

```
User (natural language input)
          │
          ▼
┌─────────────────────────────┐
│  Primary Orchestrator Agent  │  ← Google Gemini + 11 MCP tools
└────────┬──────────┬──────────┘
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
              │   SQLite DB    │
              │ tasks | events │
              │ notes | logs   │
              └────────────────┘
```

---

## Multi-Step Workflow — Example

**User says:**
> "Set up project kickoff for next Monday — schedule a 2hr meeting, create prep tasks, and save an agenda note."

**What AgentOS does in a single `/api/chat` request:**

| Step | Agent Action | MCP Tool |
|------|-------------|----------|
| 1 | Checks calendar for conflicts | `check_availability` |
| 2 | Creates a 2-hour meeting event | `create_event` |
| 3 | Creates prep tasks with priorities | `create_task` |
| 4 | Saves the agenda as a note | `create_note` |

No second prompt. No manual switching between tools. One request, four coordinated actions.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI / Orchestration | Google Gemini 1.5 Flash, MCP (11 tools) |
| Backend | FastAPI, Python 3.10+ |
| ORM / Database | SQLAlchemy, SQLite (PostgreSQL-ready) |
| Frontend | Vanilla JS dashboard, served by FastAPI |
| DevOps | Docker, Cloud Run (PORT env configurable) |
| Agent Logging | Custom execution tracing via `/api/logs` |

---

## Features

- **Orchestrator-based routing** — Gemini decides which agent(s) to invoke based on intent
- **11 specialized MCP tools** across Task, Calendar, and Notes domains
- **Full CRUD REST API** — every agent domain is independently accessible
- **Agent execution logs** — every tool call is recorded with timestamps and outcomes
- **Interactive dashboard** — built-in frontend, zero separate deployment needed
- **Docker + Cloud Run ready** — one-command deployment

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/ishaa21/AgentOS.git
cd AgentOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Google Gemini API key
export GOOGLE_API_KEY="your_api_key_here"

# 4. Run the server
uvicorn multi_agent_backend:app --reload --port 8000
```

Open **http://localhost:8000** for the dashboard, or **http://localhost:8000/docs** for the Swagger API explorer.

### Docker

```bash
docker build -t agentos .
docker run -p 8080:8080 -e GOOGLE_API_KEY="your_api_key_here" -e PORT=8080 agentos
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Main orchestrator — natural language input |
| `GET / POST / PUT / DELETE` | `/api/tasks` | Task management |
| `GET / POST / DELETE` | `/api/events` | Calendar scheduling |
| `GET / POST / DELETE` | `/api/notes` | Notes / knowledge base |
| `GET` | `/api/logs` | Agent execution trace |
| `GET` | `/health` | System health check |

Full interactive docs available at `/docs` (Swagger UI) and `/redoc`.

---

## Live Demo

**[https://agentos-hkc4.onrender.com](https://agentos-hkc4.onrender.com)**

> Note: Hosted on Render free tier — the first load may take ~30 seconds to spin up.

---

## Project Status

This project is actively developed. Planned improvements:
- [ ] PostgreSQL integration for production deployments
- [ ] Authentication layer (JWT)
- [ ] Streaming responses for long orchestrator chains
- [ ] Memory/context persistence across sessions

---

## Author

**Isha Zalavadia** — B.Tech Computer Engineering, BVM | Diploma in CE, AVPTI  
[GitHub](https://github.com/ishaa21) · [LinkedIn](https://linkedin.com/in/isha-zalavadia) · [Portfolio](#)
