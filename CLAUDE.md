# CLAUDE.md — AI Networking Assistant (Conference Bot)

## Project Overview

A mobile-first AI networking assistant for conference use, accessible via Telegram (MVP) and optionally WhatsApp. The system captures contacts and interactions via text or voice, enriches them with LinkedIn/company data, and generates personalized follow-ups.

Single-user, single-conference focus for MVP. Built by one senior Python developer.

> **Where this file is out of date.** Everything from "Project Structure" down is the original build spec.
> The code has moved on: access is a `bot_users` allowlist with owners (not one `TELEGRAM_ALLOWED_USER_ID`),
> there is a browser UI in `app/web/`, badge photos are read, and the default model is set by
> `ANTHROPIC_MODEL` (Haiku 4.5 today). The sections between here and "Project Structure", plus `docs/`, are
> authoritative. If the spec, README, docs and code disagree, tell Eze.

## Commands

Everything runs either in Docker (`docker compose ...`, see README) or locally with `uv`. Locally, prefix
Python commands with `PYTHONDONTWRITEBYTECODE=1`: `__pycache__/` folders created by the container are
owned by root.

| What | Command |
|---|---|
| Import smoke test (catches syntax and import errors in the whole app) | `PYTHONDONTWRITEBYTECODE=1 uv run python -c "import app.api.main"` |
| Lint the files you changed | `uvx ruff check <changed .py files>` |
| Tests, all / one file / one test | `uv run pytest` · `uv run pytest tests/test_agent/test_x.py` · `... ::test_ucNNN_x` |
| Database for local runs | `docker compose up -d db` (Postgres 16 + pgvector on `localhost:5434`) |
| Models and migrations in sync | `docker compose run --rm app alembic check` |
| New migration after a model change | `docker compose run --rm app alembic revision --autogenerate -m "<change>"` |
| Docs consistency | `python3 .claude/hooks/docs_guard.py check` |
| Guard self-test | `python3 .claude/hooks/test_guard.py` |
| Run the stack | `docker compose up` (bot in polling mode, web UI on `http://localhost:8000/`) |

## Development workflow

Eze is the only developer and reviews every PR on GitHub (`ezefernandez94/congress_ai_agent`). Work is
tracked in Linear: project `congress-bot-76da1c024bec`, team `EZE` (issue IDs `EZE-N`); milestones are
phases, issues are tasks. Session loop:
`/start-session` → `/develop <EZE-N | milestone>` (plan, then stop for approval) → `/continue` →
`/commit` (push + PR) → Eze approves → `/post-approve <pr>` → `/end-session`. `/status` any time.
Step-by-step behavior lives in `.claude/commands/`; the rules below always apply.

- **Branches:** `<type>/<EZE-N>-<short-slug>` (feat | fix | chore | refactor | test | docs), from an
  up-to-date `main`. One branch/PR per issue or small group of related issues. Work without a Linear
  issue (`/develop "<description>"`) is allowed: branch `<type>/<short-slug>`, no ID in commits, PR
  title `<type>: ...`, no `Refs`.
- **Plans:** `.claude/plans/<branch, / → ->.md` (gitignored), checkboxes ticked as steps finish. No code
  before Eze approves the plan; nothing outside it without asking.
- **PRs:** into `main`, title `EZE-N: ...`, body uses `Refs EZE-N`, never Closes/Fixes/Resolves/Completes/
  Implements. Merge with **squash** (`gh pr merge <n> --squash`), only in `/post-approve`, never deleting
  branches. Update a branch by merging `main` into it; never rebase a branch with an open PR. There is no
  branch protection and no CI, so the local guardrails are the only ones.
- **Linear is read-only** except in `/post-approve`, after Eze names the issues to mark Done.
- **Commits:** `DURATION="HH:MM" git commit -m '<message>'`, message
  `<type>(<scope>): <EZE-N> <summary> [claude HH:MM]`, optional body, `Co-Authored-By` trailer.
  DURATION = human-developer estimate for the diff; `[claude HH:MM]` = Claude's active time from
  `python3 .claude/hooks/timer.py show` (UserPromptSubmit/Stop hooks; state in `.claude/state/`).
- **Checks** (`/commit`: the parts touched; `/post-approve`: everything): the import smoke test;
  `uvx ruff check` on the changed `.py` files (the repo has older violations, so lint only what you touch
  and fix what you find there); `alembic check` when `app/models/` changed (and commit the migration);
  `uv run pytest` for what changed (full suite in `/post-approve`); `python3 .claude/hooks/docs_guard.py check`.
- **Tests:** pytest with `asyncio_mode = "auto"`, against a real PostgreSQL with pgvector (the
  `conference_bot_test` database in `tests/conftest.py`). Mock only external services: Anthropic, OpenAI
  (Whisper), Telegram, Proxycurl, Tavily. Never call a paid API from a test. Test names follow
  `test_ucNNN_<scenario>` (see "Documentation workflow").
- **Definition of done:** plan steps ticked, acceptance criteria met, checks green, docs updated (REQ/ADR/UC
  per "Documentation workflow"), PR open with test results.
- **Failures:** if a check fails or the commit-msg hook rejects a commit, stop and report. No workarounds.

**Clockify commit-msg hook:** not installed in this repo yet (Eze will add it). DURATION is still mandatory
on every commit and merge commit, and the guard enforces it. Once the hook exists (`.git/hooks/commit-msg`,
not versioned), never edit it, and never read or edit `~/.clockify_env`.

**Guardrails** are enforced by `.claude/hooks/guard.py` (PreToolUse; self-test `python3
.claude/hooks/test_guard.py`) plus deny/ask rules in `.claude/settings.json`. Denied: commit on main,
commit without DURATION, `--no-verify`/`-n`, `core.hooksPath`, any force push, push to main, `add -A`/`.`,
`commit -a`, staged secrets, approving PRs, merging outside `/post-approve`, merge without `--squash` or
with `--delete-branch`, closing keywords in PRs, a PR title without the branch's `EZE-N` (or without
`<type>:` when there is no issue), edits to git hooks or `~/.clockify_env`, reading or editing `.env`,
Linear status changes outside `/post-approve`. Ask first: `gh pr merge`, branch deletion, `reset --hard`,
`clean -f`, `rm -rf`, rebase, `--amend`, other Linear writes, edits to the guard files. Scope and "stop on
failure" are rules, not enforced.

## Invariants worth preserving

Reconstructed from the code on 2026-10-28; tell Eze if one looks wrong rather than silently breaking it.

- **Access is the `bot_users` table, nothing else** (ADR-006). Every Telegram handler calls
  `app/bot/auth.authorize` first (only `/whoami` is open). Every web route depends on `require_web_user`
  except `/health`, `/webhook/{secret}`, `/login`, `/auth/telegram`, `/logout` and `/static`. Both fail
  closed on a database error.
- `TELEGRAM_ALLOWED_USER_IDS` only **adds** owners at startup; removing an ID from the env revokes nothing.
  Only owners add or remove users; an owner cannot be removed with `/removeuser`, and nobody can remove
  themselves.
- The web development login bypass runs only when `APP_ENV != production` (ADR-008). Never widen it.
- Agent tools return a dict with `success` (and `error` on failure). `ToolExecutor.execute` commits after
  each successful tool and rolls back a failed one. Repositories `flush`, they never `commit`.
- The agent loop is bounded (`ConferenceAgent.MAX_TOOL_ROUNDS`).
- When a name matches several contacts, return all matches to the agent and let it ask; never silently
  pick one (REQ-006; several tools still break this today, see that entry).
- Proxycurl (paid, about $0.10 per call) runs only when the user asks for enrichment or gives a LinkedIn URL;
  never on contact creation. Follow-up drafts are never sent automatically.
- Conversation history is keyed by Telegram user ID and shared by Telegram and the web chat; the agent sees
  the last 20 messages.
- Logs never contain the bot token or the webhook secret (`_redact` in `app/api/main.py`).
- The web UI has no build step and loads nothing from a CDN: Jinja2 templates plus a vendored
  `htmx.min.js` (ADR-007).
- Every model change ships with its Alembic migration in `alembic/versions/`.
- Telegram replies use `parse_mode="Markdown"`, so escape `_` and `*` in literal text (for example
  `/digest\_on`).

## Documentation workflow (`docs/`)

Three files in `docs/` are the project's written memory. Read them **on demand**; they are deliberately not
imported here, so they do not cost context in every session.

| File | Holds | IDs |
|---|---|---|
| `docs/requirements.md` | What the product must do, plus constraints | `REQ-NNN` |
| `docs/architecture.md` | Decisions and the reasons for them (ADR style) | `ADR-NNN` |
| `docs/use-cases.md` | What a person can do, step by step; the source for tests | `UC-NNN` |

Rules:

1. **New feature or behavior change: run `/new-requirement` before writing code.** It compares the request with
   `docs/requirements.md`. If it conflicts with, or duplicates, an `active` or `planned` requirement, **stop,
   tell the user what conflicts (IDs and a one-line quote of each) and wait for their decision.** Never resolve
   a conflict silently.
2. If the user overrides an old requirement, mark it `superseded` and link both entries. Never delete entries.
3. **Choosing a library, data model, external API or pattern, or reversing an earlier choice: run
   `/record-decision`.** A new dependency needs the user's approval and an ADR before it is installed. Only
   the user marks a decision `accepted`.
4. **User-visible behavior added, changed or removed: run `/update-use-cases`.** Tests come from use cases and are
   named `test_ucNNN_<scenario>`.
5. **Before reporting a task as done**, update the docs, or say in your final message why nothing needed to
   change. A Stop hook checks this and validates the docs.
6. Entries marked `backfill` or `claude-suggested` are not confirmed by the user. When one matters for the task,
   ask instead of assuming.

## Conventions

- Code, comments, docs and user-facing bot/web strings are in English. Commit subjects follow the commit
  format above (older commits are partly in Spanish; don't copy that).
- Comments explain *why* (see `ToolExecutor.execute`, `require_web_user`); match that density.
- structlog events are `snake_case` names with keyword fields: `logger.info("seed_users_ready", count=n)`.
- Line length 100 (`[tool.ruff]` in `pyproject.toml`).
- Never commit the data dumps in the repo root (`*.csv`, `*.sql`, `*.odt`, logs): they can hold real
  contacts.

---

## Project Structure

```
conference-bot/
│
├── CLAUDE.md                        # This file
├── README.md
├── .env.example
├── .env                             # Never commit
├── .gitignore
├── pyproject.toml                   # uv project config
├── uv.lock
│
├── alembic/                         # DB migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/                        # Config and infrastructure
│   │   ├── __init__.py
│   │   ├── config.py                # Settings via pydantic-settings
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   └── logging.py
│   │
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                  # Base class, TimestampMixin
│   │   ├── person.py
│   │   ├── company.py
│   │   ├── meeting.py
│   │   ├── interaction.py
│   │   ├── note.py
│   │   ├── task.py
│   │   ├── opportunity.py
│   │   └── conference.py
│   │
│   ├── schemas/                     # Pydantic v2 schemas (API + internal)
│   │   ├── __init__.py
│   │   ├── person.py
│   │   ├── company.py
│   │   ├── meeting.py
│   │   ├── interaction.py
│   │   ├── task.py
│   │   ├── opportunity.py
│   │   └── conference.py
│   │
│   ├── repositories/                # DB access layer (no raw SQL in business logic)
│   │   ├── __init__.py
│   │   ├── base.py                  # Generic CRUD base
│   │   ├── person_repo.py
│   │   ├── company_repo.py
│   │   ├── interaction_repo.py
│   │   ├── task_repo.py
│   │   └── opportunity_repo.py
│   │
│   ├── services/                    # Business logic layer
│   │   ├── __init__.py
│   │   ├── enrichment.py            # LinkedIn + company enrichment
│   │   ├── transcription.py         # Whisper voice → text
│   │   ├── digest.py                # Daily digest generation
│   │   ├── followup.py              # Follow-up email drafting
│   │   └── search.py                # Semantic + structured search
│   │
│   ├── agent/                       # LLM orchestration layer
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # Main agent loop
│   │   ├── prompts.py               # All system prompts
│   │   ├── tools.py                 # Tool definitions (Anthropic tool-use format)
│   │   └── context_builder.py       # Dynamic system prompt assembler
│   │
│   ├── bot/                         # Telegram interface
│   │   ├── __init__.py
│   │   ├── handlers.py              # Message + voice handlers
│   │   ├── formatter.py             # Response formatting for Telegram
│   │   └── router.py                # Command routing
│   │
│   ├── api/                         # FastAPI webhook receiver
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── routes/
│   │   │   ├── webhook.py           # Telegram webhook endpoint
│   │   │   └── health.py
│   │   └── middleware.py
│   │
│   └── jobs/                        # Scheduled tasks
│       ├── __init__.py
│       ├── scheduler.py             # APScheduler setup
│       └── daily_digest.py          # 7:30 AM digest job
│
├── tests/
│   ├── conftest.py
│   ├── test_agent/
│   ├── test_services/
│   └── test_repositories/
│
└── scripts/
    ├── seed_conference.py           # Load conference + target contacts
    ├── batch_enrich.py              # Pre-conference bulk enrichment
    └── export_crm.py                # Post-conference CRM export
```

---

## Technology Stack

### Runtime and Package Management
- **Python 3.11+**
- **uv** for dependency management (faster than pip, replaces virtualenv)

### Web Framework
- **FastAPI** — webhook receiver, health endpoints
- **uvicorn** — ASGI server

### Database
- **PostgreSQL** — primary datastore (use Supabase for free hosted tier)
- **pgvector** — semantic search extension (enable on Supabase with one click)
- **SQLAlchemy 2.x** — ORM (use async where possible)
- **Alembic** — migrations

### AI / LLM
- **Anthropic SDK** (`anthropic`) — Claude claude-sonnet-4 as orchestrator, tool-use mode
- **OpenAI SDK** (`openai`) — Whisper API for voice transcription only

### Bot Interface
- **python-telegram-bot** v21+ — Telegram bot SDK

### Enrichment
- **httpx** — async HTTP for enrichment API calls
- **Proxycurl** — LinkedIn profile data (REST API, pay-per-call)
- **Tavily** — web search and company news (`tavily-python`)

### Scheduling
- **APScheduler** — daily digest cron job

### Utilities
- **pydantic-settings** — environment config
- **pydantic v2** — data validation
- **structlog** — structured logging
- **tenacity** — retry logic for external API calls

---

## Environment Variables

```bash
# .env.example

# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/conference_bot

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_ID=          # Single user ID — security gate

# Anthropic
ANTHROPIC_API_KEY=

# OpenAI (Whisper only)
OPENAI_API_KEY=

# Enrichment
PROXYCURL_API_KEY=
TAVILY_API_KEY=

# App
APP_ENV=development                 # development | production
WEBHOOK_SECRET=                     # Random string for webhook validation
BASE_URL=https://your-app.railway.app

# Optional
APOLLO_API_KEY=                     # Alternative to Proxycurl for email finding
TIMEZONE=America/Los_Angeles        # Conference timezone
DIGEST_HOUR=7
DIGEST_MINUTE=30
```

---

## Data Models

### Enums (define in `app/models/base.py`)

```python
class ContactType(str, Enum):
    investor = "investor"
    customer = "customer"
    partner = "partner"
    founder = "founder"
    speaker = "speaker"
    other = "other"

class PriorityTier(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    unranked = "unranked"

class InterestLevel(str, Enum):
    hot = "hot"
    warm = "warm"
    cold = "cold"
    unknown = "unknown"

class FollowUpStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    not_needed = "not_needed"

class TaskType(str, Enum):
    send_email = "send_email"
    send_deck = "send_deck"
    schedule_meeting = "schedule_meeting"
    linkedin_connect = "linkedin_connect"
    research = "research"
    follow_up = "follow_up"
    other = "other"

class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class TaskPriority(str, Enum):
    urgent = "urgent"
    high = "high"
    medium = "medium"
    low = "low"

class Sentiment(str, Enum):
    very_positive = "very_positive"
    positive = "positive"
    neutral = "neutral"
    negative = "negative"

class OpportunityType(str, Enum):
    investment = "investment"
    customer = "customer"
    partnership = "partnership"
    co_founder = "co_founder"
    advisor = "advisor"
    press = "press"

class OpportunityStage(str, Enum):
    identified = "identified"
    contacted = "contacted"
    interested = "interested"
    proposal_sent = "proposal_sent"
    negotiating = "negotiating"
    closed_won = "closed_won"
    closed_lost = "closed_lost"
    nurture = "nurture"

class MeetingType(str, Enum):
    pitch = "pitch"
    intro = "intro"
    casual = "casual"
    panel = "panel"
    coffee = "coffee"
    scheduled = "scheduled"
    spontaneous = "spontaneous"

class InteractionType(str, Enum):
    conversation = "conversation"
    pitch = "pitch"
    email = "email"
    linkedin_message = "linkedin_message"
    introduction = "introduction"
    follow_up = "follow_up"

class NoteSource(str, Enum):
    voice = "voice"
    text = "text"
```

### Person (`app/models/person.py`)

```python
class Person(Base):
    __tablename__ = "people"

    id: uuid (PK)
    full_name: str (not null)
    role: str (nullable)
    company_id: uuid (FK → companies, nullable)
    linkedin_url: str (nullable, unique)
    email: str (nullable)
    phone: str (nullable)
    twitter_handle: str (nullable)

    contact_type: ContactType (default: other)
    priority_tier: PriorityTier (default: unranked)
    interest_level: InterestLevel (default: unknown)
    warmth_score: float (default: 0.5)

    how_met: str (nullable)
    first_interaction_date: datetime (nullable)
    last_interaction_date: datetime (nullable)
    notes: text (nullable)

    follow_up_status: FollowUpStatus (default: pending)
    next_action: str (nullable)
    next_action_due: date (nullable)

    # Enrichment
    linkedin_summary: text (nullable)
    bio_snapshot: text (nullable)
    enriched_at: datetime (nullable)
    enrichment_source: str (nullable)    # "proxycurl" | "manual" | "pdf"

    # pgvector embedding of bio+notes for semantic search
    embedding: Vector(1536) (nullable)

    # Relationships
    company: relationship → Company
    interactions: relationship → Interaction[]
    tasks: relationship → Task[]
    opportunities: relationship → Opportunity[]
    meetings: relationship → Meeting[] (via association table)
```

### Company (`app/models/company.py`)

```python
class Company(Base):
    __tablename__ = "companies"

    id: uuid (PK)
    name: str (not null)
    website: str (nullable)
    linkedin_url: str (nullable)
    crunchbase_url: str (nullable)

    industry: str (nullable)
    stage: str (nullable)
    funding_total: int (nullable)           # USD
    last_funding_date: date (nullable)
    investor_list: ARRAY(str) (nullable)

    relevance_tags: ARRAY(str) (nullable)   # ["potential_customer", "investor"]
    strategic_notes: text (nullable)

    company_summary: text (nullable)
    recent_news: JSONB (nullable)           # [{title, url, date}]
    enriched_at: datetime (nullable)

    embedding: Vector(1536) (nullable)

    # Relationships
    people: relationship → Person[]
```

### Meeting (`app/models/meeting.py`)

```python
class Meeting(Base):
    __tablename__ = "meetings"

    id: uuid (PK)
    title: str (not null)
    scheduled_at: datetime (nullable)
    duration_minutes: int (default: 30)
    location: str (nullable)
    meeting_type: MeetingType (default: spontaneous)
    conference_id: uuid (FK → conferences, nullable)

    prep_brief: text (nullable)
    talking_points: ARRAY(str) (nullable)
    questions_to_ask: ARRAY(str) (nullable)

    outcome_summary: text (nullable)
    sentiment: Sentiment (nullable)
    next_steps: ARRAY(str) (nullable)
    followed_up: bool (default: False)
    followed_up_at: datetime (nullable)

    # M2M with Person via meeting_participants
    participants: relationship → Person[]
```

### Interaction (`app/models/interaction.py`)

```python
class Interaction(Base):
    __tablename__ = "interactions"

    id: uuid (PK)
    person_id: uuid (FK → people, not null)
    meeting_id: uuid (FK → meetings, nullable)
    interaction_type: InteractionType (default: conversation)
    occurred_at: datetime (not null, default: now)

    raw_note: text (nullable)
    processed_summary: text (nullable)
    topics_discussed: ARRAY(str) (nullable)
    commitments_made: JSONB (nullable)    # [{who: "me"|"them", what: str}]
    sentiment: Sentiment (nullable)

    source: NoteSource (default: text)
    transcription: text (nullable)        # original Whisper output if voice

    embedding: Vector(1536) (nullable)
```

### Note (`app/models/note.py`)

```python
class Note(Base):
    __tablename__ = "notes"

    id: uuid (PK)
    person_id: uuid (FK, nullable)
    meeting_id: uuid (FK, nullable)
    raw_content: text (not null)
    content_type: NoteSource (default: text)
    transcription: text (nullable)
    processed: bool (default: False)
    created_at: datetime (default: now)

    # extracted_actions created as Task records with note_id FK
```

### Task (`app/models/task.py`)

```python
class Task(Base):
    __tablename__ = "tasks"

    id: uuid (PK)
    title: str (not null)
    description: text (nullable)
    task_type: TaskType (default: other)

    related_person_id: uuid (FK, nullable)
    related_company_id: uuid (FK, nullable)
    related_meeting_id: uuid (FK, nullable)
    note_id: uuid (FK → notes, nullable)

    priority: TaskPriority (default: medium)
    status: TaskStatus (default: pending)
    due_date: date (nullable)
    completed_at: datetime (nullable)

    created_by: str (default: "agent")    # "agent" | "user"
    draft_content: text (nullable)        # pre-generated email draft
```

### Opportunity (`app/models/opportunity.py`)

```python
class Opportunity(Base):
    __tablename__ = "opportunities"

    id: uuid (PK)
    title: str (not null)
    opportunity_type: OpportunityType (not null)

    person_id: uuid (FK, nullable)
    company_id: uuid (FK, nullable)

    stage: OpportunityStage (default: identified)
    estimated_value: str (nullable)
    probability: float (default: 0.5)
    expected_close_date: date (nullable)

    notes: text (nullable)
    pitch_feedback: ARRAY(str) (nullable)
    objections_raised: ARRAY(str) (nullable)
    next_step: str (nullable)
    next_step_due: date (nullable)
```

### Conference (`app/models/conference.py`)

```python
class Conference(Base):
    __tablename__ = "conferences"

    id: uuid (PK)
    name: str (not null)
    location: str (nullable)
    start_date: date (nullable)
    end_date: date (nullable)

    goals: ARRAY(str) (nullable)
    target_contact_types: ARRAY(str) (nullable)
    schedule_imported: bool (default: False)

    summary_generated: bool (default: False)
    post_conference_report: text (nullable)

    # Active conference flag — agent always uses the active one
    is_active: bool (default: True)
```

---

## Agent Architecture

### Tool Definitions (`app/agent/tools.py`)

Define all tools in Anthropic tool-use format. The orchestrator calls these; each maps to a service or repository function.

```python
TOOLS = [
    # --- CONTACT TOOLS ---
    {
        "name": "create_contact",
        "description": "Create a new contact record. Call this when the user mentions meeting someone new.",
        "input_schema": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string"},
                "role": {"type": "string"},
                "company_name": {"type": "string"},
                "contact_type": {"type": "string", "enum": ["investor", "customer", "partner", "founder", "speaker", "other"]},
                "interest_level": {"type": "string", "enum": ["hot", "warm", "cold", "unknown"]},
                "how_met": {"type": "string"},
                "notes": {"type": "string"},
                "linkedin_url": {"type": "string"},
                "email": {"type": "string"}
            },
            "required": ["full_name"]
        }
    },
    {
        "name": "log_interaction",
        "description": "Log an interaction with an existing contact. Use after a meeting or conversation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
                "interaction_type": {"type": "string"},
                "summary": {"type": "string"},
                "sentiment": {"type": "string", "enum": ["very_positive", "positive", "neutral", "negative"]},
                "topics_discussed": {"type": "array", "items": {"type": "string"}},
                "commitments_made": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "who": {"type": "string", "enum": ["me", "them"]},
                            "what": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["person_name", "summary"]
        }
    },
    {
        "name": "create_task",
        "description": "Create an action item or follow-up task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "task_type": {"type": "string", "enum": ["send_email", "send_deck", "schedule_meeting", "linkedin_connect", "research", "follow_up", "other"]},
                "person_name": {"type": "string"},
                "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low"]},
                "due_date": {"type": "string", "description": "ISO date string YYYY-MM-DD"},
                "draft_content": {"type": "string", "description": "Pre-written draft if applicable"}
            },
            "required": ["title", "task_type"]
        }
    },
    {
        "name": "search_contacts",
        "description": "Search for contacts by name, company, or description. Use when user refers to someone by partial name or context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "contact_type": {"type": "string"},
                "limit": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_contact_brief",
        "description": "Get full context on a contact: bio, enrichment data, interaction history, open tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"}
            },
            "required": ["person_name"]
        }
    },
    {
        "name": "get_pending_tasks",
        "description": "Get all pending tasks, optionally filtered by priority or person.",
        "input_schema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string"},
                "person_name": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            }
        }
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "task_title": {"type": "string", "description": "Can be used instead of task_id for fuzzy match"}
            }
        }
    },

    # --- ENRICHMENT TOOLS ---
    {
        "name": "enrich_contact",
        "description": "Fetch LinkedIn and company data for a contact. Call when user provides a LinkedIn URL or asks for background on someone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
                "linkedin_url": {"type": "string"},
                "company_name": {"type": "string"}
            },
            "required": ["person_name"]
        }
    },
    {
        "name": "search_web",
        "description": "Search the web for news or information about a person or company.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "days_back": {"type": "integer", "default": 90}
            },
            "required": ["query"]
        }
    },

    # --- DRAFT TOOLS ---
    {
        "name": "draft_followup",
        "description": "Generate a personalized follow-up email draft for a contact.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
                "tone": {"type": "string", "enum": ["warm", "professional", "casual"], "default": "warm"},
                "key_points": {"type": "array", "items": {"type": "string"}, "description": "Specific things to mention"}
            },
            "required": ["person_name"]
        }
    },
    {
        "name": "generate_meeting_prep",
        "description": "Generate a pre-meeting brief with talking points and questions for an upcoming meeting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
                "meeting_context": {"type": "string", "description": "Type of meeting: pitch, intro, coffee, etc."}
            },
            "required": ["person_name"]
        }
    },

    # --- DIGEST / SUMMARY TOOLS ---
    {
        "name": "get_daily_digest",
        "description": "Generate the full daily digest: pending tasks, today's meetings, priority contacts to approach.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_conference_summary",
        "description": "Generate a summary of all contacts, opportunities, and follow-ups from the conference.",
        "input_schema": {"type": "object", "properties": {}}
    }
]
```

### Orchestrator (`app/agent/orchestrator.py`)

```python
# Core agent loop — simplified pseudocode for implementation guide

class ConferenceAgent:
    def __init__(self, db_session, conference_id):
        self.client = anthropic.AsyncAnthropic()
        self.db = db_session
        self.conference_id = conference_id
        self.tool_executor = ToolExecutor(db_session)

    async def process_message(
        self,
        user_message: str,
        message_history: list[dict]
    ) -> str:
        """
        Main entry point. Accepts a text message (already transcribed if voice).
        Returns a formatted response string.
        """
        system_prompt = await self.build_system_prompt()

        messages = message_history + [{"role": "user", "content": user_message}]

        # Agentic loop — keep going until no more tool calls
        while True:
            response = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=2048,
                system=system_prompt,
                tools=TOOLS,
                messages=messages
            )

            # Append assistant response to history
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Extract text response
                return self._extract_text(response)

            if response.stop_reason == "tool_use":
                # Execute all tool calls in this response
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self.tool_executor.execute(
                            block.name,
                            block.input
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                # Add tool results to history and loop
                messages.append({"role": "user", "content": tool_results})
                continue

            break  # unexpected stop_reason

        return "Sorry, something went wrong. Please try again."
```

### Context Builder (`app/agent/context_builder.py`)

```python
# Builds dynamic system prompt with fresh conference state

async def build_system_prompt(db_session, conference_id: str) -> str:
    conference = await get_active_conference(db_session)
    pending_tasks = await get_pending_tasks(db_session, limit=5)
    todays_meetings = await get_todays_meetings(db_session)
    recent_contacts = await get_recent_contacts(db_session, hours=24)

    return f"""
You are a personal AI networking assistant helping at a startup conference.

## Identity
You are a focused, efficient assistant. Responses should be brief and mobile-friendly.
Use short paragraphs. Use bullet points only when listing 3+ items.
Use emojis sparingly — only where they genuinely aid scannability (✅ for completed, ⚠️ for urgent).

## Conference Context
Name: {conference.name}
Location: {conference.location}
Dates: {conference.start_date} to {conference.end_date}
Goals: {chr(10).join(f"- {g}" for g in conference.goals)}

## Current State
Today's date: {date.today().isoformat()}
Pending tasks: {len(pending_tasks)} open
Today's meetings: {len(todays_meetings)} scheduled

## Recent Activity (last 24h)
{format_recent_contacts(recent_contacts)}

## Behavior Rules
1. When the user mentions meeting someone, ALWAYS call create_contact — never just acknowledge.
2. When commitments are mentioned ("I'll send them the deck", "they'll connect me with X"), ALWAYS call create_task.
3. When the user asks to be "briefed" on someone, call get_contact_brief first, then generate_meeting_prep.
4. If you're not sure which person the user means, call search_contacts and ask for disambiguation — never guess.
5. After creating records, give a brief confirmation with what was saved and what tasks were created.
6. Always confirm task due dates. If none given, suggest "tomorrow" for hot contacts, "3 days" for warm.
7. Never fabricate details about contacts. If you don't have data, say so and offer to enrich.
8. Draft follow-ups using only information present in the contact's record. Flag any gaps.

## Response Format for Common Actions
Contact capture: "[Name] saved ✅ — [company, role]. [N] task(s) created: [task list]. Anything to add?"
Brief: Lead with 3-5 bullets, end with "Ready to talk to them?"
Follow-up draft: Present the draft, then ask "Want me to adjust the tone or add anything?"
Task list: Group by priority. Urgent first. Max 7 items before truncating with "...and N more".
""".strip()
```

---

## Services

### Transcription Service (`app/services/transcription.py`)

```python
# Dependencies: openai SDK, httpx for downloading audio

async def transcribe_voice_note(audio_url: str) -> str:
    """
    Download audio from Telegram URL, transcribe via Whisper.
    Returns transcribed text.
    """
    # 1. Download audio file (Telegram provides a file URL)
    # 2. POST to openai.audio.transcriptions.create(model="whisper-1")
    # 3. Return .text field
    # Handle: file size limit (25MB Whisper limit), format conversion if needed
    # Telegram sends voice notes as .ogg — Whisper accepts this natively
```

### Enrichment Service (`app/services/enrichment.py`)

```python
# Dependencies: httpx, tenacity for retries

async def enrich_person_proxycurl(linkedin_url: str) -> dict:
    """
    Fetches structured LinkedIn profile data via Proxycurl.
    Returns dict with: full_name, headline, summary, experiences, education.
    Cost: ~$0.10/call. Only call once per profile — cache in DB.
    """
    # GET https://nubela.co/proxycurl/api/v2/linkedin
    # params: url=linkedin_url
    # headers: Authorization: Bearer {PROXYCURL_API_KEY}
    # Map response to our Person schema fields
    # Store raw response in person.enrichment_source metadata

async def enrich_company_tavily(company_name: str, website: str) -> dict:
    """
    Search for company info via Tavily. Cheaper than Proxycurl for companies.
    Returns: summary, recent_news[]
    """
    # Use tavily_client.search(f"{company_name} startup funding news", days=90)
    # Pass results to Claude to extract: one-liner summary, funding info, news items
    # Store as company.company_summary and company.recent_news

async def generate_intel_brief(person_id: str, db_session) -> str:
    """
    Assembles a pre-meeting brief from stored enrichment data.
    Does NOT call external APIs — uses only cached data.
    Calls Claude to synthesize into a readable brief.
    """
    # 1. Fetch person + company from DB
    # 2. Fetch last 3 interactions
    # 3. Pass all to Claude with prompt: "Generate a 5-bullet pre-meeting brief..."
    # 4. Return formatted brief
```

### Follow-up Service (`app/services/followup.py`)

```python
async def draft_followup_email(person_id: str, tone: str, key_points: list, db_session) -> str:
    """
    Generates a personalized follow-up email using stored context.
    Never makes external API calls — all context from DB.
    """
    # 1. Fetch person, company, interactions, tasks
    # 2. Build context string
    # 3. Call Claude with prompt:
    #    "Write a {tone} follow-up email from [user] to [person].
    #     Context: [context]. Key points to include: [key_points].
    #     Length: 4-6 sentences. No generic openers.
    #     Reference a specific detail from their conversation."
    # 4. Return draft
    # Note: user must explicitly send it — never auto-send
```

### Digest Service (`app/services/digest.py`)

```python
async def generate_daily_digest(db_session, conference_id: str) -> str:
    """
    Generates morning briefing. Called by scheduler at 7:30 AM conference timezone.
    """
    # 1. Pending tasks (grouped by priority)
    # 2. Today's scheduled meetings (with 1-line prep each)
    # 3. High-priority contacts not yet approached
    # 4. Follow-ups overdue from yesterday
    # 5. One recommended action: "Most important thing to do today: ..."
    # Format for Telegram (Markdown, no HTML)
```

---

## Bot Handlers (`app/bot/handlers.py`)

```python
# Key handler patterns for python-telegram-bot v21

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main text handler — routes everything through the agent."""
    user_id = update.effective_user.id
    if user_id != settings.TELEGRAM_ALLOWED_USER_ID:
        return  # Security gate — single user only

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Send "thinking" acknowledgment for non-trivial requests
    if is_complex_request(update.message.text):
        await update.message.reply_text("⏳ On it...")

    # Retrieve conversation history from DB (last 10 turns)
    history = await get_conversation_history(user_id, limit=10)

    # Run agent
    response = await agent.process_message(
        user_message=update.message.text,
        message_history=history
    )

    # Save to history
    await save_message_to_history(user_id, "user", update.message.text)
    await save_message_to_history(user_id, "assistant", response)

    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Voice note handler — transcribe then route to agent."""
    user_id = update.effective_user.id
    if user_id != settings.TELEGRAM_ALLOWED_USER_ID:
        return

    # Immediate acknowledgment — transcription takes a few seconds
    await update.message.reply_text("🎙 Transcribing...")

    # Download voice file
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    audio_bytes = await voice_file.download_as_bytearray()

    # Transcribe
    transcript = await transcription_service.transcribe(audio_bytes)

    # Process as text message with "[Voice note]: " prefix
    user_message = f"[Voice note]: {transcript}"

    history = await get_conversation_history(user_id, limit=10)
    response = await agent.process_message(user_message, history)

    # Echo transcript so user can verify
    await update.message.reply_text(f"_Heard: {transcript}_", parse_mode="Markdown")
    await update.message.reply_text(response, parse_mode="Markdown")


# Slash command handlers
# /start — welcome + setup
# /digest — trigger daily digest on demand
# /tasks — show all pending tasks
# /contacts — show recent contacts
# /help — command reference
```

---

## Conversation History

Conversation history for the agent loop is stored in a `conversation_messages` table:

```python
class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: uuid (PK)
    user_id: str          # Telegram user ID
    role: str             # "user" | "assistant"
    content: text
    created_at: datetime

# Retrieve with: SELECT * FROM conversation_messages
#   WHERE user_id = ? ORDER BY created_at DESC LIMIT 20
# Pass to agent as: [{"role": m.role, "content": m.content} for m in reversed(messages)]
```

---

## Scheduled Jobs (`app/jobs/daily_digest.py`)

```python
# APScheduler configuration
# Run digest job every day at 7:30 AM in conference timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)

scheduler.add_job(
    func=send_daily_digest,
    trigger=CronTrigger(hour=settings.DIGEST_HOUR, minute=settings.DIGEST_MINUTE),
    id="daily_digest",
    replace_existing=True
)

async def send_daily_digest():
    async with get_db_session() as db:
        digest_text = await digest_service.generate_daily_digest(db)
        await telegram_bot.send_message(
            chat_id=settings.TELEGRAM_ALLOWED_USER_ID,
            text=digest_text,
            parse_mode="Markdown"
        )
```

---

## API Routes (`app/api/routes/webhook.py`)

```python
# FastAPI webhook endpoint for Telegram updates

@router.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403)

    update_data = await request.json()
    update = Update.de_json(update_data, bot_application.bot)
    await bot_application.process_update(update)

    return {"ok": True}

# Register webhook on startup:
# POST https://api.telegram.org/bot{TOKEN}/setWebhook
#   url: https://your-app.railway.app/webhook/{WEBHOOK_SECRET}
```

---

## Scripts

### `scripts/seed_conference.py`

```python
# Usage: uv run python scripts/seed_conference.py
# Creates the Conference record and sets initial goals
# Prompts for: conference name, dates, location, goals (one per line)
# Creates active conference in DB
```

### `scripts/batch_enrich.py`

```python
# Usage: uv run python scripts/batch_enrich.py --input attendees.csv
# Input CSV: full_name, company, linkedin_url, contact_type
# Runs enrichment for each row (Proxycurl + Tavily)
# Rate limits: 1 request/second to respect API limits
# Saves all to DB with priority scoring
# Outputs: enriched_contacts_summary.txt
```

### `scripts/export_crm.py`

```python
# Usage: uv run python scripts/export_crm.py --format airtable|notion|csv
# Exports all contacts, interactions, tasks, opportunities
# CSV export: one file per entity type
# Airtable export: via Airtable API (requires AIRTABLE_API_KEY + BASE_ID in .env)
# Notion export: via Notion API (requires NOTION_API_KEY + DATABASE_IDs in .env)
```

---

## pyproject.toml

```toml
[project]
name = "conference-bot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pgvector>=0.3.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "anthropic>=0.40.0",
    "openai>=1.50.0",
    "python-telegram-bot>=21.0.0",
    "httpx>=0.27.0",
    "tavily-python>=0.3.0",
    "apscheduler>=3.10.0",
    "structlog>=24.0.0",
    "tenacity>=9.0.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-mock>=3.14.0",
    "httpx>=0.27.0",  # for TestClient
    "factory-boy>=3.3.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
```

---

## Deployment (Railway)

```bash
# railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.api.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 10
restartPolicyType = "on_failure"
```

```bash
# Procfile (alternative)
web: uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
worker: python -m app.jobs.scheduler  # if running scheduler as separate process
```

For Railway: connect GitHub repo → add PostgreSQL plugin → set all env vars → deploy.
Enable pgvector on Supabase: `CREATE EXTENSION IF NOT EXISTS vector;`

---

## Implementation Order

Build in this exact sequence — each phase is independently testable:

**Phase 1: Foundation (Day 1)**
1. `uv init`, install dependencies, set up project structure
2. `app/core/config.py` — load all env vars
3. `app/core/database.py` — async SQLAlchemy engine
4. All models + Alembic migration
5. All repositories (generic CRUD base + specific ones)
6. `pytest` with `conftest.py` — confirm DB read/write works

**Phase 2: Bot Shell (Day 1-2)**
1. FastAPI app with `/health` and `/webhook/{secret}` routes
2. Telegram bot application wired to webhook
3. Text and voice message handlers (stub responses for now)
4. Security gate (user ID check)
5. Conversation history table + retrieval
6. Deploy to Railway — confirm webhook receives messages

**Phase 3: Agent Core (Day 2-3)**
1. All tool executor functions (map tool names to repo calls)
2. Orchestrator agent loop (tool-use iteration)
3. Context builder with dynamic system prompt
4. Wire handlers to agent
5. Test: "just met [name] from [company]" → creates Person record
6. Test: voice note → transcription → contact creation

**Phase 4: Enrichment (Day 3-4)**
1. Whisper transcription service (with .ogg handling)
2. Proxycurl enrichment (single call test first)
3. Tavily company search
4. Intel brief generation
5. Test: "brief me on [name]" end-to-end

**Phase 5: Follow-up and Digest (Day 4-5)**
1. Follow-up email draft generation
2. Daily digest generation
3. APScheduler wired to digest + Telegram send
4. Test all three digest triggers (scheduler, `/digest` command, `get_daily_digest` tool)

**Phase 6: Polish and Pre-conference (Day 5-6)**
1. `scripts/seed_conference.py`
2. `scripts/batch_enrich.py`
3. Response formatting review — ensure all Telegram messages are clean on mobile
4. Error handling: API failures, unknown contacts, malformed voice notes
5. Load test with 50 fake contacts

---

## Key Implementation Notes

**On tool execution:** Each tool should return a structured dict (not a string) so the agent can reason about partial failures. Include a `success: bool` and `error: str` in every response.

**On disambiguation:** When `search_contacts` returns multiple results, return them all to the agent with their IDs. The agent will ask the user to clarify. Never silently pick one.

**On voice notes:** Telegram sends voice as `.ogg` (Opus codec). Whisper accepts this natively. No conversion needed. Max duration to handle gracefully: 3 minutes.

**On embedding generation:** Generate embeddings for Person and Interaction records asynchronously after creation — don't block the response. Use `text-embedding-3-small` (OpenAI) or Anthropic embeddings. Store in pgvector `Vector(1536)` column.

**On cost control:** Proxycurl is the most expensive call (~$0.10/profile). Only enrich when explicitly requested or when a LinkedIn URL is provided. Never auto-enrich on contact creation. Tavily is cheap (<$0.01/search) — fine to call freely.

**On conversation history:** Keep last 20 messages (10 turns) per user. Older messages are archived but not passed to the agent. This keeps token costs low and context fresh.

**On response length:** The system prompt instructs Claude to be brief, but add explicit max-length guidance for each response type in the prompt. Conference context = 5 bullets max. Task list = 7 items max. Follow-up draft = 6 sentences max.

**On the single-user constraint:** The `TELEGRAM_ALLOWED_USER_ID` check in every handler is the security model. This is intentional — no auth system needed, no multi-tenancy, no API keys to manage. Keep it simple.
