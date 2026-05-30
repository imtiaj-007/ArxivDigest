import { getDb } from "@repo/db/client";
import { papers } from "@repo/db/schema";
import { sql } from "drizzle-orm";
import { PaperCard } from "@/components/paper-card";

export const dynamic = "force-dynamic";

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
          {rows.map((p) => (
            <PaperCard key={p.id} paper={p} />
          ))}
        </div>
      )}
    </main>
  );
}
