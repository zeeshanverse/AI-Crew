# AI-Crew — Run and Test

## Start

```powershell
cd D:\codes\AI-Crew-Project\AI-Crew
docker compose up -d --build
docker compose ps
```

Expected services:

- ai
- backend
- frontend
- postgres (healthy)
- redis

Open `http://localhost:5173`.

## Infrastructure checks

```powershell
docker compose exec postgres pg_isready
docker compose exec redis redis-cli ping
curl.exe http://localhost:8000/health
```

Expected:

- PostgreSQL: `accepting connections`
- Redis: `PONG`
- AI: JSON with `"status":"ok"`

## API checks

```powershell
curl.exe http://localhost:8080/api/agents
curl.exe http://localhost:8080/api/dashboard
curl.exe http://localhost:8080/api/projects
curl.exe http://localhost:8080/api/tasks
curl.exe http://localhost:8080/api/vendors
curl.exe http://localhost:8080/api/finance/summary
curl.exe http://localhost:8080/api/knowledge/documents
```

## AI end-to-end test

```powershell
$body = @{
    agent = "CEO"
    objective = "Increase monthly revenue by 20%"
    context = @{}
} | ConvertTo-Json -Compress

Invoke-RestMethod `
  -Uri "http://localhost:8080/api/ai/run" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

Then:

```powershell
docker compose logs --tail=100 ai
```

Look for:

```text
POST /agents/run HTTP/1.1" 200 OK
```

## Functional UI test

### Dashboard
Verify live counts and cash balance.

### AI Command Center
Run all five:
- CEO
- Manager
- Business Analyst
- Software Engineer
- Research

Verify browser Network contains:

```text
POST http://localhost:8080/api/ai/run
200 OK
```

### Goals
Create, edit, delete and refresh.

### Projects
Create, edit, delete and verify persistence.

### Tasks
Create, assign to an AI employee/project, update status, delete and refresh.

### Business
Create KPI, edit/delete it, verify summary cards.

### Vendors
Create, edit/delete and refresh.

### Finance
Record income and expense. Verify income, expense and balance update.

### Knowledge
Create documents, search them, edit and delete.

## Persistence test

Create test records, then:

```powershell
docker compose restart
```

Refresh the UI.

Then test a full restart:

```powershell
docker compose down
docker compose up -d
docker compose ps
```

Do not use `docker compose down -v` unless you intentionally want to delete the PostgreSQL volume.

## Real AI mode

Default:

```env
AI_MODE=mock
```

Optional:

```env
AI_MODE=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-mini
```

Rebuild after changing the environment:

```powershell
docker compose up -d --build
```
