#!/bin/sh
set -e

echo "Waiting for database to be ready..."

python << 'PYEOF'
import asyncio
import os
import sys

import asyncpg


async def wait_for_db():
    raw_url = os.getenv("DATABASE_URL", "")
    url = raw_url.replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        print("DATABASE_URL not set", flush=True)
        sys.exit(1)

    for attempt in range(1, 31):
        try:
            conn = await asyncpg.connect(url)
            await conn.close()
            print("Database is ready.", flush=True)
            return
        except Exception as exc:
            print(f"Attempt {attempt}/30 — waiting for DB: {exc}", flush=True)
            await asyncio.sleep(1)

    print("Database not reachable after 30 seconds. Exiting.", flush=True)
    sys.exit(1)


asyncio.run(wait_for_db())
PYEOF

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
