#!/bin/sh
# Container entrypoint.
#
# The Claude Code CLI saves its OAuth credentials to ~/.claude/. On Railway we
# mount a single persistent volume at /data, so we symlink ~/.claude into it.
# That way `claude login` (run once via `railway shell` after the first deploy)
# writes to the volume and survives every subsequent redeploy.
#
# DB_NAME defaults to /data/database.db in the Railway env, so the SQLite file
# lives on the same volume as the auth creds.

set -e

mkdir -p /data/.claude
ln -snf /data/.claude /root/.claude

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
