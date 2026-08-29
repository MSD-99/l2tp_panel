#!/usr/bin/env python3
"""
Lightweight script meant to be called by crontab - it only takes a backup,
it does not import the full FastAPI app (faster, no dependency on
uvicorn/fastapi at run time).

Example crontab entry (nightly at 00:00):
    0 0 * * * /path/to/venv/bin/python3 /path/to/l2tp_panel/cron_backup.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.backup_manager import create_backup  # noqa: E402

if __name__ == "__main__":
    result = create_backup(triggered_by="cron")
    print(f"[cron_backup] {result}")
