# AI-Crew — Human-in-the-Loop AI Company Operating System

AI-Crew is a multi-service platform where five role-based AI employees (CEO, Manager, Business Analyst, Software Engineer, Research) help run a small company. You give an employee an objective; it reads company data, recommends a plan, and **proposes** concrete actions such as creating a goal, project or task. Nothing is written until **you approve it**, and every executed action is saved to an audit table.

<!-- Add a demo GIF/video and screenshots here:
![AI Command Center](docs/command-center.png) -->

## How the loop works

1. You give an AI employee an objective in the **AI Command Center**.
2. The agent (a LangGraph workflow) reads the company snapshot and searches the knowledge base through read-only tools.
3. It replies with a recommendation and, when useful, **proposes write actions** with their arguments.
4. You approve or reject each action in the UI.
5. Approved actions are executed through the Spring Boot API and stored in PostgreSQL.
6. Every executed action is recorded in the `ai_action_audit` table (agent, tool, arguments, result, status, timestamp).
7. You continue the conversation, and the agent sees the updated company state.

Agents never write to the database directly. They can only propose, and the backend performs the action after approval. Supported actions: `create_goal`, `create_project`, `create_task`, `create_metric`, `create_vendor`, `record_transaction`, `create_knowledge_document`.

## Architecture

```mermaid
flowchart LR
    UI[React + TypeScript UI] --> API[Spring Boot API :8080]
    API --> DB[(PostgreSQL)]
    API --> AI[FastAPI + LangGraph AI service :8000]
    AI --> API
    AI -.-> LLM[OpenAI via LangChain, optional]
    API --> AUD[(ai_action_audit)]
```

The AI service calls the backend's internal endpoints (protected by a shared internal token) to read company context. Approved actions are executed by the backend.

| Service | Role | Port |
|---|---|---|
| `frontend/` | React + TypeScript (Vite) UI | 5173 |
| `backend/` | Spring Boot REST API, Flyway migrations, executes approved actions | 8080 |
| `ai/` | FastAPI service running the LangGraph agent workflow | 8000 |
| PostgreSQL | Data store (pgvector-enabled image, reserved for planned semantic search) | 5432 |
| Redis | Provisioned in Compose for planned background jobs; **not used yet** | 6379 |

## Features

- **Five AI employees** with distinct role guidance.
- **Tool-calling agents:** read tools (company snapshot, knowledge search) and write tools that only *propose* actions.
- **Approval workflow and audit trail** for every AI-initiated change.
- **Company modules:** dashboard, goals, projects, tasks, business KPIs, vendors, finance ledger and knowledge documents, each with CRUD endpoints.
- **Two AI modes:** `mock` (default; runs with no API key and returns role-specific canned responses) and `openai` (real reasoning through LangChain + OpenAI).
- **One-command setup** with Docker Compose.

## Tech stack

Java 21, Spring Boot, Flyway · Python 3.11, FastAPI, LangGraph, LangChain · React, TypeScript, Vite · PostgreSQL · Docker Compose · JUnit 5, pytest

---

## Run locally

### Option 1: Docker (recommended)

Requirements: Docker Desktop (or Docker Engine) with Docker Compose v2. Nothing else is needed.

```bash
git clone https://github.com/zeeshanverse/AI-Crew.git
cd AI-Crew

cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
docker compose up --build -d
docker compose ps               # wait until all services are running and postgres is healthy
```

Open **http://localhost:5173**.

| What | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8080/api/agents |
| AI service health | http://localhost:8000/health |
| AI mode as seen by the backend | http://localhost:8080/api/ai/status |

Quick check:

```bash
curl http://localhost:8000/health
curl http://localhost:8080/api/ai/status
# expect "mode":"mock" and "live_enabled":false until you add an OpenAI key
```

Useful commands:

```bash
docker compose logs -f ai          # follow the AI service logs
docker compose down                # stop everything, keep data
docker compose down -v             # stop and delete the database volume (fresh start)
```

### Enable real AI reasoning (optional)

The default `AI_MODE=mock` needs no credentials. To use OpenAI, edit `.env`:

```text
AI_MODE=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
```

Then recreate the containers and verify:

```bash
docker compose up -d
curl http://localhost:8080/api/ai/status     # expect "mode":"openai" and "live_enabled":true
```

If `AI_MODE=openai` but the key is empty, the service falls back to mock mode, so check `live_enabled`. Never commit `.env`.

### Option 2: Run each service without Docker (for development)

Requirements: JDK 21, Maven 3.9+, Python 3.11, Node.js 20, and Docker (only for PostgreSQL).

**1. Start PostgreSQL**

```bash
docker compose up -d postgres
```

**2. Backend** (terminal 1). The defaults connect to `localhost:5432/ai_crew` and the AI service on `localhost:8000`; Flyway creates the schema on startup.

```bash
cd backend
mvn spring-boot:run
```

**3. AI service** (terminal 2). The backend URL must point to localhost instead of the Docker hostname.

```bash
cd ai
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export INTERNAL_API_BASE_URL=http://localhost:8080      # PowerShell: $env:INTERNAL_API_BASE_URL="http://localhost:8080"
# optional real mode:
# export AI_MODE=openai OPENAI_API_KEY=your_key_here

uvicorn app.main:app --reload --port 8000
```

**4. Frontend** (terminal 3)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Try the API from the command line

```bash
curl http://localhost:8080/api/agents
curl http://localhost:8080/api/dashboard

curl -X POST http://localhost:8080/api/ai/run \
  -H "Content-Type: application/json" \
  -d '{"agent":"CEO","objective":"Increase monthly revenue by 20%","context":{}}'
```

Windows PowerShell (use `curl.exe` or `Invoke-RestMethod`; plain `curl` is an alias with different behavior):

```powershell
$body = @{ agent = "CEO"; objective = "Increase monthly revenue by 20%"; context = @{} } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://localhost:8080/api/ai/run" -Method POST -ContentType "application/json" -Body $body
```

### Troubleshooting

| Problem | Fix |
|---|---|
| `/api/ai/status` returns 502 / "unavailable" | The AI service is not running or not reachable. Check `docker compose logs ai` (Docker) or `INTERNAL_API_BASE_URL` (non-Docker). |
| Port already in use | Change `POSTGRES_PORT`, `BACKEND_PORT`, `AI_PORT`, `REDIS_PORT` or `FRONTEND_PORT` in `.env` and restart. |
| Backend fails on Flyway or schema validation | Reset the database with `docker compose down -v`, then start again. |
| Agents always give canned answers | You are in mock mode. Set `AI_MODE=openai` with a valid key and confirm `live_enabled` is `true`. |
| UI shows network or CORS errors | The backend only allows the UI origin `http://localhost:5173`. Open the UI on that exact address. |

---

## Try the demo flow

1. Open **AI Command Center**, pick **CEO AI**, and enter "Increase MRR by 20% in 90 days".
2. Approve the proposed goal.
3. Ask **Manager AI** to turn it into a project and tasks, then approve them.
4. Ask **Business Analyst AI** to define KPIs, and approve them.
5. Add a policy under **Knowledge**, then ask **Research AI** what evidence is missing.
6. Ask **CEO AI**: "Review the updated company state. What should we do next?"

In mock mode, responses are canned but the propose, approve and audit flow works the same way.

## Tests

```bash
cd ai && pip install -r requirements.txt && pytest      # health and agent endpoint tests
cd backend && mvn test                                   # agent catalog test
```

More documentation: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/RUN_AND_TEST.md`](docs/RUN_AND_TEST.md) · [`docs/ROADMAP.md`](docs/ROADMAP.md) · [`PROJECT_STATUS.md`](PROJECT_STATUS.md)

## Current limitations

- `mock` is the default mode, so agent output is canned until you enable `openai`.
- No authentication or multi-user support yet, so run it locally or behind your own gateway rather than exposing it publicly.
- Knowledge search is keyword matching. `rag.py`, `mcp.py` and `tools.py` are placeholders for planned semantic search and integrations.
- Redis is provisioned but not used yet.
- Test coverage is minimal.

## Roadmap

Authentication and RBAC · RAG over knowledge documents with pgvector · persistent conversation history · background jobs on Redis · external integrations via MCP · analytics dashboards

## Author

**Mohammed Zeeshan** — [GitHub](https://github.com/zeeshanverse) · [LinkedIn](https://www.linkedin.com/in/zeeshanmohd/)