# AI-Crew Project Status

## Current release
AI-Crew v0.3 — conversational multi-agent company operating system.

## Working
- Docker Compose infrastructure
- PostgreSQL + Flyway
- Redis
- Spring Boot API
- FastAPI AI service
- React control center
- Five specialized AI employees
- Conversational AI Command Center
- Per-agent follow-up conversation context
- Role-specific AI system guidance
- Rich natural-language AI responses
- Mock conversational mode without an API key
- Optional OpenAI-powered reasoning mode
- AI run history
- Goals
- Projects
- Tasks
- Business KPIs
- Vendors
- Finance ledger
- Knowledge documents/search
- Dashboard metrics
- AI service status on the dashboard

## AI behavior
Each employee has a distinct operating role:
- CEO — strategy and priorities
- Manager — execution and coordination
- Business Analyst — metrics and evidence
- Software Engineer — architecture and implementation
- Research — research planning and evidence validation

The UI no longer exposes the agent response as the primary raw JSON payload. The Command Center presents a conversational response view with follow-up prompts.

## Default behavior
`AI_MODE=mock` remains the default so the complete system runs without external credentials. Mock mode is role-specific and conversationally formatted for development/testing.

For real LLM reasoning, set `AI_MODE=openai` and provide `OPENAI_API_KEY`.

## Validation
Python modules were syntax-checked. The frontend source was updated without adding a runtime dependency; run the Docker build on the development machine to perform the authoritative TypeScript/Vite compilation.

## Next extension areas
- Controlled agent tools and action proposals
- Human approval workflows
- Persistent conversation history in PostgreSQL
- RAG over Knowledge documents
- Semantic search with pgvector
- Background jobs/Redis queues
- Authentication and multi-user tenancy
- RBAC and per-agent permissions
- Rich analytics and charts
- External provider integrations
