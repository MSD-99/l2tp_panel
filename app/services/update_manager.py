import subprocess
import sys

from app.config import DEV_MODE, PANEL_WORKDIR

SYSTEM_PACKAGES = ["nginx", "xl2tpd", "strongswan", "ufw"]


def update_python_packages() -> dict:
    requirements_path = PANEL_WORKDIR / "requirements.txt"
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "-r", str(requirements_path)]

    if DEV_MODE:
        return {"applied": False, "output": f"(dry-run) would run: {' '.join(cmd)}"}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return {"applied": result.returncode == 0, "output": (result.stdout + result.stderr)[-3000:]}
    except Exception as e:
        return {"applied": False, "output": str(e)}


def update_system_packages() -> dict:
    if DEV_MODE:
        cmd_preview = f"apt-get update && apt-get install --only-upgrade -y {' '.join(SYSTEM_PACKAGES)}"
        return {"applied": False, "output": f"(dry-run) would run: {cmd_preview}"}
    try:
        subprocess.run(["apt-get", "update"], capture_output=True, text=True, timeout=300)
        result = subprocess.run(
            ["apt-get", "install", "--only-upgrade", "-y"] + SYSTEM_PACKAGES,
            capture_output=True, text=True, timeout=600,
        )
        return {"applied": result.returncode == 0, "output": (result.stdout + result.stderr)[-3000:]}
    except Exception as e:
        return {"applied": False, "output": str(e)}
