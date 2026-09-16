#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-backend.service"
UNIT_TARGET="/etc/systemd/system/pubchat-backend.service"
HEALTH_URL="${PUBCHAT_HEALTH_URL:-http://127.0.0.1:9000/health/ready}"

if [[ ! -f "$UNIT_SOURCE" ]]; then
  echo "Missing systemd unit: $UNIT_SOURCE" >&2
  exit 1
fi

sudo install -m 0644 "$UNIT_SOURCE" "$UNIT_TARGET"
sudo systemctl daemon-reload
sudo systemctl enable pubchat-backend

# This is the one intentional full restart needed to move an existing
# single-process installation under the Uvicorn multiprocess supervisor.
sudo systemctl restart pubchat-backend

for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error --max-time 2 "$HEALTH_URL" >/dev/null; then
    echo "PubChat backend is ready after service installation."
    sudo systemctl status pubchat-backend --no-pager
    exit 0
  fi
  sleep 1
done

echo "Backend did not become ready after service installation." >&2
sudo systemctl status pubchat-backend --no-pager || true
sudo journalctl -u pubchat-backend -n 120 --no-pager || true
exit 1
