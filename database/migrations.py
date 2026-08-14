import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

MIGRATIONS = []


def run_migrations(engine: Engine) -> None:
    from models import Base
    Base.metadata.create_all(engine)
    logger.info("Schema ensured (create_all)")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
        row = conn.execute(text("SELECT COALESCE(MAX(version), 0) FROM schema_version")).scalar()
        current = int(row or 0)
    for version, sql in MIGRATIONS:
        if version > current:
            with engine.begin() as conn:
                for stmt in sql.split(";"):
                    if stmt.strip():
                        conn.execute(text(stmt))
                conn.execute(text("INSERT INTO schema_version (version) VALUES (:v)"), {"v": version})
            logger.info("Applied migration v%d", version)
