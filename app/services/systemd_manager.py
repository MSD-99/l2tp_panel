import subprocess

from app.config import (
    PANEL_SERVICE_PATH, PANEL_SERVICE_NAME, PANEL_WORKDIR, PANEL_VENV_UVICORN, DEV_MODE
)
from app.settings import load_settings

SERVICE_TEMPLATE = """[Unit]
Description=Central Routing Manager Panel (FastAPI)
After=network.target

[Service]
Type=simple
WorkingDirectory={workdir}
ExecStart={uvicorn} app.main:app --host 0.0.0.0 --port {port}
Restart=on-failure
RestartSec=5
EnvironmentFile=-{workdir}/.env

[Install]
WantedBy=multi-user.target
"""


def build_service_file() -> str:
    port = load_settings()["panel_port"]
    return SERVICE_TEMPLATE.format(workdir=PANEL_WORKDIR, uvicorn=PANEL_VENV_UVICORN, port=port)


def install_service() -> dict:
    content = build_service_file()
    if DEV_MODE:
        return {"applied": False, "content": content}

    with open(PANEL_SERVICE_PATH, "w") as f:
        f.write(content)
    subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
    return {"applied": True, "content": content}


def enable_service() -> dict:
    install_service()
    if DEV_MODE:
        return {"applied": False}
    proc = subprocess.run(["systemctl", "enable", "--now", PANEL_SERVICE_NAME], capture_output=True, text=True)
    return {"applied": proc.returncode == 0, "output": proc.stdout + proc.stderr}


def disable_service() -> dict:
    if DEV_MODE:
        return {"applied": False}
    proc = subprocess.run(["systemctl", "disable", "--now", PANEL_SERVICE_NAME], capture_output=True, text=True)
    return {"applied": proc.returncode == 0, "output": proc.stdout + proc.stderr}


def start_service() -> dict:
    """Installs the unit file first (harmless if already installed), so the
    very first start on a fresh server doesn't fail with "unit not found"."""
    install_service()
    if DEV_MODE:
        return {"applied": False, "output": "(dry-run)"}
    proc = subprocess.run(["systemctl", "start", PANEL_SERVICE_NAME], capture_output=True, text=True)
    return {"applied": proc.returncode == 0, "output": proc.stdout + proc.stderr}


def stop_service() -> dict:
    if DEV_MODE:
        return {"applied": False, "output": "(dry-run)"}
    proc = subprocess.run(["systemctl", "stop", PANEL_SERVICE_NAME], capture_output=True, text=True)
    return {"applied": proc.returncode == 0, "output": proc.stdout + proc.stderr}


def restart_service() -> dict:
    """Rebuilds the unit file first, so a port/path change takes effect."""
    install_service()
    if DEV_MODE:
        return {"applied": False, "output": "(dry-run)"}
    proc = subprocess.run(["systemctl", "restart", PANEL_SERVICE_NAME], capture_output=True, text=True)
    return {"applied": proc.returncode == 0, "output": proc.stdout + proc.stderr}


def service_status() -> str:
    if DEV_MODE:
        return "unknown (DEV_MODE)"
    proc = subprocess.run(["systemctl", "is-active", PANEL_SERVICE_NAME], capture_output=True, text=True)
    return proc.stdout.strip() or "inactive"
