# Development Task Breakdown — GitHub PR Review Orchestrator

## Phase 0 — Project Setup (DONE)
- [x] Create directory structure: backend/, frontend/
- [x] Create backend virtual environment
- [x] Scaffold frontend with Vite + React + TypeScript
- [x] Create .env.template with auth/config placeholders
- [x] Setup Python venv in backend

## Phase 1 — GitHub Authentication & Webhook Receiver
- [~] **1.1 — GitHub App auth module** (`backend/src/auth.py`)
  - [x] JWT generation from app private key
  - [x] Installation token minting via GitHub API
  - [x] Redis-based token caching with TTL underflow protection
  - [x] Webhook signature verification (X-Hub-Signature-256)
  - [ ] Add retry-on-failure wrapper for token refresh
  - [ ] Write basic auth tests (mocked)
- [ ] **1.2 — Webhook receiver** (`backend/src/api/webhook.py`)
  - FastAPI endpoint `/webhook/github` receiving POST
  - Verify signature using GitHubAuth, reject 401 on failure
  - Parse event type from `X-GitHub-Event` header
  - Deduplicate using Redis SET of `PR:{id}:{sha}` keys
  - Enqueue job to Redis queue with payload
- [ ] **1.3 — Redis job queue producer**
  - Push job payload to `LIST github:jobs:pending`
  - Simple job schema: `{ "pr_id", "sha", "repo", "installation_id" }`

## Phase 2 — Orchestration Layer
- [ ] **2.1 — Redis consumer / orchestrator runner**
  - Pop jobs from `github:jobs:pending` (BLPOP for blocking)
  - Spawn LangGraph orchestrator per job
- [ ] **2.2 — LangGraph state machine**
  - Define nodes: DiffParser → [ImpactAnalyzer + RiskScorer (parallel)] → SuggestionAgent → ReportComposer
  - Configure Redis checkpoint serializer for crash recovery
- [ ] **2.3 — Postgres models** (`backend/src/models/report.py`)
  - SQLAlchemy schemas for jobs, reports, call_graph_cache, coverage_data
  - Basic DB connection and migration scaffold

## Phase 3 — Analysis Agents (Backend Learning Modules)
- [ ] **3.1 — Diff-parser agent** (`backend/src/agents/diff_parser.py`)
  - Fetch PR diff via GitHub API using auth module
  - Parse diff into changed files + changed functions (AST-based for Python)
  - Output structured list of changed symbols
- [ ] **3.2 — Impact-analyzer agent** (`backend/src/agents/impact_analyzer.py`)
  - Build call graph via Python `ast` module on repo source
  - Cross-reference changed functions vs callers (blast radius)
  - Cross-ref test coverage data (from stored coverage XML or pytest-cov)
  - Cache call graph per commit SHA in Postgres
- [ ] **3.3 — Risk-scorer agent** (`backend/src/agents/risk_scorer.py`)
  - Inputs: blast_radius_size, coverage_gaps, git_churn_score
  - Define risk scoring formula (open decision — decide during implementation)
  - Output: numeric risk score + breakdown
- [ ] **3.4 — Suggestion agent** (`backend/src/agents/suggestion_agent.py`)
  - Query Qdrant vector store for similar past tests
  - Generate test/refactor suggestions matching repo style
  - (RAG setup to be configured after Qdrant is running)
- [ ] **3.5 — Report composer** (`backend/src/agents/report_composer.py`)
  - Merge outputs from all four agents into final report object
  - Persist full report to Postgres
  - Return summary markdown for PR comment

## Phase 4 — PR Comment + Dashboard API
- [ ] **4.1 — GitHub PR commenting**
  - Post comment via GitHub Issues API (`/repos/{owner}/{repo}/issues/{pr}/comments`)
  - Idempotency: check existing comments before posting (or edit existing)
- [ ] **4.2 — Dashboard API endpoints** (`backend/src/api/`)
  - `GET /api/reports?repo={owner/repo}` — list past reviews
  - `GET /api/reports/{id}` — full report with per-agent drill-down
  - `GET /api/reports/{id}/agents/{agent_name}` — deep dive into agent output

## Phase 5 — Testing & Dockerization
- [ ] **5.1 — Backend tests**
  - Unit tests for auth.py, each agent
  - Integration test: full webhook → comment flow (mocked GitHub)
- [ ] **5.2 — Frontend** (built alongside backend as agents complete)
  - Dashboard page: list of past reviews
  - Report detail page with collapsible agent sections
  - Use React Query for data fetching, Tailwind for styling
- [ ] **5.3 — Docker Compose**
  - Services: redis, postgres, qdrant, backend (uvicorn), frontend (nginx or vite)
  - Shared network, env var injection from .env

## Phase 6 — (Post-v1) Hardening
- [ ] GitHub App token refresh retry wrapper
- [ ] Actual webhook server reachable via ngrok/tunnel (dev)
- [ ] Rate-limit handling: parse Retry-After headers, queue backoff
- [ ] Call-graph cache invalidation strategy (per-changed-file)
