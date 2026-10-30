FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/src \
    GYM_COACH_AGENT_MODE=demo \
    GYM_COACH_MAX_INPUT_TOKENS=4096 \
    ADK_MEMORY_MODE=local \
    ADK_DISABLE_LOCAL_STORAGE=1 \
    POLAR_FIT_DIR=/mounts/polar-fit

WORKDIR /app
COPY deploy/requirements.txt /app/deploy/requirements.txt
RUN pip install --no-cache-dir -r /app/deploy/requirements.txt

COPY pyproject.toml /app/pyproject.toml
COPY src/ /app/src/
COPY sport_assistant_agent/ /app/sport_assistant_agent/
COPY deploy/start.sh /app/deploy/start.sh
RUN pip install --no-cache-dir --no-deps . \
    && sed -i 's/\r$//' /app/deploy/start.sh \
    && useradd --uid 10001 --create-home appuser

USER 10001
EXPOSE 8080
CMD ["/bin/sh", "/app/deploy/start.sh"]
