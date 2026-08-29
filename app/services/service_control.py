"""
Generic systemctl wrapper used by the CLI to control both the panel's own
service and the "core" services it manages (strongswan/ipsec, xl2tpd,
nginx). This is separate from systemd_manager.py, which only deals with
installing/enabling the panel's own unit file.
"""
import subprocess

from app.config import DEV_MODE

# Maps a friendly name to the actual systemd unit name on Ubuntu 24.04
CORE_SERVICES = {
    "ipsec": "strongswan-starter",
    "xl2tpd": "xl2tpd",
    "nginx": "nginx",
}


def service_action(unit_name: str, action: str) -> dict:
    """action must be one of: start, stop, restart, status"""
    if DEV_MODE:
        return {"applied": False, "output": f"(dry-run) would run: systemctl {action} {unit_name}"}
    try:
        if unit_name == "strongswan-starter":
            candidates = ["ipsec", "strongswan-starter", "strongswan"]
            for cand in candidates:
                result = subprocess.run(["systemctl", action, cand], capture_output=True, text=True, timeout=20)
                if result.returncode == 0:
                    return {"applied": True, "output": (result.stdout + result.stderr).strip()}
            return {"applied": False, "output": "Failed to control ipsec service"}
        
        result = subprocess.run(
            ["systemctl", action, unit_name], capture_output=True, text=True, timeout=20
        )
        return {"applied": result.returncode == 0, "output": (result.stdout + result.stderr).strip()}
    except Exception as e:
        return {"applied": False, "output": str(e)}


def service_status_text(unit_name: str) -> str:
    if DEV_MODE:
        return "unknown (DEV_MODE)"
    try:
        if unit_name == "strongswan-starter":
            candidates = ["ipsec", "strongswan-starter", "strongswan"]
            for cand in candidates:
                res = subprocess.run(["systemctl", "is-active", cand], capture_output=True, text=True, timeout=5)
                if res.stdout.strip() == "active":
                    return "active"
            return "inactive"
            
        result = subprocess.run(
            ["systemctl", "is-active", unit_name], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "inactive"
    except Exception:
        return "unknown"
