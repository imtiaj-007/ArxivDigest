"""Interactive labeler for the eval ground-truth set.

Walks every paper in the DB, prints the title + abstract + the agent's
proposed themes (from the classify stage) + heuristic-extracted keyword
candidates, and prompts the user to accept / edit / skip. Each accepted
entry is written to ``evals/ground_truth.jsonl`` immediately, so the
session is resume-safe: quit any time and run ``arxivdigest label`` again
to pick up where you left off.

We deliberately do NOT use a stronger LLM to fully auto-label — that would
make the eval an LLM-vs-LLM agreement metric instead of human ground truth.
The agent's proposals are a one-keypress starting point, never the answer.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

import typer

from arxivdigest.adapters.db.postgres import pool_lifespan
from arxivdigest.config import get_settings
from arxivdigest.domain.themes import THEME_SLUGS

# apps/agent/src/arxivdigest/cli/commands/label.py → repo root is parents[6]
_REPO_ROOT = Path(__file__).resolve().parents[6]
GROUND_TRUTH_PATH = _REPO_ROOT / "evals" / "ground_truth.jsonl"

MIN_THEMES = 1
MAX_THEMES = 3
MIN_KEYWORDS = 3
MAX_KEYWORDS = 7
ABSTRACT_PREVIEW_CHARS = 700


def _suggest_keywords(title: str, summary_json: str | None, abstract: str) -> list[str]:
    """Heuristic keyword extraction: capitalized phrases + acronyms + hyphenated compounds."""
    sources = [title]
    if summary_json:
        try:
            summary = json.loads(summary_json)
            sources.extend(str(v) for v in summary.values() if isinstance(v, str))
        except json.JSONDecodeError:
            sources.append(abstract)
    else:
        sources.append(abstract)
    text = " ".join(sources)
    phrases = re.findall(r"\b(?:[A-Z][a-z]+(?:[ -][A-Z][a-z]+)+)\b", text)
    acronyms = re.findall(r"\b[A-Z][A-Z0-9]{1,5}\b", text)
    hyphens = re.findall(r"\b[a-z]+(?:-[a-z]+){1,3}\b", text)
    # Dedupe (case-insensitive) preserving order; prefer phrases > acronyms > hyphens.
    seen: OrderedDict[str, str] = OrderedDict()
    for token in (*phrases, *acronyms, *hyphens):
        key = token.lower()
        if key not in seen:
            seen[key] = token
    return list(seen.values())[:MAX_KEYWORDS]


def _parse_themes(raw: str) -> tuple[list[str] | None, str | None]:
    slugs = [s.strip().lower() for s in raw.split() if s.strip()]
    if not (MIN_THEMES <= len(slugs) <= MAX_THEMES):
        return None, f"need {MIN_THEMES}-{MAX_THEMES} themes (got {len(slugs)})"
    invalid = [s for s in slugs if s not in THEME_SLUGS]
    if invalid:
        return None, f"invalid slugs: {invalid}"
    return slugs, None


def _parse_keywords(raw: str) -> tuple[list[str] | None, str | None]:
    kws = [k.strip() for k in raw.split(",") if k.strip()]
    if not (MIN_KEYWORDS <= len(kws) <= MAX_KEYWORDS):
        return None, f"need {MIN_KEYWORDS}-{MAX_KEYWORDS} keywords (got {len(kws)})"
    return kws, None


async def _load_db_papers(dsn: str | None) -> list[dict[str, Any]]:
    async with pool_lifespan(dsn) as pool, pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT arxiv_id, title, abstract, themes, summary "
            "FROM papers ORDER BY published_at DESC",
        )
    return [dict(r) for r in rows]


def _load_jsonl() -> list[dict[str, Any]]:
    if not GROUND_TRUTH_PATH.exists():
        return []
    return [json.loads(line) for line in GROUND_TRUTH_PATH.read_text().splitlines() if line.strip()]


def _save_jsonl(entries: list[dict[str, Any]]) -> None:
    GROUND_TRUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = (json.dumps(e, ensure_ascii=False) for e in entries)
    GROUND_TRUTH_PATH.write_text("\n".join(lines) + "\n")


def label() -> None:
    """Walk through DB papers and label each for the eval ground-truth set."""
    settings = get_settings()
    db_rows = asyncio.run(_load_db_papers(settings.database_url))
    if not db_rows:
        typer.echo("No papers in DB. Run `arxivdigest run --limit 5` first.")
        return
    by_id = {r["arxiv_id"]: r for r in db_rows}

    existing = _load_jsonl()
    existing_ids = {e["arxiv_id"] for e in existing}
    entries = list(existing)
    for r in db_rows:
        if r["arxiv_id"] not in existing_ids:
            entries.append({
                "arxiv_id": r["arxiv_id"],
                "expected_themes": None,
                "expected_summary_keywords": None,
            })

    pending = [e for e in entries if not e.get("expected_themes")]
    if not pending:
        typer.secho(
            f"All {len(entries)} entries already labeled in {GROUND_TRUTH_PATH}.",
            fg=typer.colors.GREEN,
        )
        return

    typer.echo(
        f"Loaded {len(entries)} entries ({len(pending)} unlabeled). "
        "Quit any time — progress saves after each acceptance.\n",
    )

    try:
        for n, entry in enumerate(pending, start=1):
            row = by_id.get(entry["arxiv_id"])
            if row is None:
                typer.echo(f"[{n}/{len(pending)}] {entry['arxiv_id']} — not in DB, skipping")
                continue
            agent_themes = list(row["themes"] or [])
            suggested_keywords = _suggest_keywords(row["title"], row["summary"], row["abstract"])

            typer.secho(
                f"\n[{n}/{len(pending)}] {row['arxiv_id']} — {row['title']}",
                fg=typer.colors.CYAN, bold=True,
            )
            abstract = row["abstract"]
            if len(abstract) > ABSTRACT_PREVIEW_CHARS:
                abstract = abstract[:ABSTRACT_PREVIEW_CHARS].rstrip() + " […]"
            typer.echo(abstract)
            typer.echo()
            typer.echo(f"  agent themes:        {agent_themes}")
            typer.echo(f"  suggested keywords:  {suggested_keywords}")

            while True:
                raw = typer.prompt("\n[a]ccept  [e]dit  [s]kip  [q]uit", default="a")
                action = raw.strip().lower()
                if action == "q":
                    raise KeyboardInterrupt
                if action == "s":
                    break
                if action == "a":
                    themes_src, keywords_src = " ".join(agent_themes), ", ".join(suggested_keywords)
                elif action == "e":
                    themes_src = typer.prompt(
                        "  themes", default=" ".join(agent_themes),
                    )
                    keywords_src = typer.prompt(
                        "  keywords", default=", ".join(suggested_keywords),
                    )
                else:
                    typer.echo("  ?")
                    continue

                themes, err = _parse_themes(themes_src)
                if err:
                    typer.secho(f"  ! themes: {err}", fg=typer.colors.RED)
                    continue
                keywords, err = _parse_keywords(keywords_src)
                if err:
                    typer.secho(f"  ! keywords: {err}", fg=typer.colors.RED)
                    continue

                entry["expected_themes"] = themes
                entry["expected_summary_keywords"] = keywords
                _save_jsonl(entries)
                typer.secho("  ✓ saved", fg=typer.colors.GREEN)
                break
    except KeyboardInterrupt:
        _save_jsonl(entries)
        typer.secho(
            "\n\nProgress saved. Resume with `arxivdigest label`.",
            fg=typer.colors.YELLOW,
        )
        return

    typer.secho(
        f"\nDone. {len(entries)} entries in {GROUND_TRUTH_PATH}",
        fg=typer.colors.GREEN, bold=True,
    )
