import { getDb } from "@repo/db/client";
import { papers } from "@repo/db/schema";
import { sql } from "drizzle-orm";
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const dynamic = "force-dynamic";

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
    // Older/plain-text summaries fall through to the abstract.
  }
  return null;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[6.5rem_1fr] gap-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="text-foreground/90">{children}</dd>
    </div>
  );
}

export default async function PapersPage() {
  const rows = await getDb()
    .select()
    .from(papers)
    .orderBy(sql`${papers.score} desc nulls last`, sql`${papers.publishedAt} desc`)
    .limit(50);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
      <h1 className="mb-2 text-3xl font-semibold tracking-tight">Latest papers</h1>
      <p className="mb-8 text-sm text-muted-foreground">
        {rows.length} paper{rows.length === 1 ? "" : "s"}, ranked by impact.
      </p>

      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No papers yet — the daily agent hasn&apos;t published a digest.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {rows.map((p) => {
            const summary = parseSummary(p.summary);
            return (
              <Card key={p.id}>
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-2">
                    {(p.themes ?? []).map((t) => (
                      <Badge key={t}>{t}</Badge>
                    ))}
                    {p.score != null && (
                      <Badge variant="outline" className="ml-auto">
                        impact {p.score.toFixed(2)}
                      </Badge>
                    )}
                  </div>
                  <CardTitle className="mt-2">
                    <Link href={`/papers/${p.arxivId}`} className="hover:underline">
                      {p.title}
                    </Link>
                  </CardTitle>
                  <CardDescription>
                    {p.authors.slice(0, 4).join(", ")}
                    {p.authors.length > 4 ? " et al." : ""} ·{" "}
                    {p.publishedAt.toISOString().slice(0, 10)} ·{" "}
                    <a
                      href={`https://arxiv.org/abs/${p.arxivId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline"
                    >
                      arxiv ↗
                    </a>
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-sm">
                  {summary ? (
                    <dl className="grid gap-2">
                      <Field label="Problem">{summary.problem}</Field>
                      <Field label="Approach">{summary.approach}</Field>
                      <Field label="Result">{summary.result}</Field>
                      <Field label="Why it matters">{summary.why_it_matters}</Field>
                    </dl>
                  ) : (
                    <p className="text-muted-foreground">{p.abstract}</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </main>
  );
}
