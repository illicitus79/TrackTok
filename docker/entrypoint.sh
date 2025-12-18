#!/usr/bin/env bash
set -euo pipefail

if [[ "${AUTO_MIGRATE_ON_START:-0}" == "1" ]]; then
  echo "Running database migrations..."
  flask db upgrade || { echo "Migrations failed"; exit 1; }
fi

exec "$@"
