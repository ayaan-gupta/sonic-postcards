"""Database access: a small connection pool and forward-only SQL migrations."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_MIGRATION_LOCK = 0x50C4_7CA2  # arbitrary advisory lock key for this app

Connection = psycopg.Connection[DictRow]


def migrate(database_url: str) -> list[str]:
    """Apply any migration that has not run yet. Safe to call from several processes."""
    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_MIGRATION_LOCK,))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.name in done:
                    continue
                with conn.transaction():
                    conn.execute(path.read_text(encoding="utf-8").encode())
                    conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
                applied.append(path.name)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_MIGRATION_LOCK,))
    return applied


def _configure(conn: psycopg.Connection[DictRow]) -> None:
    register_vector(conn)
    conn.commit()  # the pool wants connections handed back idle


class Database:
    """Owns the pool. One instance per process, created at startup."""

    def __init__(self, database_url: str, *, max_size: int = 8) -> None:
        self.database_url = database_url
        self._pool: ConnectionPool[Connection] = ConnectionPool(
            database_url,
            min_size=1,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            configure=_configure,
            open=False,
        )

    def open(self) -> None:
        self._pool.open(wait=True, timeout=30)

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        """A connection inside one transaction: commits on success, rolls back on error."""
        with self._pool.connection() as conn:
            yield conn


def as_array(value: object) -> np.ndarray:
    """pgvector hands back its own Vector type (or an ndarray, depending on version). Normalise it."""
    to_numpy = getattr(value, "to_numpy", None)
    if callable(to_numpy):
        return np.asarray(to_numpy(), dtype=np.float32)
    return np.asarray(value, dtype=np.float32)
