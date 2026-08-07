"""
Database engine creation.

The connection URL comes from configuration so the same code runs against
SQLite (local dev) or a production Postgres database without modification.
"""
from sqlalchemy import event
from sqlmodel import Session, create_engine

from config import get_settings

settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    # Allow the same connection to be shared across threads (dev convenience).
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):
        """Enable foreign key enforcement and WAL mode for SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def create_db_and_tables():
    from models import SQLModel

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session

