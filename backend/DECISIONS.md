# Decisions log

A running record of the open decisions from project.md as they get resolved
— so the reasoning doesn't get lost once TASKS.md checkboxes are ticked.
Newest at the bottom.

---

## Queue primitive: Redis List (not Streams) — for now

**Decided:** build the job queue between the webhook receiver and the worker
using a Redis List (`LPUSH` / `BRPOP`), not Redis Streams (`XADD` / consumer
groups).

**Why:** Streams give you real crash recovery — if a worker dies mid-job,
the job isn't lost, another worker (or the same one on restart) can find and
reclaim it via `XPENDING`. A List doesn't have this: `BRPOP` removes the job
the instant a worker picks it up, so a crash mid-job loses it silently, with
no trace.

Streams is the more complete answer, but it's also more moving parts
(consumer groups, acking, reclaim logic) — building it before the basic
pipeline even works end-to-end would mean learning "what's a queue" and
"what's a consumer group" at the same time. Chose to get the simplest
version working first.

**Not a gap — a planned upgrade.** Once the full pipeline works end-to-end
(webhook → queue → worker → eventually the LangGraph pipeline → report),
come back and swap List for Streams specifically as a hands-on exercise:
kill the worker mid-job, restart it, and watch it reclaim the stuck job.
That's the concrete, felt reason to use Streams — better to learn it after
feeling the List version's gap than to build it upfront on faith.

**Revisit when:** the pipeline works end-to-end with List, *or* sooner if
a dropped job during dev testing actually becomes annoying enough to fix
early.

---

## Idempotency (dedup on rapid re-delivery) — deferred

**Decided:** don't build a dedup check yet for repeated webhook deliveries
(GitHub retrying, or two fast pushes to the same PR/commit). Every valid
event currently enqueues a new job, even if it's a duplicate of one already
queued or processed.

**Why deferred:** this project isn't customer-facing and has no real
traffic — a duplicate pipeline run wastes some compute but doesn't corrupt
anything or affect a real user. Not worth blocking Phase 1 on choosing
between a Postgres unique constraint vs a Redis `SETNX`+TTL key before the
rest of the pipeline even exists.

**Revisit when:** the pipeline works end-to-end, or if this ever needs to
handle real GitHub traffic (where retries are common, not hypothetical).

---

## Worker must tolerate transient Redis disconnects

**What happened:** while testing the Phase 2 consumer (`app/worker.py`), the
first job round-tripped fine, but the process crashed with
`redis.exceptions.TimeoutError` while idling on `BRPOP` waiting for the next
one — the underlying connection died mid-wait. Most likely cause in this
environment: Docker Desktop's Windows/WSL2 networking silently dropping an
idle TCP connection to the containerized Redis.

**Fix:** call `BRPOP` with a bounded timeout (5s) in a loop instead of
blocking forever, and wrap the call in a `try/except` catching
`redis.exceptions.ConnectionError` / `TimeoutError`, just looping again on
either. `redis-py`'s connection pool re-establishes a fresh connection on
the next call automatically.

**Why this matters beyond just fixing the crash:** a real background worker
runs indefinitely and *will* eventually see a transient network blip —
it should reconnect and keep going, not die. This is a small, real instance
of the "crash recovery" mindset project.md calls out, distinct from the
List-vs-Streams job-loss question above: this is about the worker
*process* surviving a connection hiccup, not about recovering a specific
in-flight job.

---

## GitHub auth model: GitHub App (not a personal access token)

**Decided:** authenticate to the GitHub API as a GitHub App (JWT-signed app
auth → installation access token), not a personal access token.

**Why:** a PAT is simpler to set up (no app registration, no JWT signing)
but it's tied to a personal GitHub account and carries lower rate limits.
A GitHub App is scoped per-repo via an "installation," gets higher rate
limits, and is the actual mechanism GitHub recommends for anything acting
as a bot/integration rather than a person — which is exactly what this
system is. Chose to build the real thing here rather than the shortcut,
since understanding this auth flow (app → JWT → installation token) is
itself one of the backend-fundamentals goals of the project, not just
plumbing to get past.

**Tradeoff accepted:** more upfront setup — registering the app in GitHub's
UI, generating/storing a private key, signing a JWT, exchanging it for a
short-lived installation token — before the first real API call can be
made.
