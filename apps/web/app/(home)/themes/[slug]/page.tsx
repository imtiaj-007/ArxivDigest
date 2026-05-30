import { getDb } from "@repo/db/client";
import { papers } from "@repo/db/schema";
import { arrayContains, sql } from "drizzle-orm";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PaperCard } from "@/components/paper-card";
import { THEME_BY_SLUG } from "@/lib/themes";

export const revalidate = 86_400;

export default async function ThemePage(props: { params: Promise<{ slug: string }> }) {
  const { slug } = await props.params;
  const theme = THEME_BY_SLUG.get(slug);
  if (!theme) notFound();

  const rows = await getDb()
    .select()
    .from(papers)
    .where(arrayContains(papers.themes, [slug]))
    .orderBy(sql`${papers.score} desc nulls last`, sql`${papers.publishedAt} desc`)
    .limit(50);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
      <Link
        href="/papers"
        className="mb-6 inline-block text-sm text-muted-foreground hover:underline"
      >
        ← All papers
      </Link>
      <h1 className="mb-1 text-3xl font-semibold tracking-tight">{theme.name}</h1>
      <p className="mb-2 text-sm font-mono text-muted-foreground">{theme.slug}</p>
      <p className="mb-8 text-sm text-muted-foreground">{theme.description}</p>
      <p className="mb-6 text-sm text-muted-foreground">
        {rows.length} paper{rows.length === 1 ? "" : "s"} tagged this theme, ranked by impact.
      </p>

      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No papers tagged this theme yet.
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
