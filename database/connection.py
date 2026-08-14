import logging
import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

import config

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine
    url = config.DATABASE_URL
    kwargs = {}
    if url.startswith("sqlite"):
        db_path = config.DATABASE_PATH
        parent = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(parent, exist_ok=True)
        kwargs = {"connect_args": {"check_same_thread": False, "timeout": 30},
                  "pool_size": config.DB_POOL_SIZE, "pool_pre_ping": True,
                  "pool_recycle": config.DB_POOL_RECYCLE}

        @event.listens_for(Engine, "connect")
        def _sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    else:
        kwargs = {"pool_size": config.DB_POOL_SIZE, "pool_timeout": config.DB_POOL_TIMEOUT,
                  "pool_recycle": config.DB_POOL_RECYCLE, "pool_pre_ping": True}
    _engine = create_engine(url, **kwargs)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    logger.info("Database engine created: %s", url.split("://")[0])
    return _engine


def get_session() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def session_scope():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    from .migrations import run_migrations
    run_migrations(get_engine())


def dispose_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
        logger.info("Database engine disposed")
    _engine = None
    _SessionLocal = None
