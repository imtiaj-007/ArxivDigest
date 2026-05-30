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
import { parseSummary } from "@/lib/papers";

export type PaperRow = {
  id: string;
  arxivId: string;
  title: string;
  authors: string[];
  publishedAt: Date;
  abstract: string;
  summary: string | null;
  themes: string[] | null;
  score: number | null;
};

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

export function PaperCard({ paper }: { paper: PaperRow }) {
  const summary = parseSummary(paper.summary);
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
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
        <CardTitle className="mt-2">
          <Link href={`/papers/${paper.arxivId}`} className="hover:underline">
            {paper.title}
          </Link>
        </CardTitle>
        <CardDescription>
          {paper.authors.slice(0, 4).join(", ")}
          {paper.authors.length > 4 ? " et al." : ""} ·{" "}
          {paper.publishedAt.toISOString().slice(0, 10)} ·{" "}
          <a
            href={`https://arxiv.org/abs/${paper.arxivId}`}
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
          <p className="text-muted-foreground">{paper.abstract}</p>
        )}
      </CardContent>
    </Card>
  );
}
