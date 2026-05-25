# --- Stage 1: build the React SPA into static/app ---
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# vite build outputs to ../static/app (see frontend/vite.config.js) -> /static/app
RUN npm run build

# --- Stage 2: Python app + Claude Code CLI ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Node 22 + the Claude Code CLI. The app's ChatBot shells out to `claude -p`
# so we need it on PATH; auth lives in /root/.claude and is persisted via a
# Railway volume mounted at /data (see entrypoint.sh).
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @anthropic-ai/claude-code \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /static/app ./static/app

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
