import { getDb } from "@repo/db/client";
import { papers } from "@repo/db/schema";
import { and, gte, lt, sql } from "drizzle-orm";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PaperCard } from "@/components/paper-card";

export const revalidate = 86_400;

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

export default async function ArchivePage(props: {
  params: Promise<{ year: string; month: string }>;
}) {
  const { year, month } = await props.params;
  const y = Number.parseInt(year, 10);
  const m = Number.parseInt(month, 10);
  if (!Number.isInteger(y) || !Number.isInteger(m) || y < 2024 || y > 2100 || m < 1 || m > 12) {
    notFound();
  }

  const start = new Date(Date.UTC(y, m - 1, 1));
  const end = new Date(Date.UTC(y, m, 1)); // exclusive: first of next month
  const monthName = MONTH_NAMES[m - 1];

  // Prev/next month — pure date math.
  const prev = m === 1 ? { y: y - 1, m: 12 } : { y, m: m - 1 };
  const next = m === 12 ? { y: y + 1, m: 1 } : { y, m: m + 1 };

  const rows = await getDb()
    .select()
    .from(papers)
    .where(and(gte(papers.publishedAt, start), lt(papers.publishedAt, end)))
    .orderBy(sql`${papers.score} desc nulls last`, sql`${papers.publishedAt} desc`)
    .limit(200);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
      <Link
        href="/papers"
        className="mb-6 inline-block text-sm text-muted-foreground hover:underline"
      >
        ← All papers
      </Link>
      <h1 className="mb-2 text-3xl font-semibold tracking-tight">
        {monthName} {y}
      </h1>
      <p className="mb-6 text-sm text-muted-foreground">
        {rows.length} paper{rows.length === 1 ? "" : "s"} published this month, ranked by impact.
      </p>

      <nav className="mb-8 flex items-center justify-between text-sm">
        <Link
          href={`/archive/${prev.y}/${pad2(prev.m)}`}
          className="text-muted-foreground hover:text-foreground hover:underline"
        >
          ← {MONTH_NAMES[prev.m - 1]} {prev.y}
        </Link>
        <Link
          href={`/archive/${next.y}/${pad2(next.m)}`}
          className="text-muted-foreground hover:text-foreground hover:underline"
        >
          {MONTH_NAMES[next.m - 1]} {next.y} →
        </Link>
      </nav>

      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No papers published this month yet.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {rows.map((p) => (
            <PaperCard key={p.id} paper={p} />
          ))}
        </div>
      )}
    </main>
  );
}
