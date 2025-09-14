#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

python -m pip install -U pip >/dev/null
pip install -r requirements.txt >/dev/null

# Extra deps used by the app
pip install 'aiohttp>=3.11.18' 'filelock>=3.18.0' itsdangerous 'pydantic[email]>=2.10.4' >/dev/null || true

# Start redis if not up
if ! (nc -z 127.0.0.1 6379 >/dev/null 2>&1); then
  if command -v brew >/dev/null 2>&1; then
    brew services start redis >/dev/null 2>&1 || true
  fi
  if ! (nc -z 127.0.0.1 6379 >/dev/null 2>&1); then
    if command -v redis-server >/dev/null 2>&1; then
      redis-server --daemonize yes >/dev/null 2>&1 || true
    elif [ -x /opt/homebrew/opt/redis/bin/redis-server ]; then
      /opt/homebrew/opt/redis/bin/redis-server --daemonize yes >/dev/null 2>&1 || true
    fi
  fi
fi

export PYTHONPATH=src
exec python -m app.main

