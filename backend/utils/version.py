from __future__ import annotations

import os
import re
from pathlib import Path


FALLBACK_VERSION = "0.0.0-alpha.0+unknown"
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<channel>alpha|beta)\.(?P<iteration>0|[1-9]\d*))?$"
)


def _version_candidates() -> tuple[Path, ...]:
    backend_root = Path(__file__).resolve().parents[1]
    repository_root = backend_root.parent
    return repository_root / "VERSION", backend_root / "VERSION"


def load_project_version() -> str:
    configured = os.getenv("PUBCHAT_VERSION", "").strip()
    if configured:
        return configured

    for candidate in _version_candidates():
        try:
            version = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version
    return FALLBACK_VERSION


def parse_project_version(version: str | None = None) -> dict:
    value = (version or load_project_version()).strip()
    match = SEMVER_PATTERN.fullmatch(value)
    if not match:
        return {
            "version": value,
            "valid": False,
            "channel": "unknown",
            "iteration": None,
        }

    data = match.groupdict()
    return {
        "version": value,
        "valid": True,
        "major": int(data["major"]),
        "minor": int(data["minor"]),
        "patch": int(data["patch"]),
        "channel": data["channel"] or "stable",
        "iteration": int(data["iteration"]) if data["iteration"] is not None else None,
    }


PROJECT_VERSION = load_project_version()
PROJECT_VERSION_INFO = parse_project_version(PROJECT_VERSION)
