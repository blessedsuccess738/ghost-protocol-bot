"""
database/migrations.py — Schema creation + lightweight migrations.

On startup, `create_all` is idempotent. A simple schema_version table tracks
applied migrations for future ALTER steps. New Ghost Protocol tables
(users, coin_transactions, referrals, ban_records, force_group_settings)
are created automatically via Base.metadata.create_all because the models
are registered on the Base registry.
"""
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

MIGRATIONS = [
    # Each entry is (version, sql) — run once in order.
    # v1 is handled by create_all; future migrations append here.
    # NOTE: attack_logs (AttackLog model) is created automatically by
    # Base.metadata.create_all because the model is registered on Base.
    # No explicit ALTER/CREATE statement is required for fresh databases.
]


def run_migrations(engine: Engine) -> None:
    """Create schema and apply pending migrations."""
    from models import Base

    Base.metadata.create_all(engine)
    logger.info("Schema ensured (create_all)")

    # Schema version table
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_version "
                "(version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
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
