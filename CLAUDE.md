<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MyAgent is a LangGraph-based intelligent chatbot system with knowledge base RAG, web search, and multi-model support.

**Tech Stack:**
- Backend: FastAPI + LangGraph + Python 3.12+ (managed with `uv`)
- Frontend: React 19 + Vite + TailwindCSS + Zustand
- Database: PostgreSQL 16 + pgvector
- Cache: Redis
- Async Tasks: Celery
- Observability: Langfuse

## Development Commands

### Setup & Installation
```bash
# Install all dependencies
make install

# Install backend only (uses uv)
make backend-install

# Install frontend only
make frontend-install
```

### Running Services

**Local Development:**
```bash
# Backend (hot reload on port 8080)
make run
# or directly:
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Frontend (port 3000)
make frontend-run
# or directly:
cd frontend && npm run dev
```

**Docker (all services):**
```bash
# Start all services (backend:8081, frontend:3001, postgres:5432, redis:6379)
docker compose up -d

# View logs
docker compose logs -f backend

# Production deployment
docker compose -f docker-compose.prod.yml up -d
```

### Code Quality
```bash
# Lint (ruff)
make lint

# Format (ruff + black)
make format

# Run tests
make test
# Run specific test:
cd backend && uv run pytest tests/test_health.py -v
```

### Database
```bash
# Run migrations
make db-migrate

# Create new migration
make db-revision
# Will prompt for description
```

### Cleanup
```bash
make clean  # Remove __pycache__, .pytest_cache, etc.
```

## Architecture

### LangGraph Agent Workflow

The system uses a unified LangGraph state machine with two operational modes:

**1. Chat Mode (`mode="chat"`):**
```
START → rewrite → chatbot → [tools → chatbot]* → END
```
- `rewrite`: Resolves pronouns/references using conversation history
- `chatbot`: Main LLM interaction with tool binding
- `tools`: Executes tools (RAG search, web search, calculator, etc.)

**2. Deep Search Mode (`mode="deep_search"`):**
```
START → planning → [search → planning]* → summary → END
```
- `planning`: Generates search queries based on user question
- `search`: Executes web searches via Tavily
- `summary`: Synthesizes final answer from accumulated references
- Max rounds controlled by `DEEP_SEARCH_MAX_ROUNDS` (default: 5)

**Key Files:**
- `backend/app/agent/graph.py` - Agent graph construction and routing logic
- `backend/app/nodes/` - Individual node implementations
- `backend/app/tools/` - Tool definitions (RAG, Tavily, etc.)

### Backend Architecture

**Layered Structure:**
```
API Layer (FastAPI routes)
    ↓
Service Layer (business logic)
    ↓
Model Layer (SQLAlchemy ORM)
    ↓
Database (PostgreSQL + pgvector)
```

**Key Modules:**
- `app/api/routes/` - REST endpoints (chat, knowledge, user, model, etc.)
- `app/services/` - Business logic (chat_service, knowledge_service, etc.)
- `app/models/` - SQLAlchemy models (User, Message, KnowledgeBase, etc.)
- `app/core/` - Core utilities (settings, db, checkpointer, crypto, logging)
- `app/tasks/` - Celery async tasks (document parsing, embedding generation)

### Configuration System

Settings are managed via Pydantic in `backend/app/core/settings.py`:
- Loads from `.env` file (or `.env.{APP_ENV}` for other environments)
- Grouped by domain: database, redis, JWT, AI models, RAG, OSS, Langfuse, Celery
- Access via `get_settings()` singleton

**Required Environment Variables:**
- `DB_PASSWORD` - PostgreSQL password
- `REDIS_PASSWORD` - Redis password
- `JWT_SECRET` - JWT signing key
- `AI_DEEPSEEK_API_KEY` - Default LLM API key

**Optional Services:**
- `TAVILY_API_KEY` - Web search functionality
- `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` - LLM observability
- `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` - Alibaba Cloud OSS for file storage

### Knowledge Base RAG

**Document Processing Pipeline:**
1. Upload → OSS storage (if configured) or local
2. Celery task parses document (PDF/DOCX) → chunks
3. Embedding generation (local BGE or remote API)
4. Store in PostgreSQL with pgvector

**Retrieval:**
- Hybrid search: pgvector similarity + BM25 keyword matching
- Configurable via `RAG_TOP_K` and `RAG_SIMILARITY_THRESHOLD`
- Integrated as `rag_search` tool in agent workflow

**Key Files:**
- `app/services/knowledge_service.py` - Document management
- `app/services/embedding_service.py` - Vector generation
- `app/tasks/document_tasks.py` - Async document parsing
- `app/tasks/embedding_tasks.py` - Async embedding generation
- `app/tools/rag_tool.py` - RAG tool for agent

### User-Defined Models

Users can configure custom LLM providers (OpenAI, Gemini, etc.):
- API keys encrypted with `cryptography.Fernet` before storage
- Encryption key derived from `JWT_SECRET`
- Managed via `app/services/user_model_service.py`
- Custom adapter in `app/services/custom_model_adapter.py`

### Checkpoint System

Conversation state persistence using LangGraph checkpoints:
- Stored in PostgreSQL via `langgraph-checkpoint-postgres`
- Enables conversation branching and "time travel"
- Managed by `app/core/checkpointer.py` and `app/services/checkpoint_service.py`

### Frontend Architecture

**State Management:**
- Zustand stores in `frontend/src/store/`
- React Query for server state

**Key Components:**
- `components/chat/` - Chat interface, message bubbles, model selector
- `components/knowledge/` - Knowledge base management
- `components/settings/` - User profile, model configuration
- `hooks/useSSEChat.ts` - Server-Sent Events for streaming responses
- `hooks/useMessageTree.ts` - Conversation branching logic

## Coding Conventions

**From AGENTS.md:**
- **Chinese comments required** - Add detailed Chinese comments to all code, including method internals
- **Avoid `==` operator** - Use utility classes for comparisons (e.g., `Objects.isNull()` style)
- **Import packages** - Don't use fully qualified class names
- **Answer questions in Chinese** - When responding to user queries
- **Third-party libraries** - Use MCP context7 tool to consult official documentation before implementation

**Python Style:**
- Ruff for linting (line length: 100)
- Black for formatting
- Type hints encouraged but not strictly enforced
- Async/await for I/O operations

**Database Interactions:**
- Use SQLAlchemy async sessions
- Connection pooling configured via `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`

## Testing

```bash
# Run all tests
cd backend && uv run pytest -v

# Run specific test file
cd backend && uv run pytest tests/test_health.py -v

# Run with coverage
cd backend && uv run pytest --cov=app tests/
```

Test files located in `backend/tests/`:
- `test_health.py` - Health check endpoint
- `test_oss.py` - OSS integration
- `test_upload.py` - File upload functionality
- `conftest.py` - Pytest fixtures

## Common Tasks

### Adding a New Agent Node

1. Create node file in `backend/app/nodes/your_node.py`
2. Implement node function with signature: `def your_node(state: AgentState) -> dict`
3. Register in `backend/app/agent/graph.py`:
   - Add node to workflow: `workflow.add_node("your_node", your_node)`
   - Add edges/conditional routing as needed
4. Update `AgentState` TypedDict if new state fields required

### Adding a New Tool

1. Create tool in `backend/app/tools/your_tool.py`
2. Define using `@tool` decorator or `StructuredTool`
3. Register in `backend/app/tools/__init__.py` → `AVAILABLE_TOOLS`
4. Tool will be automatically bound to agent in `create_default_agent()`

### Adding a New API Endpoint

1. Create route in `backend/app/api/routes/your_route.py`
2. Implement service logic in `backend/app/services/your_service.py`
3. Register router in `backend/app/api/router.py`
4. Add frontend API client in `frontend/src/api/your_api.ts`

### Database Schema Changes

1. Modify models in `backend/app/models/`
2. Generate migration: `make db-revision` (enter description when prompted)
3. Review generated migration in `backend/migrations/versions/`
4. Apply migration: `make db-migrate`

## Troubleshooting

**Backend won't start:**
- Check `.env` file exists and has required variables
- Verify PostgreSQL and Redis are running: `docker compose ps`
- Check logs: `docker compose logs -f backend`

**Database connection errors:**
- Ensure pgvector extension is enabled (automatic with `pgvector/pgvector:pg16` image)
- Verify `DB_PASSWORD` matches between `.env` and docker-compose

**Embedding errors:**
- Local embedding requires downloading model on first run (BAAI/bge-small-zh-v1.5)
- For remote embedding, set `AI_EMBEDDING_PROVIDER=openai` and provide `AI_EMBEDDING_API_KEY`

**Celery tasks not processing:**
- Check Celery worker is running: `docker compose ps celery-worker`
- View worker logs: `docker compose logs -f celery-worker`
- Verify Redis connection (Celery uses separate DB: `CELERY_BROKER_DB=1`)

## Service URLs

**Local Development:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- API Docs: http://localhost:8080/docs

**Docker:**
- Frontend: http://localhost:3001
- Backend API: http://localhost:8081
- API Docs: http://localhost:8081/docs
- Health Check: http://localhost:8081/api/chat/health
