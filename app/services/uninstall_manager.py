import shutil
import subprocess

from app.config import (
    DEV_MODE, IPSEC_CONF_PATH, XL2TPD_CONF_PATH, NGINX_STREAM_CONF_PATH,
    SECRETS_DIR, PANEL_SERVICE_PATH,
)
from app.services import backup_manager, systemd_manager
from app.services.firewall import CHAIN_NAME


def clean_slate() -> dict:
    """
    Safety-first teardown: always takes a backup before removing anything,
    mirroring phase-2's "Uninstall & Restore Server (Clean Slate)" option.
    """
    backup_result = backup_manager.create_backup(triggered_by="pre_uninstall")

    if DEV_MODE:
        return {
            "applied": False,
            "backup": backup_result,
            "note": "DEV_MODE is active - nothing was actually removed (dry-run).",
        }

    removed = []
    for path in (IPSEC_CONF_PATH, XL2TPD_CONF_PATH, NGINX_STREAM_CONF_PATH):
        try:
            path.unlink(missing_ok=True)
            removed.append(str(path))
        except Exception:
            pass

    if SECRETS_DIR.exists():
        shutil.rmtree(SECRETS_DIR, ignore_errors=True)
        removed.append(str(SECRETS_DIR))

    # Unhook and remove the custom iptables chain
    subprocess.run(["bash", "-c", f"iptables -D FORWARD -j {CHAIN_NAME} 2>/dev/null"], capture_output=True)
    subprocess.run(["bash", "-c", f"iptables -F {CHAIN_NAME} 2>/dev/null"], capture_output=True)
    subprocess.run(["bash", "-c", f"iptables -X {CHAIN_NAME} 2>/dev/null"], capture_output=True)
    removed.append(f"iptables chain {CHAIN_NAME}")

    systemd_manager.disable_service()
    try:
        PANEL_SERVICE_PATH.unlink(missing_ok=True)
        removed.append(str(PANEL_SERVICE_PATH))
    except Exception:
        pass

    return {"applied": True, "backup": backup_result, "removed": removed}
