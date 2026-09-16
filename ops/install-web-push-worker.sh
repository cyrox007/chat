#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
SERVICE_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-web-push.service"
TIMER_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-web-push.timer"
SERVICE_TARGET="/etc/systemd/system/pubchat-web-push.service"
TIMER_TARGET="/etc/systemd/system/pubchat-web-push.timer"

for file in "$SERVICE_SOURCE" "$TIMER_SOURCE"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing Web Push unit: $file" >&2
    exit 1
  fi
done

cd "$BACKEND_DIR"
"$BACKEND_DIR/venv/bin/python3" - <<'PY'
from settings import config
config.ensure_security_settings()
config.ensure_realtime_settings()
config.ensure_web_push_settings()
print("Web Push settings: OK")
PY

sudo install -m 0644 "$SERVICE_SOURCE" "$SERVICE_TARGET"
sudo install -m 0644 "$TIMER_SOURCE" "$TIMER_TARGET"
sudo systemctl daemon-reload
sudo systemctl enable --now pubchat-web-push.timer

if ! sudo systemctl start pubchat-web-push.service; then
  echo "PubChat Web Push worker failed its first run." >&2
  sudo systemctl status pubchat-web-push.service --no-pager || true
  sudo journalctl -u pubchat-web-push.service -n 120 --no-pager || true
  exit 1
fi

sudo systemctl status pubchat-web-push.timer --no-pager
sudo systemctl status pubchat-web-push.service --no-pager || true
