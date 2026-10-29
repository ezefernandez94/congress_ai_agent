# Congress AI Agent

A mobile-first AI networking assistant for conference use, accessible via Telegram.
Captures contacts and interactions via text or voice, enriches them with LinkedIn/company data,
and generates personalized follow-ups.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) or Docker Engine + Compose plugin (Linux)
- A Telegram bot token — create one via [@BotFather](https://t.me/BotFather)
- API keys for Anthropic, OpenAI (Whisper), and optionally Proxycurl and Tavily

No Python, uv, or any other tool needs to be installed on your machine. Everything runs inside Docker.

---

## Quick Start

### 1. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your keys (see [Environment Variables](#environment-variables) below).
At minimum you need `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`, and `ANTHROPIC_API_KEY`.

### Who can use the bot

Access lives in the `bot_users` table, not in the environment. IDs in
`TELEGRAM_ALLOWED_USER_IDS` are seeded as *owners* on every startup; everyone else is
denied unless an owner adds them. Owners add people at runtime with `/adduser <telegram id>`
(the new person gets their ID by sending `/whoami`) and revoke with `/removeuser <telegram id>`.
Removing an ID from the env does **not** revoke it — use `/removeuser`.

Each user controls their own morning digest with `/digest_on` and `/digest_off`; the 7:30 job
sends only to active users with `receives_digest = true`.

### 2. Build the Docker image

```bash
docker compose build
```

This installs all Python dependencies inside the container. Takes ~2 minutes on first run;
subsequent builds are fast due to layer caching.

### 3. Start the database

```bash
docker compose up db -d
```

This starts PostgreSQL 16 with the `pgvector` extension enabled. Data is persisted in a Docker volume.

### 4. Generate the initial database migration

Run this once to create the migration file that defines all tables:

```bash
docker compose run --rm app alembic revision --autogenerate -m "initial"
```

This writes a file to `alembic/versions/` on your machine (the directory is mounted into the container).
Commit this file to version control.

### 5. Start the full stack

```bash
docker compose up
```

On startup the app container will:
1. Wait for the database to be ready
2. Run `alembic upgrade head` (applies any pending migrations)
3. Start the FastAPI server on port `8000`

Verify it's running:

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

Your Telegram bot is now live. Send it a message to confirm.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Token from @BotFather |
| `TELEGRAM_ALLOWED_USER_ID` | Yes* | Your Telegram user ID (legacy single-user var, still honoured) |
| `RAILWAY_PUBLIC_DOMAIN` | Auto | Injected by Railway once a public domain is generated. Takes precedence over `BASE_URL` |
| `TELEGRAM_ALLOWED_USER_IDS` | Yes* | Comma-separated owner IDs, e.g. `123456,789012`. Seeded into `bot_users` on startup |
| `ANTHROPIC_API_KEY` | Yes | Claude API key for the agent and enrichment |
| `OPENAI_API_KEY` | Yes | OpenAI key for Whisper voice transcription |
| `PROXYCURL_API_KEY` | No | LinkedIn enrichment (~$0.10/profile). Only needed when you call `enrich_contact` |
| `TAVILY_API_KEY` | No | Web search for company news. Free tier available |
| `APP_ENV` | No | `development` (default) or `production` |
| `WEBHOOK_SECRET` | No | Random string to secure the Telegram webhook endpoint |
| `BASE_URL` | No | Your public HTTPS URL (e.g. Railway app). Required for `APP_ENV=production` |
| `TIMEZONE` | No | Conference timezone, e.g. `America/New_York` (default: `America/Los_Angeles`) |
| `DIGEST_HOUR` | No | Hour to send the daily digest (default: `7`) |
| `DIGEST_MINUTE` | No | Minute to send the daily digest (default: `30`) |
| `WEB_SESSION_SECRET` | No† | Random string signing the web UI's session cookie. Falls back to a value derived from the bot token, so rotating the token signs everyone out |
| `TELEGRAM_BOT_USERNAME` | No† | Your bot's username without the `@`. Required to render the web login widget |

> † Required in production if you want to use the web UI. See [Web UI](#web-ui).

> **Note:** `DATABASE_URL` in `.env` is ignored when running via Docker Compose — the compose file
> overrides it to point to the `db` service. Your `.env` value is only used if you connect
> to the database directly from your host machine.

---

## Telegram Webhook Setup

**Development (default):** The bot runs in polling mode when `APP_ENV=development` — no public URL needed.

**Production:** Set `APP_ENV=production` and `BASE_URL=https://your-app.example.com`. On startup the app
automatically registers the webhook with Telegram:

```
POST https://api.telegram.org/bot<token>/setWebhook
  url: https://your-app.example.com/webhook/<WEBHOOK_SECRET>
```

For local testing with a public URL, use [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
# Copy the https URL → set BASE_URL and APP_ENV=production in .env
docker compose restart app
```

---

## Web UI

The same service that runs the bot also serves a browser dashboard at `/` — no second deploy,
no Node build step. It covers the whole data model: dashboard, full CRUD and filtering for
people, companies, tasks, opportunities, interactions, meetings, notes and conferences, plus
CSV export, bot-user administration and a chat page that talks to the same agent and shares
the same conversation history as Telegram.

### Development

Nothing to configure. `http://localhost:8000/` signs you in automatically as the first owner
in `bot_users`, because the Telegram Login Widget cannot run against `localhost`.

If you land on the login page with "No owner is seeded", set `TELEGRAM_ALLOWED_USER_IDS`
and restart so the seed runs.

### Production

Access uses the **same `bot_users` allowlist as the bot** — there is no separate web account
and no password. People sign in with the Telegram Login Widget, and only accounts that are
already active bot users get in. `/removeuser` revokes web access immediately, mid-session.

Three things to set up:

1. `WEB_SESSION_SECRET` — any long random string:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. `TELEGRAM_BOT_USERNAME` — your bot's username, without the `@`.
3. **Register the domain with BotFather.** Send `/setdomain` to
   [@BotFather](https://t.me/BotFather), pick your bot, and give it the public host
   (e.g. `your-app.up.railway.app`). The login widget silently refuses to render on any
   domain that is not registered — this step is not optional.

`/health` and `/webhook/{secret}` stay public; every other route requires a session.

## Useful Commands

### View logs

```bash
docker compose logs -f app     # app logs
docker compose logs -f db      # postgres logs
```

### Open a shell inside the app container

```bash
docker compose exec app sh
```

### Connect to the database (psql)

```bash
docker compose exec db psql -U postgres -d conference_bot
```

### Run a script

```bash
# Seed conference data (interactive)
docker compose exec app python scripts/seed_conference.py

# Bulk enrich from a CSV file
docker compose exec app python scripts/batch_enrich.py --input /app/attendees.csv

# Export all data to CSV
docker compose exec app python scripts/export_crm.py --format csv
```

### Trigger the daily digest manually

```bash
docker compose exec app python -c "
import asyncio
from app.jobs.daily_digest import send_daily_digest
asyncio.run(send_daily_digest())
"
```

### Run tests

Tests run on the host against the compose database (published on `localhost:5434`). The test database
`conference_bot_test` and its `vector` extension are created on the first run.

```bash
docker compose up -d db
PYTHONDONTWRITEBYTECODE=1 uv run pytest
```

Set `TEST_DATABASE_URL` to use another database. Don't use `docker compose run app pytest`: the image has
no test dependencies, and its entrypoint ignores the command and starts the bot.

---

## Database Migrations

Every time you change a model (`app/models/`), generate a new migration:

```bash
# 1. Generate migration file
docker compose run --rm app alembic revision --autogenerate -m "describe your change"

# 2. The file appears in alembic/versions/ on your host. Review it.
## Upgrade the head
docker compose exec app alembic upgrade head

# 3. Restart the app — migrations run automatically on startup
docker compose restart app
```

To check current migration state:

```bash
docker compose exec app alembic current
docker compose exec app alembic history
```

---

## Development

### Rebuild after dependency changes

If you modify `pyproject.toml`:

```bash
docker compose build app
docker compose up app
```

### Hot reload (optional)

The app volume mounts the source directory, so code changes are visible inside the container.
To enable uvicorn's auto-reload:

Edit `docker/entrypoint.sh`, change the last line to:
```sh
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Then `docker compose restart app`.

### Stop everything

```bash
docker compose down          # stop and remove containers
docker compose down -v       # also delete the database volume (destructive)
```

---

## Project Structure

```
app/
├── agent/          # LLM orchestration: tools, agent loop, context builder
├── api/            # FastAPI app, webhook endpoint, health route
├── bot/            # Telegram handlers, command router, formatter
├── core/           # Config (pydantic-settings), database engine, logging
├── jobs/           # APScheduler setup, daily digest cron job
├── models/         # SQLAlchemy ORM models (Person, Company, Meeting, etc.)
├── repositories/   # Async DB access layer (no raw SQL in business logic)
├── schemas/        # Pydantic v2 schemas for all entities
├── services/       # Business logic: enrichment, transcription, digest, dashboard, follow-up
└── web/            # Browser UI: Jinja2 templates, HTMX, Telegram-login auth
    ├── crud.py     # Generates the standard list/create/edit/delete routes per entity
    ├── routes/     # Per-entity config, dashboard, chat, users, one-off actions
    ├── static/     # app.css and a vendored htmx.min.js — no CDN, no build step
    └── templates/  # base layout, shared macros, one directory per entity

alembic/            # Database migrations
docker/             # Dockerfile support files (entrypoint, init.sql)
scripts/            # CLI utilities: seed, batch enrich, CRM export
tests/              # pytest test suites
```
