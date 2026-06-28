#!/bin/sh
set -e

if [ "${SKIP_MIGRATIONS:-false}" = "true" ] || [ "${SKIP_MIGRATIONS:-0}" = "1" ]; then
	echo "Skipping database migrations (SKIP_MIGRATIONS enabled)."
else
	echo "Applying database migrations..."
	if ! alembic upgrade head; then
		if [ "${ALLOW_MIGRATION_FAILURE:-false}" = "true" ] || [ "${ALLOW_MIGRATION_FAILURE:-0}" = "1" ]; then
			echo "Migration failed, continuing startup (ALLOW_MIGRATION_FAILURE enabled)."
		else
			exit 1
		fi
	fi
fi

echo "Starting WatchTower API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
