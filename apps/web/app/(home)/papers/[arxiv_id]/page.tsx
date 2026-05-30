import { getDb } from "@repo/db/client";
import { papers } from "@repo/db/schema";
import { and, eq, isNotNull, ne, sql } from "drizzle-orm";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";

// ISR: each per-paper page is effectively static once generated; refresh daily
// in case ranking/themes change after re-runs.
export const revalidate = 86_400;

type StructuredSummary = {
  problem: string;
  approach: string;
  result: string;
  why_it_matters: string;
};

function parseSummary(raw: string | null): StructuredSummary | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<StructuredSummary>;
    if (typeof parsed.problem === "string") {
      return parsed as StructuredSummary;
    }
  } catch {
    /* old plain-text rows fall through */
  }
  return null;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="text-foreground/90">{children}</dd>
    </div>
  );
}

const NEIGHBORS = 5;

type Neighbor = {
  id: string;
  arxivId: string;
  title: string;
  themes: string[] | null;
  score: number | null;
  distance: number;
};

async function fetchNeighbors(arxivId: string, embedding: number[]): Promise<Neighbor[]> {
  const literal = `[${embedding.join(",")}]`;
  const distance = sql<number>`${papers.embedding} <=> ${literal}::vector`;
  return await getDb()
    .select({
      id: papers.id,
      arxivId: papers.arxivId,
      title: papers.title,
      themes: papers.themes,
      score: papers.score,
      distance,
    })
    .from(papers)
    .where(and(ne(papers.arxivId, arxivId), isNotNull(papers.embedding)))
    .orderBy(distance)
    .limit(NEIGHBORS);
}

export default async function PaperDetailPage(props: {
  params: Promise<{ arxiv_id: string }>;
}) {
  const { arxiv_id: arxivId } = await props.params;

  const [paper] = await getDb()
    .select()
    .from(papers)
    .where(eq(papers.arxivId, arxivId))
    .limit(1);

  if (!paper) notFound();

  const summary = parseSummary(paper.summary);
  const neighbors = paper.embedding ? await fetchNeighbors(arxivId, paper.embedding) : [];

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
      <Link
        href="/papers"
        className="mb-6 inline-block text-sm text-muted-foreground hover:underline"
      >
        ← All papers
      </Link>

      <header className="mb-8">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {(paper.themes ?? []).map((t) => (
            <Link key={t} href={`/themes/${t}`}>
              <Badge className="transition-opacity hover:opacity-80">{t}</Badge>
            </Link>
          ))}
          {paper.score != null && (
            <Badge variant="outline" className="ml-auto">
              impact {paper.score.toFixed(2)}
            </Badge>
          )}
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">{paper.title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {paper.authors.slice(0, 6).join(", ")}
          {paper.authors.length > 6 ? " et al." : ""}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          <span className="font-mono">{paper.arxivId}</span> ·{" "}
          {paper.publishedAt.toISOString().slice(0, 10)} ·{" "}
          <a
            className="hover:underline"
            href={`https://arxiv.org/abs/${paper.arxivId}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            arxiv abstract ↗
          </a>{" "}
          ·{" "}
          <a
            className="hover:underline"
            href={`https://arxiv.org/pdf/${paper.arxivId}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            pdf ↗
          </a>
        </p>
      </header>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted-foreground">
          Summary
        </h2>
        {summary ? (
          <dl className="grid gap-3 text-sm">
            <Field label="Problem">{summary.problem}</Field>
            <Field label="Approach">{summary.approach}</Field>
            <Field label="Result">{summary.result}</Field>
            <Field label="Why it matters">{summary.why_it_matters}</Field>
          </dl>
        ) : (
          <p className="text-sm text-muted-foreground">No structured summary yet.</p>
        )}
      </section>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted-foreground">
          Abstract
        </h2>
        <p className="whitespace-pre-line text-sm text-foreground/90">{paper.abstract}</p>
        <p className="mt-2 text-xs text-muted-foreground">
          Categories: {paper.categories.join(", ") || "—"}
        </p>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted-foreground">
          Similar papers
        </h2>
        {neighbors.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {paper.embedding
              ? "No other embedded papers to compare against yet."
              : "This paper hasn't been embedded yet."}
          </p>
        ) : (
          <ul className="space-y-2">
            {neighbors.map((n) => (
              <li
                key={n.id}
                className="flex items-baseline justify-between gap-4 rounded-md border border-border px-3 py-2 text-sm hover:bg-muted/30"
              >
                <Link
                  href={`/papers/${n.arxivId}`}
                  className="min-w-0 flex-1 truncate font-medium hover:underline"
                >
                  {n.title}
                </Link>
                <span className="flex shrink-0 items-center gap-3 text-xs text-muted-foreground">
                  {n.score != null && (
                    <span className="tabular-nums">impact {n.score.toFixed(2)}</span>
                  )}
                  <span className="tabular-nums">dist {n.distance.toFixed(2)}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-xs text-muted-foreground">
          Nearest neighbors by cosine distance over 1024-d BGE embeddings (pgvector HNSW).
        </p>
      </section>
    </main>
  );
}
