"""Asyncpg connection pool. Thin wrapper used by repositories in adapters/db/."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg


async def create_pool(dsn: str | None = None) -> asyncpg.Pool:
    """Open an asyncpg connection pool against the configured Postgres.

    DSN format: postgresql://user:pass@host:port/db
    For Supabase, use the *transaction-mode pooler* URL (port 6543) with prepared
    statements disabled at the SQL layer when needed.
    """
    url = dsn or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return await asyncpg.create_pool(
        url,
        min_size=1,
        max_size=4,
        statement_cache_size=0,  # disable for Supabase transaction-mode pooler
    )


@asynccontextmanager
async def pool_lifespan(dsn: str | None = None) -> AsyncIterator[asyncpg.Pool]:
    """Context manager that opens a pool and guarantees cleanup."""
    pool = await create_pool(dsn)
    try:
        yield pool
    finally:
        await pool.close()
