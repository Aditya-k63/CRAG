#!/bin/sh
# Entrypoint used by the Docker image.
# Render injects $PORT (defaults to 8000); the backend serves the chat UI too.
set -e
PORT="${PORT:-8000}"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
