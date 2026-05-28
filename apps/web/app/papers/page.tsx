import { getDb } from "@repo/db/client";
import { papers } from "@repo/db/schema";
import { desc } from "drizzle-orm";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default async function PapersPage() {
  const rows = await getDb()
    .select()
    .from(papers)
    .orderBy(desc(papers.createdAt))
    .limit(50);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
      <h1 className="mb-2 text-3xl font-semibold tracking-tight">Papers</h1>
      <p className="mb-8 text-sm text-muted-foreground">
        {rows.length} paper{rows.length === 1 ? "" : "s"} in the database.
      </p>

      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No papers yet. Run <code>arxivdigest seed-demo</code> from the agent.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {rows.map((p) => (
            <Card key={p.id}>
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  {p.categories.map((c) => (
                    <Badge key={c} variant="secondary">
                      {c}
                    </Badge>
                  ))}
                  {p.score != null && (
                    <Badge variant="outline">score {p.score.toFixed(2)}</Badge>
                  )}
                </div>
                <CardTitle className="mt-2">{p.title}</CardTitle>
                <CardDescription>
                  {p.authors.join(", ")} · {p.arxivId}
                </CardDescription>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {p.summary ?? p.abstract}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
