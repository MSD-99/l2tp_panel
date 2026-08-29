from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DB_PATH, ensure_dirs, DEV_MODE

ensure_dirs()

# In DEV mode (local testing) the DB lives right next to the code, no root needed
if DEV_MODE:
    DB_FILE_PATH = Path("./panel_dev.db").resolve()
    SQLITE_URL = f"sqlite:///{DB_FILE_PATH}"
else:
    DB_FILE_PATH = DB_PATH
    SQLITE_URL = f"sqlite:///{DB_FILE_PATH}"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
