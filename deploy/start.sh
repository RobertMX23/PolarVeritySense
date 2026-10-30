#!/bin/sh
set -eu

# One ADK process; sessions are ephemeral within this QA container.  The ASGI
# wrapper binds browser session IDs to IAP before ADK can read them.
mkdir -p /tmp/polar-adk
exec python -m uvicorn sport_assistant_agent.server:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --log-level info
