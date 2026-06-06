"""Integration coverage for PostgresRepository.sweep_stale_running.

Exercises the actual SQL semantics against a real Postgres — the unit
test mocks the connection and only verifies wiring. Skipped without
``TEST_DATABASE_URL``.

Each test inserts its own rows (via the ``run_tracker`` fixture) and
relies on the conftest teardown to drop exactly those rows. Pre-existing
rows in the test DB are never touched.
"""

from __future__ import annotations

import asyncpg
import pytest

from arxivdigest.adapters.db.repository import PostgresRepository

pytestmark = pytest.mark.db


async def _insert_running(
    pool: asyncpg.Pool, tracker: list[str], *, age_minutes: int
) -> str:
    """Insert a runs row with status='running' and started_at backdated."""
    async with pool.acquire() as conn:
        row_id = await conn.fetchval(
            "INSERT INTO runs (status, started_at) "
            "VALUES ('running', now() - make_interval(mins => $1)) "
            "RETURNING id",
            age_minutes,
        )
    rid = str(row_id)
    tracker.append(rid)
    return rid


async def _status_of(pool: asyncpg.Pool, run_id: str) -> tuple[str, str | None]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status, error_summary FROM runs WHERE id::text = $1",
            run_id,
        )
    assert row is not None
    return row["status"], row["error_summary"]


async def test_sweep_marks_old_running_rows_failed(
    repository: PostgresRepository, pool: asyncpg.Pool, run_tracker: list[str]
) -> None:
    """A row that's been 'running' longer than the cap → swept to failed."""
    stale_id = await _insert_running(pool, run_tracker, age_minutes=90)

    swept = await repository.sweep_stale_running(max_age_minutes=60)

    assert stale_id in swept
    status, err = await _status_of(pool, stale_id)
    assert status == "failed"
    assert err is not None and err.startswith("stale ")


async def test_sweep_leaves_fresh_running_rows_alone(
    repository: PostgresRepository, pool: asyncpg.Pool, run_tracker: list[str]
) -> None:
    """A row younger than the cap → must stay 'running'.

    Critical: the daily-digest concurrency group serializes runs, but the
    sweeper runs at the START of a new pipeline before start_run(), so
    racing a legit row by misconfigured max_age would clobber the new run.
    """
    fresh_id = await _insert_running(pool, run_tracker, age_minutes=10)

    swept = await repository.sweep_stale_running(max_age_minutes=60)

    assert fresh_id not in swept
    status, err = await _status_of(pool, fresh_id)
    assert status == "running"
    assert err is None


async def test_sweep_handles_mixed_ages(
    repository: PostgresRepository, pool: asyncpg.Pool, run_tracker: list[str]
) -> None:
    """Multiple rows at once: only the old ones go."""
    stale_a = await _insert_running(pool, run_tracker, age_minutes=120)
    stale_b = await _insert_running(pool, run_tracker, age_minutes=75)
    fresh = await _insert_running(pool, run_tracker, age_minutes=5)

    swept = set(await repository.sweep_stale_running(max_age_minutes=60))

    assert {stale_a, stale_b} <= swept
    assert fresh not in swept

    for rid in (stale_a, stale_b):
        status, _ = await _status_of(pool, rid)
        assert status == "failed"
    status, _ = await _status_of(pool, fresh)
    assert status == "running"


async def test_sweep_is_idempotent(
    repository: PostgresRepository, pool: asyncpg.Pool, run_tracker: list[str]
) -> None:
    """Running the sweeper twice in a row doesn't re-touch already-failed rows."""
    stale_id = await _insert_running(pool, run_tracker, age_minutes=90)

    swept_first = await repository.sweep_stale_running(max_age_minutes=60)
    swept_second = await repository.sweep_stale_running(max_age_minutes=60)

    assert stale_id in swept_first
    assert stale_id not in swept_second


async def test_sweep_sets_completed_at_to_now(
    repository: PostgresRepository, pool: asyncpg.Pool, run_tracker: list[str]
) -> None:
    """completed_at must land on the sweep call, not the original started_at."""
    stale_id = await _insert_running(pool, run_tracker, age_minutes=90)

    await repository.sweep_stale_running(max_age_minutes=60)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT started_at, completed_at FROM runs WHERE id::text = $1",
            stale_id,
        )
    assert row is not None
    assert row["completed_at"] is not None
    # completed_at should be recent (within last minute), well after started_at.
    delta = row["completed_at"] - row["started_at"]
    assert delta.total_seconds() > 60 * 60  # > 60 min spread between them
