"""
Small persisted settings the CLI tool can change without touching code:
web panel port, login path (for security-through-obscurity when locked
out), domain, and whether SSL/HTTPS is configured. Read once at process
start; changing these requires restarting the panel service.
"""
import json
from pathlib import Path

from app.config import BASE_DIR

SETTINGS_PATH = BASE_DIR / "settings.json"

DEFAULTS = {
    "panel_port": 8000,
    "login_path": "/login",
    "domain": None,
    "ssl_enabled": False,
}


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text())
            return {**DEFAULTS, **data}
        except Exception:
            return dict(DEFAULTS)
    return dict(DEFAULTS)


def save_settings(partial: dict) -> dict:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    current = load_settings()
    current.update(partial)
    SETTINGS_PATH.write_text(json.dumps(current, indent=2))
    return current
