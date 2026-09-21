#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
SERVICE_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-moderation-media-retention.service"
TIMER_SOURCE="$PROJECT_DIR/ops/systemd/pubchat-moderation-media-retention.timer"
SERVICE_TARGET="/etc/systemd/system/pubchat-moderation-media-retention.service"
TIMER_TARGET="/etc/systemd/system/pubchat-moderation-media-retention.timer"

for file in "$SERVICE_SOURCE" "$TIMER_SOURCE"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing moderation retention unit: $file" >&2
    exit 1
  fi
done

cd "$BACKEND_DIR"
"$BACKEND_DIR/venv/bin/python3" - <<'PY'
from pathlib import Path

from settings import config

config.ensure_moderation_media_retention_settings()
root = Path(config.MODERATION_MEDIA_ROOT)
root.mkdir(parents=True, exist_ok=True, mode=0o700)
root.chmod(0o700)
print(
    "Moderation media retention settings: OK "
    f"(root={root}, retention_days={config.MODERATION_MEDIA_REMOVED_RETENTION_DAYS})"
)
PY

sudo install -m 0644 "$SERVICE_SOURCE" "$SERVICE_TARGET"
sudo install -m 0644 "$TIMER_SOURCE" "$TIMER_TARGET"
sudo systemctl daemon-reload
sudo systemctl enable --now pubchat-moderation-media-retention.timer

# Run one bounded cycle so path/DB problems are visible during installation.
if ! sudo systemctl start pubchat-moderation-media-retention.service; then
  echo "PubChat moderation media retention worker failed its first run." >&2
  sudo systemctl status pubchat-moderation-media-retention.service --no-pager || true
  sudo journalctl -u pubchat-moderation-media-retention.service -n 120 --no-pager || true
  exit 1
fi

sudo systemctl status pubchat-moderation-media-retention.timer --no-pager
sudo systemctl status pubchat-moderation-media-retention.service --no-pager || true
