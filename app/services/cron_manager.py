import subprocess

from app.config import CRON_MARKER, PANEL_WORKDIR, DEV_MODE


def _current_crontab() -> str:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def cron_status() -> bool:
    if DEV_MODE:
        return False
    return CRON_MARKER in _current_crontab()


def enable_cron_backup() -> dict:
    cron_line = f"0 0 * * * {PANEL_WORKDIR}/venv/bin/python3 {PANEL_WORKDIR}/cron_backup.py {CRON_MARKER}"

    if DEV_MODE:
        return {"applied": False, "line": cron_line}

    existing = _current_crontab()
    lines = [l for l in existing.splitlines() if CRON_MARKER not in l]
    lines.append(cron_line)
    new_crontab = "\n".join(lines) + "\n"

    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
    return {"applied": proc.returncode == 0, "line": cron_line, "stderr": proc.stderr}


def disable_cron_backup() -> dict:
    if DEV_MODE:
        return {"applied": False}

    existing = _current_crontab()
    lines = [l for l in existing.splitlines() if CRON_MARKER not in l]
    new_crontab = "\n".join(lines) + ("\n" if lines else "")

    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
    return {"applied": proc.returncode == 0, "stderr": proc.stderr}
