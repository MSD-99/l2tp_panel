"""
Central panel configuration.
Security note: SECRET_KEY must come from an env file, never hardcoded in
code (see the "Security & Access" requirements).
"""
import os
from pathlib import Path

# --- Load .env if present (so CLI/systemd can share the same config) ---
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Whether the app is running on the real production server or just locally
# for dev/testing. This must be resolved BEFORE deciding paths below,
# otherwise even DEV mode would try to write under /etc (needs root).
DEV_MODE = os.environ.get("PANEL_DEV_MODE", "1") == "1"

if DEV_MODE:
    # In dev/test mode, everything lives next to the project itself - no sudo needed
    BASE_DIR = Path("./dev_data").resolve()
else:
    # Real production paths on the VPS - matches phase 2 of the project (needs sudo/root)
    BASE_DIR = Path("/etc/central_proxy")

DB_DIR = BASE_DIR
DB_PATH = DB_DIR / "panel.db"

# Sensitive secret files (PSK, chap-secrets) - kept separate from both the DB and the code
SECRETS_DIR = BASE_DIR / "secrets"
if DEV_MODE:
    IPSEC_SECRETS_PATH = SECRETS_DIR / "ipsec.secrets"
    CHAP_SECRETS_PATH = SECRETS_DIR / "chap-secrets"
else:
    IPSEC_SECRETS_PATH = Path("/etc/ipsec.secrets")
    CHAP_SECRETS_PATH = Path("/etc/ppp/chap-secrets")

# Real OS-level service config paths (only actually written outside DEV_MODE -
# see the _write() helper in config_generator.py)
IPSEC_CONF_PATH = Path("/etc/ipsec.conf")
XL2TPD_CONF_PATH = Path("/etc/xl2tpd/xl2tpd.conf")
XL2TPD_PPP_OPTIONS_PATH = Path("/etc/ppp/options.xl2tpd")
NGINX_STREAM_CONF_PATH = Path("/etc/nginx/stream-available/central_routes.conf")

BACKUP_DIR = BASE_DIR / "backups"

# --- The panel's own systemd service (not the ipsec/xl2tpd/nginx services it manages) ---
PANEL_SERVICE_PATH = Path("/etc/systemd/system/central_panel.service")
PANEL_SERVICE_NAME = "central_panel.service"

# --- Log file (used in DEV_MODE when journalctl isn't available) ---
LOG_FILE = BASE_DIR / "panel.log"
PANEL_WORKDIR = Path(os.environ.get("PANEL_WORKDIR", os.getcwd()))
PANEL_VENV_UVICORN = PANEL_WORKDIR / "venv" / "bin" / "uvicorn"

# Marker used to find/cleanly remove the auto-backup cron line in crontab
CRON_MARKER = "# central_panel_auto_backup"

# --- Auth settings ---
# In a real deployment this must be read from an environment variable, never hardcoded
SECRET_KEY = os.environ.get("PANEL_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_ENV_FILE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

# --- Secrets-at-rest encryption (PSK / PPP password) in the DB ---
# This key must never be hardcoded. Generate it with:
#   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# and store it in a .env file (outside git, root-readable only).
_DEV_FALLBACK_KEY = "g10TBqJTkPXu6HUW8cWa0VcRKUDlztxCRPl__HwAKW0="  # dev/testing only!
ENCRYPTION_KEY = os.environ.get("PANEL_ENCRYPTION_KEY", _DEV_FALLBACK_KEY)

if not DEV_MODE:
    if SECRET_KEY == "CHANGE_ME_IN_PRODUCTION_ENV_FILE":
        raise ValueError("CRITICAL: PANEL_SECRET_KEY is not set in the .env file! Refusing to start in production mode with a hardcoded fallback key.")
    if ENCRYPTION_KEY == _DEV_FALLBACK_KEY:
        raise ValueError("CRITICAL: PANEL_ENCRYPTION_KEY is not set in the .env file! Refusing to start in production mode with a hardcoded fallback key.")



def ensure_dirs():
    for d in (DB_DIR, SECRETS_DIR, BACKUP_DIR):
        d.mkdir(parents=True, exist_ok=True)
