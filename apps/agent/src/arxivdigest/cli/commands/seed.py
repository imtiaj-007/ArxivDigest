import asyncio

import structlog

from arxivdigest.adapters.db.postgres import pool_lifespan
from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.config import get_settings

log = structlog.get_logger()

DEMO_ARXIV_ID = "0000.0000"


async def _insert_demo() -> str:
    settings = get_settings()
    # Fake but correctly-shaped 1024-dim embedding (pgvector text literal).
    embedding = "[" + ",".join(["0.1"] * 1024) + "]"
    async with pool_lifespan(settings.database_url) as pool, pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO papers
                (arxiv_id, title, abstract, authors, categories, published_at,
                 embedding, summary, score)
            VALUES ($1, $2, $3, $4, $5, now(), $6::vector, $7, $8)
            ON CONFLICT (arxiv_id) DO UPDATE SET
                title = EXCLUDED.title,
                updated_at = now()
            RETURNING id
            """,
            DEMO_ARXIV_ID,
            "Hello from ArxivDigest",
            "A placeholder paper inserted by the seed-demo smoke test to verify the "
            "agent can write to Supabase and the web app can read it back.",
            ["ArxivDigest Bot"],
            ["cs.AI"],
            embedding,
            "This row proves the end-to-end loop: agent → Postgres → Next.js.",
            0.99,
        )
        if row is None:
            raise RuntimeError("insert returned no row")
        return str(row["id"])


def seed_demo() -> None:
    """Insert (or upsert) a demo paper row to smoke-test the agent → DB → web loop."""
    with trace_span("seed-demo", arxiv_id=DEMO_ARXIV_ID) as span:
        paper_id = asyncio.run(_insert_demo())
        log.info("seed.demo.inserted", paper_id=paper_id, arxiv_id=DEMO_ARXIV_ID)
        if span is not None:
            span.update(output={"paper_id": paper_id})
