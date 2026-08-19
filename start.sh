#!/bin/sh
# Entrypoint used by the Docker image.
# Render injects $PORT (defaults to 10000 for free tier); supervisord reads it
# via the %(ENV_PORT)s interpolation in supervisord.conf.
set -e
export PORT="${PORT:-10000}"
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf