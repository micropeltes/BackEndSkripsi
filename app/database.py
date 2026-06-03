from __future__ import annotations

from collections.abc import Callable, Generator
import logging
from typing import TypeVar

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models import Base


settings = get_settings()
logger = logging.getLogger(__name__)
T = TypeVar("T")

TRANSIENT_DB_ERROR_MESSAGES = (
    "ssl connection has been closed unexpectedly",
    "server closed the connection unexpectedly",
    "connection already closed",
    "connection not open",
    "terminating connection",
)

engine_options: dict[str, object] = {
    "pool_pre_ping": True,
}
if not settings.database_url.startswith("sqlite"):
    engine_options.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
    )

engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_transient_db_error(exc: OperationalError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return any(
        transient_message in message
        for transient_message in TRANSIENT_DB_ERROR_MESSAGES
    )


def run_read_with_db_retry(
    db: Session,
    operation: Callable[[], T],
    *,
    operation_name: str,
) -> T:
    try:
        return operation()
    except OperationalError as exc:
        if not is_transient_db_error(exc):
            raise

        logger.warning(
            "Transient database connection error during %s; invalidating session and retrying once",
            operation_name,
        )
        db.invalidate()
        return operation()


def init_db() -> bool:
    try:
        Base.metadata.create_all(bind=engine)
        for table in Base.metadata.sorted_tables:
            for index in table.indexes:
                index.create(bind=engine, checkfirst=True)
        return True
    except SQLAlchemyError as exc:
        logger.exception("Database initialization error: %s", exc)
        return False
