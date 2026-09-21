import os
import shutil
import json
import tempfile
from datetime import datetime
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker
from src.models.base import Base

DB_PATH = os.path.join(os.path.expanduser("~"), ".expense_manager", "database.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
PREFERENCES_PATH = os.path.join(os.path.expanduser("~"), ".expense_manager", "preferences.json")
PREFERENCES_VERSION = 1
DEFAULT_PREFERENCES = {
    "version": PREFERENCES_VERSION,
    "font_family": "Canva Sans, IBM Plex Sans Arabic, Noto Sans Variable, Noto Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif",
    "font_size": "14px",
    "accent_color": "#D4AF37",
    "dashboard_period": "this_month",
    "dashboard_custom_start": "",
    "dashboard_custom_end": "",
}


def load_preferences() -> dict[str, str | int]:
    if not os.path.exists(PREFERENCES_PATH):
        return DEFAULT_PREFERENCES.copy()
    try:
        with open(PREFERENCES_PATH, "r", encoding="utf-8") as preferences_file:
            stored = json.load(preferences_file)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_PREFERENCES.copy()
    if stored.get("version") != PREFERENCES_VERSION:
        return DEFAULT_PREFERENCES.copy()
    preferences = DEFAULT_PREFERENCES.copy()
    preferences.update({
        key: stored[key]
        for key in (
            "font_family",
            "font_size",
            "accent_color",
            "dashboard_period",
            "dashboard_custom_start",
            "dashboard_custom_end",
        )
        if key in stored
    })
    return preferences


def save_preferences(preferences: dict[str, str | int]) -> None:
    os.makedirs(os.path.dirname(PREFERENCES_PATH), exist_ok=True)
    payload = DEFAULT_PREFERENCES.copy()
    payload.update(preferences)
    payload["version"] = PREFERENCES_VERSION
    directory = os.path.dirname(PREFERENCES_PATH)
    fd, temporary_path = tempfile.mkstemp(prefix="preferences-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as preferences_file:
            json.dump(payload, preferences_file, indent=2)
        os.replace(temporary_path, PREFERENCES_PATH)
    except OSError:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise

def init_db():
    project_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(project_root / "alembic.ini"))
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    application_tables = tables - {"alembic_version"}
    if application_tables:
        if "alembic_version" not in tables:
            command.stamp(alembic_config, "head")
        else:
            command.upgrade(alembic_config, "head")
    else:
        command.upgrade(alembic_config, "head")


def backup_db(destination_dir: str | None = None) -> str:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database does not exist: {DB_PATH}")
    target_dir = destination_dir or os.path.dirname(DB_PATH)
    os.makedirs(target_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = os.path.join(target_dir, f"database_backup_{timestamp}.db")
    shutil.copy2(DB_PATH, destination)
    return destination
    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
