FROM python:3.11-slim

# Copy uv binary from the official image — nothing installs on the host
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System dependencies required to compile asyncpg (C extension)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying the rest of the code
# so this layer is cached unless pyproject.toml changes
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

# Copy application source
COPY . .

EXPOSE 8000

ENTRYPOINT ["sh", "docker/entrypoint.sh"]
