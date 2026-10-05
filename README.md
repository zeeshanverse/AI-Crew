# AI-Crew — AI Operating System

AI-Crew is a local-first **AI operating system for company execution**.

It is not just a chatbot. The system gives you five specialized AI employees and connects their recommendations to persistent company operations:

```text
Business objective
       ↓
AI employee reasoning
       ↓
Strategy / analysis / research / engineering / execution plan
       ↓
Goals → Projects → Tasks → KPIs → Finance → Knowledge
       ↓
Company Control Center
```

The current release supports both:

- **Mock mode** — no external AI key required; useful for local development and UI testing.
- **OpenAI mode** — real LLM-powered responses with conversational follow-ups.

---

## 1. What AI-Crew is for

Imagine you are running an AI SaaS company and say:

> "Increase monthly recurring revenue by 20% within 90 days."

AI-Crew lets you give that objective to different AI employees:

- **CEO AI** — strategy, priorities, trade-offs, risks and executive decisions.
- **Manager AI** — execution plans, milestones, owners, dependencies and tasks.
- **Business Analyst AI** — KPIs, baselines, data requirements and hypotheses.
- **Software Engineer AI** — architecture, APIs, implementation, testing and technical risks.
- **Research AI** — research questions, evidence plans, competitors and decision implications.

The important idea is that these employees have different responsibilities. The same objective should therefore produce different kinds of responses.

---

# 2. The AI Command Center

Open:

```text
http://localhost:5173
```

Select an AI employee and start a conversation.

### Example

Choose **CEO AI** and enter:

```text
We need to increase monthly recurring revenue by 20% within 90 days.

Create a strategic plan. Identify the highest-priority initiatives,
measurable success criteria, major risks, and the first actions
the company should take.
```

The result is presented as an actual AI response rather than a raw JSON payload.

You can then continue:

```text
Which initiative should we prioritize first and why?
```

Then:

```text
What information do you need from me before making that decision?
```

Then:

```text
Challenge your recommendation. What could make this plan fail?
```

AI-Crew sends the conversation history to the AI employee so follow-up questions remain contextual.

Use **Ctrl + Enter** to send.

---

# 3. Five AI employees

## CEO AI

Think of CEO AI as the strategic layer.

Use it for:

- company strategy
- prioritization
- growth plans
- trade-offs
- risks
- success criteria
- executive decisions

Example:

```text
We have 500 customers, 4% monthly churn and ₹600,000 MRR.
We want to reach ₹750,000 MRR in 90 days.

Create an executive strategy and identify the biggest risks.
```

---

## Manager AI

Manager AI turns strategy into execution.

Example:

```text
Turn the goal of increasing MRR by 25% into a 30-day execution plan.

Break it into workstreams, projects, tasks, dependencies,
owners and weekly milestones.
```

Expected thinking:

```text
Objective
  ↓
Workstreams
  ↓
Projects
  ↓
Tasks
  ↓
Owners
  ↓
Milestones
```

---

## Business Analyst AI

Business Analyst AI focuses on evidence and measurement.

Example:

```text
Our objective is to increase MRR by 20% in 90 days.

Define the KPIs, baseline data, segmentation and analysis
we need before deciding which growth initiative to fund.
```

It should distinguish between:

- known information
- assumptions
- missing data
- hypotheses
- measurable recommendations

---

## Software Engineer AI

Use it to translate company requirements into technical execution.

Example:

```text
We want to launch an enterprise billing system.

Design the backend architecture including APIs, PostgreSQL
schema, authentication, payment integration, testing,
observability and deployment.
```

You can follow up:

```text
Now turn that architecture into implementation milestones
for a Java Spring Boot team.
```

---

## Research AI

Research AI structures research rather than pretending it already knows facts that have not been verified.

Example:

```text
We are considering launching an AI productivity SaaS for small
businesses.

Create a research plan covering competitors, customer problems,
pricing, market risks and the evidence we need before launching.
```

---

# 4. A complete AI-Crew workflow

Use this example to understand the whole product.

### Step 1 — CEO

```text
Increase MRR by 20% within 90 days.
```

CEO produces:

- strategic priorities
- success criteria
- risks
- first actions

### Step 2 — Business Analyst

Ask:

```text
Define the metrics and data needed to measure whether the CEO strategy
is working.
```

### Step 3 — Research

Ask:

```text
Create a competitor and market research plan that could influence
our pricing and acquisition strategy.
```

### Step 4 — Manager

Ask:

```text
Turn the approved strategy into a 30-day execution plan.
```

### Step 5 — Software Engineer

Ask:

```text
Identify the engineering work required to support the highest-priority
initiative.
```

### Step 6 — Operating system

Record the approved work in:

```text
Goals
  ↓
Projects
  ↓
Tasks
  ↓
Business KPIs
  ↓
Finance
  ↓
Knowledge
```

This is what differentiates AI-Crew from a normal chatbot.

---

# 5. Company operating modules

## Goals

Store measurable company outcomes.

Example:

```text
Increase monthly recurring revenue by 20% within 90 days.
```

---

## Projects

Turn larger initiatives into execution containers.

Example:

```text
Project:
Revenue Expansion Initiative

Status:
ACTIVE
```

---

## Tasks

Create executable work.

Example:

```text
Analyze customer churn
Review pricing tiers
Build upgrade campaign
Improve conversion funnel
Implement billing changes
```

Tasks can be assigned to AI employees.

---

## Business

Store KPIs and operational metrics.

Example:

```text
MRR                  ₹600,000
Monthly churn        4%
Conversion rate      7.2%
Enterprise customers 35
```

---

## Vendors

Track external companies and service providers.

Example:

```text
Cloud provider
Payment provider
Email provider
Analytics provider
AI API provider
```

---

## Finance

Track:

- income
- expenses
- balance

Example:

```text
Income      ₹850,000
Expenses    ₹420,000
Balance     ₹430,000
```

---

## Knowledge

Store company memory:

- policies
- product decisions
- onboarding material
- architecture decisions
- procedures
- customer information
- internal documentation

The Knowledge module is intended to become the foundation for future RAG-powered AI context.

---

# 6. Architecture

```text
                         USER
                           │
                           ▼
                 React / TypeScript
                  Company Control Center
                           │
                           ▼
                    Spring Boot API
                         :8080
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
        PostgreSQL       Redis       Python AI
         + Flyway                     :8000
                                         │
                                         ▼
                                     LangGraph
                                         │
              ┌──────────┬──────────┬────┼────┬──────────┐
              ▼          ▼          ▼         ▼          ▼
             CEO      Manager    Analyst      SWE     Research
              │          │          │         │          │
              └──────────┴──────────┴─────────┴──────────┘
                               │
                               ▼
                    Company operating state
```

### Technology stack

- React 19
- TypeScript
- Vite
- Java 21
- Spring Boot
- Python
- FastAPI
- LangGraph
- LangChain
- OpenAI integration
- PostgreSQL
- pgvector-ready database
- Redis
- Flyway
- Docker Compose

---

# 7. Mock mode vs real AI mode

## Mock mode

The project defaults to:

```env
AI_MODE=mock
```

Mock mode does not call an external LLM.

It produces realistic role-specific responses so you can:

- test the UI
- test Docker
- test API integration
- learn the workflow
- develop without an API key

The response will show:

```text
AI Mode: MOCK
```

This is intentional.

---

## Real OpenAI mode

Set in `.env`:

```env
AI_MODE=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
```

Then rebuild:

```powershell
docker compose up -d --build
```

The dashboard should show:

```text
AI Mode: OPENAI
```

Now the five employees use real LLM reasoning.

**Never commit your API key to GitHub.**

---

# 8. Run the complete system

From:

```text
D:\codes\AI-Crew-Project\AI-Crew
```

Run:

```powershell
docker compose up -d --build
```

Check:

```powershell
docker compose ps
```

You should see:

```text
ai
backend
frontend
postgres
redis
```

Then open:

```text
http://localhost:5173
```

---

# 9. Useful service URLs

Frontend:

```text
http://localhost:5173
```

Spring Boot:

```text
http://localhost:8080
```

Spring Boot health:

```text
http://localhost:8080/actuator/health
```

AI service:

```text
http://localhost:8000
```

AI health:

```text
http://localhost:8000/health
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

---

# 10. Useful commands

Start:

```powershell
docker compose up -d
```

Rebuild:

```powershell
docker compose up -d --build
```

Stop:

```powershell
docker compose down
```

View all logs:

```powershell
docker compose logs -f
```

AI logs:

```powershell
docker compose logs -f ai
```

Backend logs:

```powershell
docker compose logs -f backend
```

Check PostgreSQL:

```powershell
docker compose exec postgres pg_isready
```

Check Redis:

```powershell
docker compose exec redis redis-cli ping
```

Do **not** use `docker compose down -v` unless you intentionally want to delete the local PostgreSQL volume.

---

# 11. Direct AI API test

PowerShell:

```powershell
$body = @{
    agent = "CEO"
    objective = "Increase monthly revenue by 20% within 90 days"
    context = @{}
    conversation = @()
} | ConvertTo-Json -Depth 10 -Compress

Invoke-RestMethod `
  -Uri "http://localhost:8080/api/ai/run" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

For a follow-up, include previous messages in `conversation`.

---

# 12. How to showcase AI-Crew

Do not present it as:

> "I made a chatbot."

Present it as:

> **AI-Crew is a full-stack multi-agent AI operating system for company execution. It combines five specialized AI employees with persistent operational systems for goals, projects, tasks, KPIs, vendors, finance and organizational knowledge.**

A good live demonstration is:

```text
1. Give CEO AI a business objective
2. Ask CEO AI to create strategy
3. Challenge the strategy
4. Ask Business Analyst AI for the measurement plan
5. Ask Research AI for a research plan
6. Ask Manager AI to turn the strategy into execution
7. Ask Software Engineer AI for the technical implementation
8. Save the objective as a Goal
9. Create the resulting Project
10. Create Tasks
11. Record KPIs
12. Record financial impact
13. Store the final decision in Knowledge
14. Show the Dashboard
```

This demonstrates both the **AI layer** and the **operating-system layer**.

---

# 13. Current limitations

The current release is intentionally controlled.

AI employees can:

- reason
- analyze
- plan
- recommend
- maintain conversational context during a Command Center session

They do not yet autonomously modify company records based on their own recommendations.

For example, an AI may recommend:

> "Create a Revenue Expansion project."

The current workflow still expects a human to approve and create that project.

This is deliberate because autonomous database-changing agents should use explicit tools, permissions, validation and approval boundaries.

---

# 14. Next evolution

The next major architecture step is controlled agent actions:

```text
User objective
      ↓
AI reasoning
      ↓
Proposed action
      ↓
Human approval
      ↓
Tool call
      ↓
Spring Boot API
      ↓
PostgreSQL
      ↓
Verification
      ↓
Dashboard
```

Examples:

```text
CEO AI
  → propose Goal

Manager AI
  → propose Project + Tasks

Business Analyst AI
  → propose KPI

Finance AI capability
  → propose financial record

Knowledge capability
  → save approved company decision
```

This would turn AI-Crew from an AI-assisted operating system into a **controlled agentic operating system**.

---

# 15. Learning checklist

To understand the project deeply, learn it in this order:

### Backend

1. Spring Boot controllers
2. REST APIs
3. PostgreSQL
4. JPA/JdbcTemplate
5. Flyway
6. Docker networking
7. Redis

### AI service

1. FastAPI
2. Pydantic
3. LangChain
4. LangGraph
5. System prompts
6. Conversation context
7. Tool calling
8. RAG
9. MCP

### Frontend

1. React state
2. React effects
3. API calls
4. Component architecture
5. Conversation UI
6. Loading/error states

### Architecture

Finally understand:

```text
React
  ↓
Spring Boot
  ↓
FastAPI
  ↓
LangGraph
  ↓
LLM
```

and:

```text
Spring Boot
  ↓
PostgreSQL
```

The combination of these two paths is the main engineering value of AI-Crew.

## Agentic operating loop (v0.4)

AI-Crew now follows a human-in-the-loop operating loop:

1. You give an AI employee an objective.
2. The selected employee reads relevant company state and can search company knowledge.
3. The model produces a natural-language recommendation.
4. When useful, it proposes concrete write actions such as creating a goal, project, task, KPI, vendor, finance transaction or knowledge document.
5. **No write action happens automatically.** The Control Center shows the proposed action and its arguments.
6. You approve or reject each action.
7. Approved actions are executed through the Spring Boot API and persisted in PostgreSQL.
8. Approved actions are written to an audit table.
9. Continue the conversation and ask the agent to evaluate the updated company state.

### How to test the operating loop

Use this scenario:

> We need to increase MRR by 20% in 90 days. Start by creating a company goal, then propose the first execution project and the KPIs we should track. Do not assume any current MRR value unless it exists in company data.

Then:

- CEO AI → strategy and goal proposal.
- Approve the goal.
- Manager AI → project and task proposals.
- Approve the project/tasks.
- Business Analyst AI → KPI proposals.
- Approve KPI records.
- Research AI → search/reuse Knowledge and identify evidence gaps.
- Software Engineer AI → propose implementation tasks tied to the approved project.
- Finance → record only real or clearly fictional test transactions.
- Vendors → create dependencies when a vendor is actually part of the scenario.
- Knowledge → store validated company decisions and policies.

### The six operating modules

**Projects** are the initiatives that turn goals into execution.

**Tasks** are the smallest actionable units of work, optionally assigned to an AI employee and linked to a project.

**Business** stores KPIs and operating metrics used to measure whether objectives are improving.

**Vendors** stores external companies/resources the operating plan depends on.

**Finance** records income and expenses so the company can reason about cash impact.

**Knowledge** is the company's persistent memory. Put product decisions, policies, customer insights, SOPs and validated research here. AI employees can search this knowledge during conversations.

### Suggested end-to-end demo

1. Create a goal: `Increase MRR by 20% in 90 days`.
2. Ask CEO AI for the strategy.
3. Ask Manager AI to turn it into a project and tasks.
4. Approve the project and tasks.
5. Ask Business Analyst AI to define three KPIs; approve them.
6. Add a fictional pricing policy to Knowledge.
7. Ask Research AI what the company still needs to learn; let it use Knowledge.
8. Ask Software Engineer AI to design the technical work needed for the highest-priority initiative.
9. Record a test income/expense pair in Finance.
10. Add a test SaaS vendor in Vendors.
11. Return to Dashboard and inspect the resulting company state.
12. Ask CEO AI: `Review the updated company state. What should we do next?`

The key learning objective is to see the loop from **conversation → recommendation → approval → company data → next decision**.
