#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-backend.service"
SOCKET_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-backend.socket"
SERVICE_TARGET="/etc/systemd/system/pubchat-backend.service"
SOCKET_TARGET="/etc/systemd/system/pubchat-backend.socket"
HEALTH_URL="${PUBCHAT_HEALTH_URL:-http://127.0.0.1:9000/health/ready}"

for file in "$SERVICE_SOURCE" "$SOCKET_SOURCE"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing production unit: $file" >&2
    exit 1
  fi
done

sudo install -m 0644 "$SERVICE_SOURCE" "$SERVICE_TARGET"
sudo install -m 0644 "$SOCKET_SOURCE" "$SOCKET_TARGET"
sudo systemctl daemon-reload
sudo systemctl enable pubchat-backend.socket pubchat-backend.service

# One intentional migration interruption: the legacy process currently owns
# port 9000, so it must release the port before systemd can take ownership of
# the persistent listener. All routine deploys after this use reload instead.
sudo systemctl stop pubchat-backend || true
sudo systemctl start pubchat-backend.socket
sudo systemctl start pubchat-backend

if ! sudo systemctl is-active --quiet pubchat-backend.socket; then
  echo "PubChat backend socket failed to start." >&2
  sudo systemctl status pubchat-backend.socket --no-pager || true
  exit 1
fi

for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error --max-time 3 "$HEALTH_URL" >/dev/null; then
    echo "PubChat backend is ready after service installation."
    sudo systemctl status pubchat-backend.socket --no-pager
    sudo systemctl status pubchat-backend --no-pager
    exit 0
  fi
  sleep 1
done

echo "Backend did not become ready after service installation." >&2
sudo systemctl status pubchat-backend.socket --no-pager || true
sudo systemctl status pubchat-backend --no-pager || true
sudo journalctl -u pubchat-backend -n 120 --no-pager || true
exit 1
