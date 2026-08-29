import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from app.config import BACKUP_DIR, SECRETS_DIR, DEV_MODE

BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _get_db_file_path() -> Path:
    # Local import to avoid a circular import with database.py
    from app.database import DB_FILE_PATH
    return DB_FILE_PATH


def create_backup(triggered_by: str = "manual") -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"backup_{timestamp}_{triggered_by}.zip"
    archive_path = BACKUP_DIR / archive_name

    db_path = _get_db_file_path()

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if db_path.exists():
            zf.write(db_path, arcname="panel.db")
        if SECRETS_DIR.exists():
            for root, _, files in os.walk(SECRETS_DIR):
                for fname in files:
                    full = Path(root) / fname
                    rel = full.relative_to(SECRETS_DIR)
                    zf.write(full, arcname=f"secrets/{rel}")

    return {
        "filename": archive_name,
        "path": str(archive_path),
        "size_kb": round(archive_path.stat().st_size / 1024, 1),
        "created_at": timestamp,
    }


def list_backups() -> list[dict]:
    items = []
    for f in sorted(BACKUP_DIR.glob("backup_*.zip"), reverse=True):
        items.append({
            "filename": f.name,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return items


def restore_backup(filename: str) -> dict:
    archive_path = BACKUP_DIR / filename
    if not archive_path.exists() or archive_path.parent != BACKUP_DIR:
        raise FileNotFoundError("Backup file not found.")

    db_path = _get_db_file_path()

    if DEV_MODE:
        return {"applied": False, "note": "DEV_MODE is active - the restore wasn't actually applied (dry-run)."}

    with zipfile.ZipFile(archive_path, "r") as zf:
        # Take an emergency backup of the current DB before overwriting it
        if db_path.exists():
            shutil.copy2(db_path, db_path.with_suffix(".db.before_restore"))

        for member in zf.namelist():
            if member == "panel.db":
                with zf.open(member) as src, open(db_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            elif member.startswith("secrets/"):
                target = SECRETS_DIR / Path(member).relative_to("secrets")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    return {"applied": True, "restored_from": filename}
