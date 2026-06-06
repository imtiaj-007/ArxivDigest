"""PostgresRepository.sweep_stale_running — wiring + return-shape contract.

The actual SQL is exercised against a real Postgres in integration tests
(when those land). Here we only check that the method:

- delegates to ``conn.fetch`` with the configured ``max_age_minutes``,
- returns the swept row ids as strings (callers log/assert on this).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from arxivdigest.adapters.db.repository import _SWEEP_STALE_RUNS, PostgresRepository


class _StubConn:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.last_sql: str | None = None
        self.last_args: tuple[Any, ...] | None = None

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self.last_sql = sql
        self.last_args = args
        return self.rows


class _StubPool:
    def __init__(self, conn: _StubConn) -> None:
        self._conn = conn

    def acquire(self) -> _AcquireCtx:
        return _AcquireCtx(self._conn)


class _AcquireCtx:
    def __init__(self, conn: _StubConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _StubConn:
        return self._conn

    async def __aexit__(self, *_: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_sweep_returns_swept_ids_as_strings() -> None:
    ids = [uuid4(), uuid4()]
    conn = _StubConn(rows=[{"id": i} for i in ids])
    repo = PostgresRepository(_StubPool(conn))

    swept = await repo.sweep_stale_running(max_age_minutes=45)

    assert swept == [str(i) for i in ids]
    assert conn.last_sql == _SWEEP_STALE_RUNS
    assert conn.last_args == (45,)


@pytest.mark.asyncio
async def test_sweep_with_no_stale_rows_returns_empty_list() -> None:
    conn = _StubConn(rows=[])
    repo = PostgresRepository(_StubPool(conn))

    swept = await repo.sweep_stale_running()

    assert swept == []
    # Default max_age_minutes (60) is propagated.
    assert conn.last_args == (60,)


@pytest.mark.asyncio
async def test_sweep_ids_are_uuid_parseable() -> None:
    """Callers may further wrap ids in UUID() — confirm the strings survive."""
    rid = uuid4()
    conn = _StubConn(rows=[{"id": rid}])
    repo = PostgresRepository(_StubPool(conn))

    [swept_id] = await repo.sweep_stale_running()

    assert UUID(swept_id) == rid
