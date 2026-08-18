#!/bin/sh
# Container entrypoint.
# 1. Wait until Postgres accepts connections.
# 2. Run alembic migrations.
# 3. Train ML models if any are missing (idempotent, non-fatal).
# 4. Exec uvicorn (PID 1) so signals reach it.

set -e

echo "==> [entrypoint] waiting for database at ${DATABASE_HOST:-postgres}:${DATABASE_PORT:-5432}..."
for i in $(seq 1 30); do
    if python - <<'PY'
import os, socket, sys
try:
    s = socket.create_connection((
        os.environ.get("DATABASE_HOST", "postgres"),
        int(os.environ.get("DATABASE_PORT", "5432")),
    ), timeout=2)
    s.close()
except Exception:
    sys.exit(1)
PY
    then
        echo "==> [entrypoint] database is reachable"
        break
    fi
    sleep 1
done

echo "==> [entrypoint] running alembic upgrade head"
alembic upgrade head

echo "==> [entrypoint] training ML models (skipped if already present)"
python -m app.ml.train_pipeline || echo "WARN: ml.train_pipeline failed (continuing)"

echo "==> [entrypoint] starting uvicorn on :${BACKEND_PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT:-8000}"
