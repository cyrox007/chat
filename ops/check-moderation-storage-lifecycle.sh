#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

cd "$BACKEND_DIR"
PYTHON_BIN="$BACKEND_DIR/venv/bin/python3"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi
"$PYTHON_BIN" - <<'PY'
from settings import config

config.ensure_moderation_media_retention_settings(require_storage_lifecycle=True)
status = config.moderation_media_storage_lifecycle_status()
if not status["aligned"]:
    raise SystemExit("Moderation media storage lifecycle is not aligned")
print(
    "Moderation storage lifecycle: OK "
    f"(application={status['application_retention_days']}d, "
    f"backup={status['backup_retention_days']}d, "
    f"snapshot={status['snapshot_retention_days']}d)"
)
PY
