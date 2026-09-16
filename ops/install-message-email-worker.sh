#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
SERVICE_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-message-email.service"
TIMER_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-message-email.timer"
SERVICE_TARGET="/etc/systemd/system/pubchat-message-email.service"
TIMER_TARGET="/etc/systemd/system/pubchat-message-email.timer"

for file in "$SERVICE_SOURCE" "$TIMER_SOURCE"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing notification worker unit: $file" >&2
    exit 1
  fi
done

cd "$BACKEND_DIR"
"$BACKEND_DIR/venv/bin/python3" - <<'PY'
from settings import config
config.ensure_security_settings()
config.ensure_realtime_settings()
config.ensure_message_email_delivery_settings()
print("Message email delivery settings: OK")
PY

sudo install -m 0644 "$SERVICE_SOURCE" "$SERVICE_TARGET"
sudo install -m 0644 "$TIMER_SOURCE" "$TIMER_TARGET"
sudo systemctl daemon-reload
sudo systemctl enable --now pubchat-message-email.timer

# Run one bounded cycle now so configuration/provider problems are visible during installation.
if ! sudo systemctl start pubchat-message-email.service; then
  echo "PubChat message email worker failed its first run." >&2
  sudo systemctl status pubchat-message-email.service --no-pager || true
  sudo journalctl -u pubchat-message-email.service -n 120 --no-pager || true
  exit 1
fi

sudo systemctl status pubchat-message-email.timer --no-pager
sudo systemctl status pubchat-message-email.service --no-pager || true
