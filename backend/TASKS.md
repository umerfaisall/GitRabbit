# Backend build plan

Working breakdown for the orchestrator backend, in build order (per project.md).
Each task lists *why* it exists, not just what it is — the point of this project
is understanding the mechanism, not ticking boxes. Tasks marked **[DECISION]**
block on an open question from project.md and shouldn't be started until that's
answered.

Checkboxes are for tracking progress by hand as we pair on this.

---

## Phase 0 — project skeleton

- [x] FastAPI app boots, `/health` responds — done (mock scaffold)
- [x] Replace mock endpoints with real structure: split `app/main.py` into
      `app/api/` (routes), `app/services/` (business logic), `app/models/`
      (Pydantic schemas)
  - Why: the mock crammed everything into one file on purpose (it was just for
    the UI to point at). Once real logic lands, one file becomes unreadable
    and untestable.
- [x] Add `.env` / `app/config.py` (pydantic-settings) for GitHub token, Redis
      URL, Postgres URL, webhook secret
  - Why: these are all things that differ between your machine, CI, and
    eventually prod — hardcoding any of them means you're one commit away
    from leaking a secret or breaking on another machine.
- [x] Set up pytest + a `tests/` folder with one trivial test (e.g. `/health`
      returns 200)
  - Why: every phase below is easier to trust if there's a working test
    harness before the first real logic goes in, not bolted on after.

---

## Phase 1 — webhook receiver

This is the entry point: GitHub → your system. Gets it wrong once and either
you miss real PR events or you process fake/duplicate ones.

- [x] `POST /webhooks/github` endpoint that accepts the raw payload
  - Why: this is the contract GitHub calls — has to exist before anything
    else in this phase makes sense.
- [x] Verify the `X-Hub-Signature-256` header (HMAC-SHA256 over the raw body,
      using the webhook secret)
  - Why: without this, anyone who finds your endpoint URL can post a fake
    "PR opened" event and trigger a pipeline run pretending to be GitHub.
    This is the actual security boundary of the whole system.
- [x] Reject/ack-and-drop events that aren't `pull_request` with action
      `opened` or `synchronize`
  - Why: GitHub sends you *every* subscribed event type (comments, reviews,
    labels...). Most of them aren't a "PR changed, re-analyze it" signal —
    processing them would run the pipeline for no reason or crash on a
    payload shape you didn't design for.
- [x] Extract `(pr_id, commit_sha, repo)` from the payload into a typed model
  - Why: everything downstream (dedup key, diff-parser input, Redis job) is
    keyed on this triplet — get the extraction wrong and every agent
    downstream silently works on the wrong PR or commit.
- [ ] **[DEFERRED]** Idempotency store: how do you remember "I already
      enqueued a job for (pr_id, sha)"? Options: a Postgres `jobs` table
      unique constraint, or a Redis `SETNX` key with TTL.
  - Why deferred: this guards against double-running the pipeline when
    GitHub retries a webhook delivery, or a dev pushes twice in quick
    succession. Real failure mode, but low-stakes here — this isn't
    customer-facing and a duplicate run just wastes some compute, it
    doesn't corrupt anything. Worth doing once the pipeline itself works
    end to end; not worth blocking on now.
- [x] Push the extracted event onto the Redis queue (`pr-review-jobs` list),
      then return 202 Accepted (not the pipeline result) — no dedup check yet,
      every valid event enqueues a job
  - Why: GitHub expects a fast response and will retry on timeout — if the
    webhook handler blocks on the actual pipeline work, GitHub will re-send
    the same event and you'll be fighting your own retries. Pushing to the
    queue and returning immediately (rather than running the pipeline
    synchronously) is what makes the async architecture actually async.
- [ ] Log/metric malformed or unsigned requests separately from valid-but-
      irrelevant events
  - Why: a wave of signature failures is a signal someone's probing the
    endpoint; a wave of "wrong event type" is just normal GitHub traffic.
    Conflating them in logs makes real problems invisible.

---

## Phase 2 — Redis job queue

- [x] **Queue primitive: Redis List** (`LPUSH`/`BRPOP`) — decided, already in
      use from Phase 1
  - Why chosen: build the simplest working version first, end to end, before
    layering on Streams' extra mechanics (consumer groups, `XACK`,
    `XPENDING`). Once the whole pipeline works with List, swap in Streams as
    a deliberate, focused upgrade — see "Planned future upgrade" below. Don't
    try to learn "what's a queue" and "what's a consumer group" at once.
- [x] Define the job payload schema (pr_id, commit_sha, repo, action) — this
      is `PrEvent` in `app/models/webhook.py`, already built and in use
  - Why: this is the contract between the webhook receiver (producer) and
    the orchestrator (consumer) — changing it later means touching both
    sides.
- [x] Producer: webhook receiver pushes a job after the filter passes — done
      in `app/api/webhook.py` (`redis_client.lpush(...)`)
  - Why: connects Phase 1's output to Phase 2's queue — nothing downstream
    runs without this.
- [x] Consumer skeleton: a worker loop that blocks waiting for jobs and logs
      what it received (no orchestrator logic yet) — `app/worker.py`,
      run standalone via `uv run python -m app.worker`
  - Why: proves the queue actually moves data end-to-end before adding the
    complexity of LangGraph on top — isolates "is the queue wired right"
    from "is the graph wired right."
  - Note: hit a real transient-disconnect issue during testing (the Redis
    connection died while idling on `BRPOP`, likely Docker Desktop/WSL2
    networking dropping it) — fixed by using a bounded `BRPOP` timeout in a
    loop and catching `ConnectionError`/`TimeoutError` around it instead of
    letting either kill the process. Logged in DECISIONS.md.

**Planned future upgrade (not a gap — a deliberate later exercise):** once
the full pipeline works end-to-end with the List queue, swap it for Redis
Streams (consumer groups, `XACK`, `XPENDING`) specifically to feel what
crash recovery buys you — kill the worker mid-job, restart it, watch it
reclaim the stuck job. Doing this after the pipeline works means modifying
two files you already understand, instead of learning "queue" and "consumer
group" simultaneously.

---

## Phase 3 — diff-parser agent (first LangGraph node)

- [x] **GitHub auth model: GitHub App** — decided
  - Why: scoped per-repo install, higher rate limits, and it's the actual
    mechanism a real automated PR-review integration would use (this is not
    a hypothetical — GitHub explicitly recommends Apps over PATs for
    anything acting on behalf of a bot/integration rather than a person).
    More setup upfront (registering the app, JWT-signing to get an
    installation token) than a PAT, but that setup *is* part of what's
    worth understanding here — this determines how every GitHub API call
    authenticates, so worth doing deliberately rather than retrofitting.
- [x] Sign a JWT with the App's private key and exchange it for an
      installation access token — `app/services/github_auth.py`
      (`get_installation_token()` builds the JWT, `post_installation_token()`
      exchanges it; verified end-to-end, returns a real `ghs_...` token)
  - Why: this is the two-layer auth mechanism GitHub Apps require — the JWT
    proves "I am this app," the installation token is what actually
    authenticates real API calls. Got this working before writing any real
    API client code so auth isn't a variable when debugging the next piece.
- [x] GitHub API client wrapper: fetch PR diff (`GET /repos/{owner}/{repo}/
      pulls/{pr}/files`) — `app/services/github_client.py`, `get_pr_files()`.
      Code complete; live test against a real PR still pending.
  - Why: this is the actual data source for the entire pipeline — nothing
    downstream has anything to analyze without it.
- [x] Basic rate-limit handling: read `X-RateLimit-Remaining` /
      `X-RateLimit-Reset` from responses, back off when close to the limit —
      `check_rate_limit_of_response()` in `app/services/github_client.py`,
      raises `GitHubRateLimitError` if remaining < 5 or on a rate-limit 403
  - Why: project.md flags this as a real mechanism to implement, not stub —
    a burst of PR activity (or a bug that retries too eagerly) can exhaust
    your GitHub API quota and stall the whole system silently.
- [x] Parse the diff into changed files + changed line ranges —
      `parser_patch()` in `app/services/diff_parser.py`, returns
      `[(start_line, end_line), ...]` per file's patch text, tested against
      a fake multi-hunk patch including a count-omitted single-line hunk
  - Why: raw unified diff text isn't directly usable — everything after this
    needs "which files, which lines" as structured data.
- [x] Map changed line ranges to changed *function* names (parse the file's
      AST, find which function defs the changed lines fall inside) —
      `find_changed_functions()` in `app/services/diff_parser.py`, tested
      against a fake multi-function source with overlapping/non-overlapping
      ranges
  - Why: impact-analyzer needs function-level granularity to walk the call
    graph — file-level or line-level isn't precise enough to answer "what
    calls this."
- [x] Define diff-parser's output schema (this becomes the first piece of
      LangGraph state) — `DiffParserOutput`/`ChangedFile` in
      `app/models/diff.py`, assembled by `DiffParser()` in
      `app/services/diff_parser.py`, which wires together `get_pr_files`,
      `parser_patch`, `get_file_content`, and `find_changed_functions`.
      Skips function-mapping for removed files and non-`.py` files
      (pragmatic default — AST scope is Python-only for v1 per project.md's
      open question). Code complete; still needs a live test against a
      real PR (same pending item as `get_pr_files` itself).
  - Why: impact-analyzer and risk-scorer both consume this — it's the
    interface contract for the rest of the graph, so it's worth nailing down
    deliberately rather than growing it ad hoc.

**Phase 3 complete** (pending live verification against a real PR).

---

## Phase 4 — impact-analyzer (blast radius)

- [ ] Build a call graph of the repo using the `ast` module (walk all `.py`
      files, record function defs and call sites)
  - Why: this graph is the core data structure the whole "blast radius"
    concept depends on — see the earlier discussion of what blast radius
    means.
- [ ] **[DECISION]** Cache invalidation: is the call graph cached per-commit-
      SHA (rebuild only on new commits) or per-changed-file (patch the
      existing graph)?
  - Why: full-repo AST parsing on every PR push doesn't scale, but an
    incrementally-patched graph can drift from reality if invalidation logic
    has a bug — this is explicitly called out in project.md as worth
    implementing for real, not skipping.
- [ ] Persist/read cached call graphs from Postgres, keyed by commit SHA
  - Why: ties into the Postgres schema decision below — the cache needs
    somewhere durable to live across pipeline runs.
- [ ] Walk the graph backwards from each changed function to find all
      (transitive) callers
  - Why: this is the actual blast-radius computation — direct callers alone
    under-report risk for widely-used utility functions.
- [ ] **[DECISION]** How is test coverage data obtained? (parse `pytest-cov`
      XML/JSON output locally, or pull a CI artifact from a prior run)
  - Why: "uncovered callers" is only meaningful if coverage data is real —
    picking the source determines whether this runs standalone or depends on
    CI having already run.
- [ ] Cross-reference blast-radius callers against coverage data to flag
      uncovered ones
  - Why: this is the signal risk-scorer and suggestion-agent both act on —
    an uncovered caller of changed code is the concrete "this could break
    silently" case the whole project exists to catch.

---

## Phase 5 — risk-scorer

- [ ] **[DECISION]** Risk formula and weights: how do blast-radius size,
      coverage gap, and churn/bug density combine into one score?
  - Why: project.md is explicit this isn't decided yet and shouldn't be
    defaulted on — a bad formula (e.g. treating a 1-caller blast radius the
    same as a 50-caller one) makes the risk score meaningless, and this is
    the one piece of the system that's a judgment call rather than an
    engineering mechanism.
- [ ] Compute churn/bug density from git log (e.g. commit frequency touching
      the changed files, or commits with "fix"/"bug" in the message)
  - Why: a file that changes constantly and gets bugfixed often is riskier
    to touch than a stable one — blast radius and coverage alone don't
    capture that history.
- [ ] Combine the three inputs into a single score + a breakdown (matching
      the `risk_score.breakdown` shape the mock UI already expects)
  - Why: keeping the breakdown (not just a final number) is what makes the
    score explainable on the PR comment — "risk 78" alone tells a reviewer
    nothing about *why*.

---

## Phase 6 — suggestion agent (RAG)

- [ ] Stand up Qdrant (local, via Docker) and pick an embedding model
  - Why: needed before anything can be embedded or retrieved.
- [ ] Embed the repo's existing test files into Qdrant
  - Why: the point of RAG here is suggesting tests in the *codebase's own
    style* — without embedding real examples, this degrades into generic
    boilerplate suggestions.
- [ ] Retrieval step: given an uncovered caller from impact-analyzer, find
      the most similar existing tests
  - Why: this is what grounds the suggestion in something concrete rather
    than a hallucinated test structure.
- [ ] Generate a suggested test/refactor using the retrieved examples as
      style reference
  - Why: this is the actual output artifact the report shows to a reviewer.
- [ ] Decide re-embedding trigger (on every push? only when test files
      change?)
  - Why: re-embedding the whole test suite on every PR is wasteful; only
    doing it when test files actually changed keeps Qdrant in sync without
    redundant work.

---

## Phase 7 — report composer + orchestration wiring

- [ ] **[DECISION]** Postgres schema: `jobs`, `reports`, `call_graphs` tables
      — columns, keys, relations not designed yet
  - Why: multiple other tasks above (idempotency store, call-graph cache)
    already depend on this existing — worth designing once, deliberately,
    rather than growing it table-by-table as each phase needs a place to
    write.
- [ ] **[DECISION]** Redis checkpoint schema for LangGraph state — not
      designed yet
  - Why: this is what makes "LangGraph checkpoints intermediate state to
    Redis" in project.md's tech flow actually mean something concrete —
    without a defined shape, crash recovery can't be tested meaningfully.
- [ ] Define the LangGraph `StateGraph`: nodes (diff-parser, impact-analyzer,
      risk-scorer, suggestion-agent, report-composer) and edges (impact-
      analyzer + risk-scorer run in parallel after diff-parser; both feed
      suggestion-agent)
  - Why: this is the actual orchestration graph project.md describes — up to
    this point every phase has been building a node in isolation.
- [ ] Wire LangGraph's checkpointer to Redis using the schema above
  - Why: this is what enables resuming a pipeline after a crash instead of
    restarting from diff-parser every time — the concrete crash-recovery
    mechanism the project is meant to teach.
- [ ] Report composer: merge outputs from all four agents into one
      structured report, write to Postgres
  - Why: this is the durable record the dashboard reads and what the PR
    comment is generated from — it's the single source of truth for a given
    (pr_id, commit_sha).
- [ ] Post the summary as a PR comment via the GitHub API (create vs. update
      an existing bot comment on re-runs)
  - Why: updating an existing comment (rather than posting a new one each
    push) keeps the PR thread from being spammed on every commit — worth
    deciding deliberately since it changes the API call and requires
    tracking the comment id per PR.
- [ ] Consumer loop (from Phase 2) now runs the actual graph instead of just
      logging
  - Why: closes the loop — webhook → queue → graph → report → comment, fully
    wired end to end.

---

## Phase 8 — Dockerize

- [ ] `Dockerfile` for the backend service
- [ ] `docker-compose.yml` wiring backend + Redis + Postgres + Qdrant
- [ ] Confirm the whole pipeline runs via `docker compose up` with a manually
      triggered fake webhook payload
  - Why: this is the actual end-to-end proof the system works outside your
    local dev environment — the manual trigger mentioned in project.md's
    "user flow" as the testing path before real webhooks are wired to a
    public URl.

---

## Decisions to resolve before their phase starts

Flagging again in one place so none get defaulted on silently:

1. Idempotency store: Postgres unique constraint vs Redis SETNX+TTL (Phase 1)
2. Redis queue primitive: List vs Streams (Phase 2)
3. GitHub auth model: GitHub App vs PAT (Phase 3)
4. Call-graph cache invalidation: per-commit vs per-changed-file (Phase 4)
5. Test coverage data source: pytest-cov output vs CI artifact (Phase 4)
6. Risk-scoring formula and weights (Phase 5)
7. Postgres schema for jobs/reports/call_graphs (Phase 7)
8. Redis checkpoint schema for LangGraph state (Phase 7)
