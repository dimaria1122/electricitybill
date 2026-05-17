#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

if [ ! -f ".env" ]; then
  echo "Missing .env. Copy .env.example to .env and fill your token first." >&2
  exit 1
fi

python3 -m uvicorn electricitybill.app:app --host "$HOST" --port "$PORT"
