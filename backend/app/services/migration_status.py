from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.schema import MetaData, Table
from sqlalchemy.sql import select
from sqlalchemy.orm import Session


def _read_current_revision(connection: Connection) -> str | None:
    # Prefer Alembic's direct revision lookup, fallback to raw table read for edge cases.
    try:
        revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version LIMIT 1").scalar_one_or_none()
        if revision:
            return str(revision)
    except SQLAlchemyError:
        pass

    metadata = MetaData()
    try:
        alembic_table = Table("alembic_version", metadata, autoload_with=connection)
    except NoSuchTableError:
        return None

    row = connection.execute(select(alembic_table.c.version_num)).first()
    return str(row[0]) if row else None


def get_migration_status(engine: Engine) -> dict[str, str | bool | None]:
    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"

    alembic_cfg = Config(str(alembic_ini))
    script = ScriptDirectory.from_config(alembic_cfg)
    head_revision = script.get_current_head()

    current_revision: str | None = None
    with engine.connect() as connection:
        current_revision = _read_current_revision(connection)

    return {
        "current_revision": current_revision,
        "head_revision": head_revision,
        "is_up_to_date": current_revision == head_revision,
    }
