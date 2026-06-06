import { getDb } from "@repo/db/client";
import { papers } from "@repo/db/schema";
import { sql } from "drizzle-orm";

import { parseSummary } from "@/lib/papers";
import { SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "@/lib/site";

// Render on demand — Next tries to prerender any route without explicit
// dynamic + the build server has no DATABASE_URL, so without this CI fails.
// Freshness comes from the Cache-Control header below: Vercel's edge CDN
// caches the response for 1 hour and serves stale for up to a day while
// revalidating in the background, so readers still only hit the DB ~once
// per hour even though the route itself is dynamic.
export const dynamic = "force-dynamic";

const FEED_PATH = "/feed.xml";
const ITEM_LIMIT = 50;

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function cdata(html: string): string {
  // The closing ]]> is the one sequence forbidden inside a CDATA section; the
  // canonical workaround splits it across two sections so readers reassemble
  // the original bytes.
  return `<![CDATA[${html.replace(/]]>/g, "]]]]><![CDATA[>")}]]>`;
}

type PaperRow = {
  arxivId: string;
  title: string;
  abstract: string;
  summary: string | null;
  authors: string[] | null;
  themes: string[] | null;
  publishedAt: Date;
};

function renderItemDescription(row: PaperRow): string {
  const structured = parseSummary(row.summary);
  const parts: string[] = [];
  if (structured) {
    parts.push(
      `<p><strong>Problem.</strong> ${escapeXml(structured.problem)}</p>`,
      `<p><strong>Approach.</strong> ${escapeXml(structured.approach)}</p>`,
      `<p><strong>Result.</strong> ${escapeXml(structured.result)}</p>`,
      `<p><strong>Why it matters.</strong> ${escapeXml(structured.why_it_matters)}</p>`,
    );
  } else if (row.summary) {
    parts.push(`<p>${escapeXml(row.summary)}</p>`);
  } else {
    parts.push(`<p>${escapeXml(row.abstract.slice(0, 600))}</p>`);
  }
  if (row.themes && row.themes.length > 0) {
    parts.push(
      `<p><em>Themes: ${row.themes.map((t) => escapeXml(t)).join(", ")}</em></p>`,
    );
  }
  return cdata(parts.join(""));
}

function renderItem(row: PaperRow): string {
  const link = `${SITE_URL}/papers/${encodeURIComponent(row.arxivId)}`;
  const authorLine =
    row.authors && row.authors.length > 0
      ? `      <dc:creator>${escapeXml(row.authors.join(", "))}</dc:creator>`
      : "";
  const categoryLines = (row.themes ?? [])
    .map((t) => `      <category>${escapeXml(t)}</category>`)
    .join("\n");
  return `    <item>
      <title>${escapeXml(row.title)}</title>
      <link>${link}</link>
      <guid isPermaLink="false">arxiv:${escapeXml(row.arxivId)}</guid>
      <pubDate>${row.publishedAt.toUTCString()}</pubDate>
${authorLine ? `${authorLine}\n` : ""}${categoryLines ? `${categoryLines}\n` : ""}      <description>${renderItemDescription(row)}</description>
    </item>`;
}

export async function GET() {
  const rows = (await getDb()
    .select({
      arxivId: papers.arxivId,
      title: papers.title,
      abstract: papers.abstract,
      summary: papers.summary,
      authors: papers.authors,
      themes: papers.themes,
      publishedAt: papers.publishedAt,
    })
    .from(papers)
    .where(sql`${papers.summary} is not null`)
    .orderBy(sql`${papers.score} desc nulls last`, sql`${papers.publishedAt} desc`)
    .limit(ITEM_LIMIT)) as PaperRow[];

  const lastBuild =
    rows.length > 0 ? rows[0]!.publishedAt.toUTCString() : new Date().toUTCString();

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>${escapeXml(SITE_NAME)}</title>
    <link>${SITE_URL}</link>
    <atom:link href="${SITE_URL}${FEED_PATH}" rel="self" type="application/rss+xml" />
    <description>${escapeXml(SITE_DESCRIPTION)}</description>
    <language>en</language>
    <lastBuildDate>${lastBuild}</lastBuildDate>
    <generator>ArxivDigest / Next.js route handler</generator>
${rows.map(renderItem).join("\n")}
  </channel>
</rss>
`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
