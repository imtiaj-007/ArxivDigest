"""Shared fixtures for integration tests that touch a real Postgres.

Set ``TEST_DATABASE_URL`` to a database that already has the project's
schema applied (e.g. a local Supabase, a throwaway docker postgres, or
the dev DB). All ``db``-marked tests skip when the env var is missing,
so the suite stays green on a fresh checkout without infra.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio

from arxivdigest.adapters.db.repository import PostgresRepository


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set — skipping db-marked tests.")
    return url


@pytest_asyncio.fixture
async def pool(test_database_url: str) -> AsyncIterator[asyncpg.Pool]:
    p = await asyncpg.create_pool(test_database_url, min_size=1, max_size=2)
    assert p is not None
    try:
        yield p
    finally:
        await p.close()


@pytest_asyncio.fixture
async def repository(pool: asyncpg.Pool) -> PostgresRepository:
    return PostgresRepository(pool)


@pytest_asyncio.fixture
async def run_tracker(pool: asyncpg.Pool) -> AsyncIterator[list[str]]:
    """List of run UUIDs inserted during the test. Cleaned up on teardown.

    Tests append the ids they insert; the fixture drops exactly those rows
    afterwards. Pre-existing rows in the test DB are never touched, so the
    same env vars can point at a dev DB without collateral damage.
    """
    ids: list[str] = []
    yield ids
    if ids:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM runs WHERE id::text = ANY($1::text[])",
                ids,
            )
