import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect
from src.models import Base


ROOT = Path(__file__).resolve().parents[1]


def run_alembic(database_path: Path, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["ALEMBIC_DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_fresh_database_migrates_to_current_schema(tmp_path):
    database_path = tmp_path / "fresh.db"
    run_alembic(database_path, "upgrade", "head")
    tables = set(inspect(create_engine(f"sqlite:///{database_path}")).get_table_names())
    assert {"users", "accounts", "transactions", "savings_goals"} <= tables
    assert "alembic_version" in tables


def test_legacy_snapshot_can_be_adopted_at_current_head(tmp_path):
    database_path = tmp_path / "legacy.db"
    legacy_engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(legacy_engine)
    assert "alembic_version" not in inspect(legacy_engine).get_table_names()

    run_alembic(database_path, "stamp", "head")
    run_alembic(database_path, "upgrade", "head")

    tables = set(inspect(legacy_engine).get_table_names())
    assert "alembic_version" in tables
    assert {"users", "transactions", "goal_transactions"} <= tables
