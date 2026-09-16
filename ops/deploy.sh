#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
SERVICE_NAME="${PUBCHAT_SERVICE_NAME:-pubchat-backend}"
SOCKET_NAME="${PUBCHAT_SOCKET_NAME:-pubchat-backend.socket}"
HEALTH_URL="${PUBCHAT_HEALTH_URL:-http://127.0.0.1:9000/health/ready}"
STAGED_DIST="$FRONTEND_DIR/dist.next"
LIVE_DIST="$FRONTEND_DIR/dist"

cd "$PROJECT_DIR"

echo "==> Updating source"
git fetch origin main
git pull --ff-only origin main

echo "==> Backend dependencies"
"$BACKEND_DIR/venv/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"

echo "==> Production configuration preflight"
cd "$BACKEND_DIR"
"$BACKEND_DIR/venv/bin/python" - <<'PY'
from components.realtime.redis_client import redis_topology_mode
from settings import config

config.ensure_security_settings()
config.ensure_realtime_settings()
print("Security settings: OK")
print(f"DEBUG={config.DEBUG}")
print(f"DB={config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
print(f"Redis topology={redis_topology_mode()}")
PY

echo "==> Database migrations"
"$BACKEND_DIR/venv/bin/python" -m alembic heads
"$BACKEND_DIR/venv/bin/python" -m alembic upgrade head
"$BACKEND_DIR/venv/bin/python" -m alembic current

echo "==> Frontend staged build"
cd "$FRONTEND_DIR"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
rm -rf "$STAGED_DIST"
npm run build -- --outDir "$STAGED_DIST"
test -s "$STAGED_DIST/index.html"

# Keep the currently served build intact until the replacement build is fully
# complete. Publish hashed/static files first and index.html last. Old hashed
# assets are intentionally retained so already-open tabs never lose a file they
# still reference during a deployment.
mkdir -p "$LIVE_DIST"
(
  cd "$STAGED_DIST"
  tar --exclude='./index.html' -cf - .
) | (
  cd "$LIVE_DIST"
  tar -xf -
)
install -m 0644 "$STAGED_DIST/index.html" "$LIVE_DIST/index.html"
rm -rf "$STAGED_DIST"

echo "==> Verify persistent production listener and rolling reload"
if ! sudo systemctl cat "$SERVICE_NAME" | grep -q 'ExecReload=.*/kill -HUP'; then
  echo "The installed $SERVICE_NAME unit is still the legacy restart-only unit." >&2
  echo "Run the one-time installer first:" >&2
  echo "  sudo bash $PROJECT_DIR/ops/install-production-service.sh" >&2
  exit 1
fi
if ! sudo systemctl is-active --quiet "$SOCKET_NAME"; then
  echo "$SOCKET_NAME is not active; refusing a deploy that could recreate the 502 window." >&2
  echo "Run the one-time installer first:" >&2
  echo "  sudo bash $PROJECT_DIR/ops/install-production-service.sh" >&2
  exit 1
fi

echo "==> Rolling backend reload"
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
  sudo systemctl reload "$SERVICE_NAME"
else
  # The systemd-owned listener remains bound while the service starts, so nginx
  # sees queued connections rather than connection-refused/502 during startup.
  sudo systemctl start "$SERVICE_NAME"
fi

echo "==> Readiness gate"
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error --max-time 3 "$HEALTH_URL" >/dev/null; then
    echo "Backend ready."
    sudo nginx -t
    sudo systemctl reload nginx
    echo "PubChat deploy completed successfully."
    exit 0
  fi
  sleep 1
done

echo "Deployment failed readiness gate; nginx was not reloaded." >&2
sudo systemctl status "$SOCKET_NAME" --no-pager || true
sudo systemctl status "$SERVICE_NAME" --no-pager || true
sudo journalctl -u "$SERVICE_NAME" -n 120 --no-pager || true
exit 1
