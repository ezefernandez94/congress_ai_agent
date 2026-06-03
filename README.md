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
At minimum you need `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`, and `ANTHROPIC_API_KEY`.

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
| `TELEGRAM_ALLOWED_USER_ID` | Yes | Your Telegram user ID (only this user can use the bot) |
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

```bash
docker compose run --rm app pytest tests/ -v
```

---

## Database Migrations

Every time you change a model (`app/models/`), generate a new migration:

```bash
# 1. Generate migration file
docker compose run --rm app alembic revision --autogenerate -m "describe your change"

# 2. The file appears in alembic/versions/ on your host. Review it.

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
└── services/       # Business logic: enrichment, transcription, digest, follow-up

alembic/            # Database migrations
docker/             # Dockerfile support files (entrypoint, init.sql)
scripts/            # CLI utilities: seed, batch enrich, CRM export
tests/              # pytest test suites
```
