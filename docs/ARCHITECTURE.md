# AI-Crew Architecture

## Core rule

Spring Boot owns enterprise business state. Python/LangGraph owns AI orchestration. Agents never directly mutate the database; they request controlled actions through APIs/tools.

## Target flow

Human goal
→ CEO AI
→ Manager AI
→ specialist agents
→ review
→ human approval for risky actions
→ execution
→ result
→ company memory
→ next cycle

## Planned agents

CEO AI — strategy and goals  
Manager AI — planning and coordination  
Business Analyst AI — KPIs and business analysis  
Software Engineer AI — technical work  
Finance AI — budgets and financial analysis  
Vendor AI — procurement and vendors  
Research AI — external research  

Later: Product, QA, DevOps, Security, HR, Marketing, Sales, Support.

## Technology

Frontend: React + TypeScript  
Enterprise backend: Java 21 + Spring Boot  
AI: Python + FastAPI + LangChain + LangGraph  
Database: PostgreSQL + pgvector  
Cache/jobs: Redis  
Deployment: Docker first; cloud later.

## RAG

Company documents → chunking → embeddings → pgvector → retrieval → agent context.

## MCP

MCP will be added after the base tool layer:
- GitHub
- files/documents
- company data
- external services
- AI-Crew MCP server

## Security

Future versions will include authentication, RBAC, per-agent tool permissions, approval gates, audit logs, rate limiting and secrets management.
