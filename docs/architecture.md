# Architecture decisions

Why the product is built the way it is. One entry per decision (ADR). Maintained by Claude Code through the
`/record-decision` skill. Check the file with `python3 .claude/hooks/docs_guard.py check`.

**Rules**

- IDs are permanent (`ADR-NNN`). Entries are never deleted: a reversed decision becomes `superseded`.
- Statuses: `proposed` (under discussion, not decided), `accepted` (decided), `superseded` (replaced).
- Claude proposes; **only the user accepts**. Never mark an entry `accepted` without the user's say-so.
- Entries dated 2026-10-28 were reconstructed from CLAUDE.md, README.md and the code as already built, so they
  are `accepted`. Correct them if they are wrong.
- Keep the Index table in sync with the entries. The validator checks it.

## Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| ADR-001 | One FastAPI service runs the bot, the web UI and the scheduler | accepted | 2026-10-28 |
| ADR-002 | PostgreSQL + pgvector with async SQLAlchemy 2 and Alembic | accepted | 2026-10-28 |
| ADR-003 | Claude tool-use loop as the agent | accepted | 2026-10-28 |
| ADR-004 | OpenAI Whisper for voice notes only | accepted | 2026-10-28 |
| ADR-005 | Proxycurl for people, Tavily for web and company search | accepted | 2026-10-28 |
| ADR-006 | Access through a bot_users table with owners | accepted | 2026-10-28 |
| ADR-007 | Server-rendered web UI: Jinja2 + vendored HTMX, generic CRUD | accepted | 2026-10-28 |
| ADR-008 | Web sign-in with the Telegram Login Widget and a signed cookie | accepted | 2026-10-28 |
| ADR-009 | APScheduler inside the app for the digest | accepted | 2026-10-28 |
| ADR-010 | Docker everywhere; Railway for production | accepted | 2026-10-28 |
| ADR-011 | Conversation history in the database, keyed by Telegram user ID | accepted | 2026-10-28 |
| ADR-012 | uv for dependencies, ruff for lint, pytest for tests | accepted | 2026-10-28 |
| ADR-013 | Workspaces in one shared database: workspace_id on every table, Postgres RLS as backstop | accepted | 2026-10-28 |
| ADR-014 | One shared bot and deployment; tenant resolved in one place so an org can be split out | accepted | 2026-10-28 |
| ADR-015 | Usage ledger table, with quotas checked before every paid call | accepted | 2026-10-28 |
| ADR-016 | Events are workspace-scoped conferences; records carry an optional event_id | accepted | 2026-10-28 |
| ADR-017 | Event status computed from dates; attendance in an event_attendees table | accepted | 2026-10-29 |

## Entries

### ADR-001 — One FastAPI service runs the bot, the web UI and the scheduler
- Status: accepted
- Date: 2026-10-28
- Related: ADR-007, ADR-009, ADR-010

**Context.** One developer, one small deployment. Separate services for the webhook, a web app and a worker
would multiply deploys and configuration.
**Decision.** `app/api/main.py` builds one FastAPI app. Its lifespan seeds owners, starts python-telegram-bot
(webhook mode when `APP_ENV=production`, otherwise long polling after deleting the webhook), starts the
scheduler, and mounts the web routers.
**Consequences.** One process to run and monitor. A slow agent turn holds a worker; the scheduler runs once
per process, so scaling to several replicas would send the digest several times. Starting in development with
the production token deletes the production webhook (the bot identity is logged at startup to make that visible).

### ADR-002 — PostgreSQL + pgvector with async SQLAlchemy 2 and Alembic
- Status: accepted
- Date: 2026-10-28
- Related: REQ-023

**Context.** Relational data (people, companies, meetings, tasks) plus a planned semantic search.
**Decision.** PostgreSQL 16 with the pgvector extension (`pgvector/pgvector:pg16` locally), async SQLAlchemy 2
over asyncpg, Alembic migrations committed in `alembic/versions/` and applied at startup. Repositories in
`app/repositories/` hold the queries and only `flush`; the caller owns the transaction. `postgres://` URLs
(Railway) are rewritten to `postgresql+asyncpg://`.
**Consequences.** `Vector(1536)` columns exist but nothing fills them yet. Every model change needs a migration.

### ADR-003 — Claude tool-use loop as the agent
- Status: accepted
- Date: 2026-10-28
- Related: REQ-001, REQ-019

**Context.** Free-form messages ("just met Ana from Acme, she wants the deck") must become records.
**Decision.** `ConferenceAgent` sends the message, the history and a system prompt rebuilt each turn from the
database (`context_builder.py`) to Claude with the tools in `app/agent/tools.py`, and loops while the model
asks for tools, at most `MAX_TOOL_ROUNDS` (12) rounds. `ToolExecutor` maps each tool to `_tool_<name>`,
returns `{success, error, ...}` dicts and commits per successful tool. The model is `ANTHROPIC_MODEL`
(default `claude-haiku-4-5-20251001`; the original spec said Sonnet).
**Consequences.** Behavior lives mostly in prompts and tool descriptions, so it needs tests with a mocked
Anthropic client. Records saved before a failure stay saved.

### ADR-004 — OpenAI Whisper for voice notes only
- Status: accepted
- Date: 2026-10-28
- Related: REQ-002

**Context.** Voice notes at a conference are faster than typing. Telegram sends Opus `.ogg`.
**Decision.** `whisper-1` through the OpenAI SDK, with the audio sent as is (no conversion). OpenAI is used
for nothing else.
**Consequences.** A second AI vendor and key. Whisper's 25 MB limit is far above a 3-minute voice note.

### ADR-005 — Proxycurl for people, Tavily for web and company search
- Status: accepted
- Date: 2026-10-28
- Related: REQ-008, REQ-009

**Context.** Briefs need background on people and companies.
**Decision.** Proxycurl's LinkedIn API for person profiles (about $0.10 per call, only on request, cached on
the person), Tavily for web and company news (cheap, used freely), Claude to condense Tavily results.
**Consequences.** Two more paid keys; Proxycurl calls must never happen automatically. Apollo is configured as
a possible alternative but not used.

### ADR-006 — Access through a bot_users table with owners
- Status: accepted
- Date: 2026-10-28
- Related: REQ-014, REQ-015, ADR-008

**Context.** The spec gated everything on one `TELEGRAM_ALLOWED_USER_ID`. The product now needs several users
without redeploying.
**Decision.** Table `bot_users` (Telegram ID, name, `is_active`, `is_owner`, `receives_digest`) is the only
source of access. Env IDs are seeded as owners at startup and only ever added. Owners manage users with
`/adduser` and `/removeuser`. Access checks fail closed on database errors.
**Consequences.** No passwords or API keys to manage. All users share one data set: there is no per-user or
per-organization separation of contacts yet, which a multi-customer product would need.

### ADR-007 — Server-rendered web UI: Jinja2 + vendored HTMX, generic CRUD
- Status: accepted
- Date: 2026-10-28
- Related: REQ-016, REQ-017, ADR-001

**Context.** Telegram is poor for reviewing and editing many records. A separate frontend would add a
build, a deploy and an API.
**Decision.** `app/web/`: Jinja2 templates, `app.css` and a vendored `htmx.min.js` (no CDN, no Node build),
served by the same app. `app/web/crud.py` generates list/filter/create/edit/delete/CSV routes from a
per-entity config in `routes/entities.py`.
**Consequences.** Adding an entity is a config entry. Rich client-side interaction would mean revisiting this.

### ADR-008 — Web sign-in with the Telegram Login Widget and a signed cookie
- Status: accepted
- Date: 2026-10-28
- Related: REQ-016, ADR-006

**Context.** Web users are the same people as bot users; a second account system would duplicate access.
**Decision.** The Telegram Login Widget proves account ownership (HMAC check with the bot token, payloads
older than 24 h rejected). The session cookie holds only the Telegram ID, is signed with `WEB_SESSION_SECRET`,
`SameSite=Lax` (the CSRF protection), HTTPS-only in production, 30 days. The user is re-read on every request.
In development the UI signs in as the first owner, because the widget cannot run on localhost.
**Consequences.** The domain must be registered with BotFather. Without `WEB_SESSION_SECRET` the key derives
from the bot token, so rotating the token signs everyone out.

### ADR-009 — APScheduler inside the app for the digest
- Status: accepted
- Date: 2026-10-28
- Related: REQ-011, ADR-001

**Context.** One daily job.
**Decision.** An `AsyncIOScheduler` in the app process with a cron trigger at DIGEST_HOUR:DIGEST_MINUTE in
TIMEZONE, sending to every active user with `receives_digest`.
**Consequences.** No worker or queue. One time zone for all users; several replicas would duplicate the job.

### ADR-010 — Docker everywhere; Railway for production
- Status: accepted
- Date: 2026-10-28
- Related: ADR-001

**Context.** Nothing should need installing on the host beyond Docker.
**Decision.** One `Dockerfile` (Python 3.11, uv) used by `docker compose` locally (app + `db`) and by Railway
(`railway.toml`, `docker/entrypoint.sh` runs migrations then uvicorn, health check `/health`).
`RAILWAY_PUBLIC_DOMAIN` beats `BASE_URL` for the webhook URL.
**Consequences.** The local compose volume mounts the source, and containers create root-owned `__pycache__/`.

### ADR-011 — Conversation history in the database, keyed by Telegram user ID
- Status: accepted
- Date: 2026-10-28
- Related: REQ-018

**Context.** The agent needs recent context, on both Telegram and the web.
**Decision.** Table `conversation_messages` (user ID, role, text). `app/services/conversation.py` loads the
last 20 messages oldest first and appends turns; both surfaces use it.
**Consequences.** Only text is stored: images and tool calls are not replayed, so a badge photo appears in
history as `[Badge photo] <caption>`.

### ADR-012 — uv for dependencies, ruff for lint, pytest for tests
- Status: accepted
- Date: 2026-10-28

**Context.** One Python project, quick to set up.
**Decision.** `pyproject.toml` + `uv.lock` managed with uv. Ruff configured in `pyproject.toml` (line length
100), run with `uvx ruff`. pytest with pytest-asyncio (`asyncio_mode = "auto"`), pytest-mock and factory-boy.
**Consequences.** Ruff is not a declared dependency, so `uvx` picks its version; existing code has older
violations (lint touched files only). Tests run on the host with `uv run pytest` against the compose
database (`localhost:5434`, or `TEST_DATABASE_URL`); `tests/conftest.py` creates `conference_bot_test` and
the `vector` extension if missing (EZE-48). They do not run in the app image: it has no dev dependencies and
its entrypoint always starts the app.

### ADR-013 — Workspaces in one shared database: workspace_id on every table, Postgres RLS as backstop
- Status: accepted
- Date: 2026-10-28
- Related: ADR-006, REQ-024, REQ-025, REQ-026, REQ-027, REQ-028, REQ-030

**Context.** Users from different organizations must never see each other's data (REQ-024). Today no
domain table has an owner column. Alternatives rejected: a database per tenant (N migrations, N pools,
N Railway databases, provisioning on every sign-up), and a schema per tenant (Alembic has to loop over
schemas, with no isolation gain that matters at this size). Repository filters alone are not enough: an
LLM picks the tools and their arguments, so one query that forgets the filter leaks another org's
contacts.
**Decision.** New tables `workspaces` and `workspace_members` (user, workspace, role `admin`|`member`).
Every domain table gets a non-null `workspace_id`, plus `created_by_user_id` (REQ-027). Repositories
filter by workspace. On top of that, Postgres Row-Level Security policies compare `workspace_id` with
`current_setting('app.workspace_id')`, which is set with `SET LOCAL` at the start of every request's
transaction. The app connects with a role that does not own the tables, or the tables use
`FORCE ROW LEVEL SECURITY`. Uniqueness rules become per workspace (for example `people.linkedin_url`). The
migration puts today's data into one workspace and makes every current `bot_users` row a member, with
owners as admins.
**Consequences.** When this ships, ADR-006 becomes `superseded` (Superseded by: ADR-013). One
migration, one pool, and cross-tenant reads fail closed. Every session must set the
workspace before its first query: scheduler jobs and scripts too, and a missing setting returns no rows.
Tests need a cross-workspace leak case for every agent tool and web route. Alembic runs as the owner role.

### ADR-014 — One shared bot and deployment; tenant resolved in one place so an org can be split out
- Status: accepted
- Date: 2026-10-28
- Related: REQ-024, REQ-033, ADR-001, ADR-010

**Context.** Alternatives: one bot per person (a BotFather token each, N deployments, every release
repeated N times), or one bot for everyone. Some organizations may later ask for a dedicated deployment
(REQ-033).
**Decision.** One bot token and one deployment serve every workspace. The Telegram user ID identifies the
person, and their membership gives the workspace. That lookup lives in one function shared by the bot
`authorize` and the web `require_web_user`, never in the handlers. A dedicated deployment is the same
image with its own env (bot token, `DATABASE_URL`, API keys) and a single workspace. There is no
per-deployment code.
**Consequences.** Operating and releasing stay at one unit. White-labelling (an org's own bot name) means
a dedicated deployment. Serving several bot tokens from one process is possible later but not planned.
Migrations and releases must also be rolled out to every dedicated deployment.

### ADR-015 — Usage ledger table, with quotas checked before every paid call
- Status: accepted
- Date: 2026-10-28
- Related: REQ-031, REQ-032

**Context.** The platform owner pays for Anthropic, Whisper, Proxycurl and Tavily for every workspace and
needs per-workspace metering and quotas. Provider dashboards cannot split costs by workspace.
**Decision.** A table `usage_events` (workspace, user, provider, operation, units such as input/output
tokens, seconds or calls, estimated cost in USD, timestamp) gets a row after each paid call, written by
one wrapper around each client. A quota check before each paid call compares the workspace's spend for the
period with its limit (stored on `workspaces`). Prices live in config, not code.
**Consequences.** Costs are estimates based on configured prices, so reconcile them against invoices. One
extra insert per paid call. Usage rows also need RLS (ADR-013). A long agent turn can go a little over the
quota because the check runs per call, not per turn.

### ADR-016 — Events are workspace-scoped conferences; records carry an optional event_id
- Status: accepted
- Date: 2026-10-28
- Related: REQ-034, REQ-035, REQ-037, ADR-011, ADR-013, ADR-017

**Context.** Members create several events per workspace, and records can be assigned to one or left
unassigned (REQ-035). Today `conferences` has one global `is_active` row, and only `meetings` link to a
conference.
**Decision.** Keep the `conferences` table as events, scoped by `workspace_id`. Add a nullable
`event_id` foreign key to people, companies, interactions, meetings, notes, tasks and opportunities, with
`ON DELETE SET NULL`. A record belongs to at most one event (Eze, 2026-10-29), so no join table.
Conversation messages get no `event_id`: chats are not linked to events. The global `is_active` flag goes
away; ADR-017 replaces it.
**Consequences.** One nullable column per table, so filtering and bulk reassignment (REQ-038) are simple
updates. A contact met at two conferences keeps one event; the other lives in its interactions' events.
`context_builder.py`, the web "activate conference" action and `seed_conference.py` all depend on
`is_active` and must change with it.

### ADR-017 — Event status computed from dates; attendance in an event_attendees table
- Status: accepted
- Date: 2026-10-29
- Related: REQ-035, REQ-037, ADR-009, ADR-013, ADR-016

**Context.** Events are upcoming, ongoing or finished, and an ongoing event becomes a user's default only
once they confirm they are attending (REQ-037). Alternatives rejected: a stored status column moved by a
daily job (drifts whenever the job misses a run, and needs a job just to finish events), and one active
event per workspace (cannot express one member attending while another does not).
**Decision.** `conferences` gets a `timezone` (defaulting to `TIMEZONE`). The status is computed from
`start_date`, `end_date` and that timezone whenever it is needed, never stored. A table `event_attendees`
(workspace, event, user, `attending` yes/no, answered at; unique per event and user) holds the answers.
A scheduler job (ADR-009) finds events starting today in their timezone and asks every member who has not
answered, with Yes/No inline buttons. A user's default event is the ongoing event they attend; with more
than one, the agent asks; with none, records stay unassigned. The context builder puts the default event
in the system prompt, and the create tools fill `event_id` from it unless the user named another event.
**Consequences.** No status can drift, and "finished" needs no job. The bot needs its first
`CallbackQueryHandler`, which must call `authorize` like every other handler. The question and its reminder
cost no paid API calls. Users who miss the question need a command and a web toggle to answer later.

## Template

```markdown
### ADR-NNN — Short title
- Status: proposed | accepted | superseded
- Date: YYYY-MM-DD
- Supersedes: ADR-NNN        (only when this replaces an older decision)
- Superseded by: ADR-NNN     (only when status is superseded)
- Related: REQ-NNN, ADR-NNN

**Context.** What forces or problem led to this.
**Decision.** What we do.
**Consequences.** What gets easier, what gets harder, what to watch for.
```
