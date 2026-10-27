#!/bin/sh
set -eu

# One ADK process; sessions are ephemeral within this QA container.
# No key or health data is required for /version and /list-apps readiness checks.
mkdir -p /tmp/polar-adk
exec adk web /app/sport_assistant_agent \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --no-reload \
  --session_service_uri "${ADK_SESSION_SERVICE_URI:-sqlite:////tmp/polar-adk/sessions.db}" \
  --memory_service_uri memory:// \
  --artifact_service_uri memory:// \
  --log_level INFO
