"""Persistent token revocation store."""
from __future__ import annotations

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from .auth import RevocationStore
from .postgres_repository import PostgresConfigurationError


class PostgresRevocationStore(RevocationStore):
    def __init__(self, database_url: str) -> None:
        if psycopg is None:
            raise PostgresConfigurationError("psycopg is required for PostgreSQL token revocation")
        self.database_url = database_url

    def revoke(self, token_id: str, expires_at: int) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                INSERT INTO yappy_token_revocations (token_id, expires_at, revoked_at)
                VALUES (%s, to_timestamp(%s), now())
                ON CONFLICT (token_id) DO UPDATE SET expires_at = EXCLUDED.expires_at, revoked_at = now()
                """,
                (token_id, expires_at),
            )

    def is_revoked(self, token_id: str) -> bool:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("DELETE FROM yappy_token_revocations WHERE expires_at <= now()")
            return connection.execute(
                "SELECT 1 FROM yappy_token_revocations WHERE token_id = %s",
                (token_id,),
            ).fetchone() is not None
