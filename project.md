# Multi-agent code review orchestrator — project brief

## Goal

A backend-fundamentals learning project. The point is to actually learn distributed
systems / backend engineering by building it — not to have Claude generate a working
app for the portfolio. Claude Code's role here is to **scaffold, explain, and
implement pieces under direction** — walk through design tradeoffs, write code
incrementally alongside the author, and stop to check in before generating large
chunks autonomously. Prioritize understanding over speed of completion.

## Origin

Inspired by the *architecture pattern* in a YouTube video about a multi-agent AI
interview platform (LangGraph + Redis + Docker + microservices, MERN stack). This
project applies the same pattern (agent orchestration, shared state via Redis,
Dockerized services) to a different domain — automated PR code review — and is
intentionally not a clone of the interview platform.

## What it does (functional spec)

A GitHub PR is opened or updated. Without any manual step, the system:

1. Parses the diff to find what changed
2. Computes the "blast radius" — everything downstream that could break
3. Scores the risk of the change (blast radius size + test coverage + code churn)
4. Suggests tests or refactors for impacted code that isn't covered
5. Posts a summary comment on the PR, and stores a fuller report for a dashboard

## End-to-end flow

**User flow:**
Developer opens/updates a PR → GitHub webhook fires (or a manual trigger for
testing) → pipeline runs asynchronously → results appear as a PR comment and,
optionally, a dashboard entry with per-agent drill-down. Two rapid pushes to the
same PR should not double-run the pipeline (idempotency on PR ID + commit SHA).

**Tech flow:**
```
Webhook receiver (FastAPI)
  → validates GitHub signature, dedups by (PR ID, commit SHA)
  → enqueues job to Redis

Redis queue
  → job picked up by orchestrator

Orchestrator (LangGraph state machine)
  → diff-parser agent (runs first)
  → impact-analyzer + risk-scorer agents (run in parallel, depend on diff-parser)
  → suggestion agent (runs last, depends on both)
  → LangGraph checkpoints intermediate state to Redis (crash recovery)

Report composer
  → merges all agent outputs into one structured report
  → persists to Postgres
  → posts summary as a PR comment via GitHub API
```

## Agents

- **Diff-parser** — fetches the PR diff via GitHub API, identifies changed
  files/functions. Everything else depends on this; build it first.
- **Impact-analyzer** — statically parses the Python repo's AST to build a call
  graph, then finds all downstream callers of changed functions (the "blast
  radius"), cross-referenced against test coverage. This is the same core idea as
  an earlier standalone "dependency impact analyzer" concept — here it's one node
  in the graph instead of a standalone tool.
- **Risk-scorer** — combines blast-radius size, test coverage gaps, and historical
  churn/bug density (from git log) into a single risk score. Formula/weights not
  yet defined — this is a design decision to make deliberately, not default on.
- **Suggestion agent** — RAG over the repo's existing tests (embedded in Qdrant) so
  it drafts suggested tests/refactors in the codebase's actual style, rather than
  generic ones.
- **Report composer** — merges outputs from all four agents into the final report;
  posts to GitHub, persists to Postgres.

## Tech stack

- **Python + FastAPI** — webhook receiver, service APIs
- **LangGraph** — agent orchestration / state graph
- **Redis** — job queue between webhook receiver and orchestrator, and LangGraph
  state checkpointing between agents
- **PostgreSQL** — job status, final reports, cached call graphs (keyed by commit
  SHA)
- **Qdrant** — embeddings of the repo's existing tests, for the suggestion agent's
  RAG retrieval
- **Docker / Docker Compose** — one container per service
- **GitHub API** — fetching diffs, posting PR comments; needs rate-limit handling
- **Python `ast` module** (or similar) — static analysis for the call graph

## Constraints on how Claude Code should work here

- The author wants to design and write most of this themselves. Claude Code should
  favor explaining approaches, sketching interfaces/schemas, and pair-implementing
  in small pieces — not generating whole services unprompted.
- The specific backend problems worth slowing down for (this is where the actual
  learning is): webhook idempotency, Redis-based job queueing and state
  checkpointing/crash recovery, call-graph cache invalidation, and GitHub API rate
  limiting. Don't paper over these with a quick library call if there's a chance to
  actually implement and understand the mechanism.

## Open decisions — do not assume, ask or flag these

- AST parsing scope: Python-only for v1, or others later?
- GitHub auth model: GitHub App install flow vs a personal access token
- How test coverage data is obtained (pytest-cov output? parsed CI artifacts?)
- Exact risk-scoring formula and weights — undecided
- Call-graph cache invalidation strategy (per-commit? per-changed-file?)
- Deployment target: local Docker Compose only for now, or cloud later (AWS is a
  plausible target given prior experience with it)
- Is a dashboard in scope for v1, or PR-comment-only to start?
- Postgres schema (jobs, reports, call-graph tables) — not designed yet
- Redis checkpoint schema for LangGraph state — not designed yet

## Suggested build order

1. Diff-parser agent (foundation everything else depends on)
2. Impact-analyzer (blast radius)
3. Risk-scorer
4. Suggestion agent (RAG via Qdrant)
5. Report composer + PR comment posting
6. Orchestration wiring — LangGraph graph, Redis queue, webhook receiver
7. Dockerize all services