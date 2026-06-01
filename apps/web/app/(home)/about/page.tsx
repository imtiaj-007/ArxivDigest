import { readFileSync } from "node:fs";
import { join } from "node:path";
import Link from "next/link";

export const metadata = {
  title: "About — ArxivDigest",
  description:
    "How ArxivDigest works: autonomous daily pipeline summarizing arxiv AI papers on free-tier infrastructure.",
};

type EvalReport = {
  timestamp: string;
  total: number;
  processed: number;
  schema_validity_rate: number;
  avg_keyword_coverage: number;
  classification: { micro_f1: number; macro_f1: number };
};

function loadEvalReport(): EvalReport | null {
  // Read the latest committed eval report at build time. Returns null if the
  // file doesn't exist yet (early in the project) so the page renders cleanly.
  try {
    const path = join(process.cwd(), "..", "..", "evals", "last_report.json");
    return JSON.parse(readFileSync(path, "utf-8")) as EvalReport;
  } catch {
    return null;
  }
}

const PIPELINE: Array<{ stage: string; what: string }> = [
  {
    stage: "crawl",
    what: "Fetch the latest cs.AI / cs.LG / cs.CL submissions from arxiv's Atom API (raw httpx + stdlib XML; UA + 429-retry).",
  },
  {
    stage: "summarize",
    what: "Groq Llama 3.3 70B + instructor → a structured TL;DR: problem, approach, result, why it matters.",
  },
  {
    stage: "classify",
    what: "Llama 3.1 8B assigns 1–3 themes from a 14-theme taxonomy, post-validated against the taxonomy.",
  },
  {
    stage: "embed",
    what: "Local BAAI/bge-large-en-v1.5 (1024d) on CPU → pgvector HNSW index for cosine semantic search.",
  },
  {
    stage: "rank",
    what: "Blend novelty (cosine distance to nearest neighbors) with an LLM-judged impact score → papers.score.",
  },
  {
    stage: "publish",
    what: "Write the daily digest row from the top-K and refresh the site.",
  },
];

const STACK: Array<{ layer: string; tech: string }> = [
  { layer: "Agent", tech: "Python 3.12 · uv · LangGraph · instructor · structlog" },
  { layer: "LLM", tech: "Groq (Llama 3.3 70B + 3.1 8B) · aiolimiter · MultiLLM failover (dormant)" },
  { layer: "Embeddings", tech: "Local BAAI/bge-large-en-v1.5 · sentence-transformers · CPU torch" },
  { layer: "Database", tech: "Supabase Postgres 17 + pgvector (HNSW) · Drizzle ORM" },
  { layer: "Web", tech: "Next.js 16 App Router · Tailwind v4 · shadcn (base-nova) · Fumadocs" },
  { layer: "Compute", tech: "GitHub Actions cron — 07:00 UTC daily" },
  { layer: "Observability", tech: "Langfuse (LLM traces) · Sentry (errors)" },
  { layer: "Hosting", tech: "Vercel (web) · Supabase (DB)" },
];

const COSTS: Array<{ service: string; monthly: string; note: string }> = [
  { service: "Groq inference", monthly: "$0", note: "free tier covers ~50 papers/day with headroom" },
  { service: "Embeddings", monthly: "$0", note: "local model, no API" },
  { service: "Supabase Postgres", monthly: "$0", note: "well under the 500 MB free tier" },
  { service: "GitHub Actions", monthly: "$0", note: "~10 min/day · 2000 min/mo free" },
  { service: "Vercel Hobby", monthly: "$0", note: "low-bandwidth static + ISR" },
  { service: "Langfuse + Sentry", monthly: "$0", note: "free tiers, low volume" },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {children}
    </section>
  );
}

export default function AboutPage() {
  const evalReport = loadEvalReport();

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
      <h1 className="mb-2 text-3xl font-semibold tracking-tight">About</h1>
      <p className="mb-12 text-base text-muted-foreground">
        ArxivDigest is an autonomous daily AI agent that scans new arxiv cs.AI / cs.LG / cs.CL
        submissions, produces structured TL;DRs, classifies them by theme, and ranks them by
        novelty and impact — published every morning, unattended, at $0/month.
      </p>

      <Section title="How it works">
        <ol className="space-y-3">
          {PIPELINE.map((s, i) => (
            <li key={s.stage} className="grid grid-cols-[2rem_8rem_1fr] gap-3 text-sm">
              <span className="text-muted-foreground tabular-nums">{i + 1}.</span>
              <span className="font-mono text-xs font-medium uppercase tracking-wide text-foreground/90">
                {s.stage}
              </span>
              <span className="text-foreground/90">{s.what}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-xs text-muted-foreground">
          Each stage is idempotent and reads its own pending work from the database
          (<code className="rounded bg-muted px-1 py-0.5 text-[0.7rem]">X IS NULL</code>),
          so re-running the LangGraph after a crash resumes exactly where it left off — the
          DB status columns <em>are</em> the checkpoint.
        </p>
      </Section>

      {evalReport && (
        <Section title="Quality">
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Metric</th>
                  <th className="px-3 py-2 text-right font-medium">Score</th>
                  <th className="px-3 py-2 text-left font-medium">What it measures</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-border">
                  <td className="px-3 py-2">Classification F1 (micro)</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {evalReport.classification.micro_f1.toFixed(3)}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    multi-label theme agreement vs human labels, pooled over all (paper, theme) pairs
                  </td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-3 py-2">Classification F1 (macro)</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {evalReport.classification.macro_f1.toFixed(3)}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    per-theme F1 averaged, so weak themes get equal weight to popular ones
                  </td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-3 py-2">Schema validity</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {(evalReport.schema_validity_rate * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    fraction of LLM calls that produced a valid Pydantic object
                  </td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-3 py-2">Summary keyword coverage</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {(evalReport.avg_keyword_coverage * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    fraction of expected keywords (per human label) found in the generated summary
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Measured on {evalReport.processed}/{evalReport.total} ground-truth papers, hand-labeled in{" "}
            <a
              className="underline"
              href="https://github.com/imtiaj-007/ArxivDigest/blob/main/evals/ground_truth.jsonl"
              target="_blank"
              rel="noopener noreferrer"
            >
              evals/ground_truth.jsonl
            </a>
            . Last run {new Date(evalReport.timestamp).toISOString().slice(0, 10)}; regenerated by the
            daily cron via the{" "}
            <Link href="/docs/methodology" className="underline">
              eval harness
            </Link>
            .
          </p>
        </Section>
      )}

      <Section title="Stack">
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <tbody>
              {STACK.map((row) => (
                <tr key={row.layer} className="border-t border-border first:border-t-0">
                  <th className="w-32 px-3 py-2 text-left font-medium text-muted-foreground">
                    {row.layer}
                  </th>
                  <td className="px-3 py-2 text-foreground/90">{row.tech}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Cost ledger">
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Service</th>
                <th className="px-3 py-2 text-right font-medium">Monthly</th>
                <th className="px-3 py-2 text-left font-medium">Notes</th>
              </tr>
            </thead>
            <tbody>
              {COSTS.map((row) => (
                <tr key={row.service} className="border-t border-border">
                  <td className="px-3 py-2">{row.service}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">{row.monthly}</td>
                  <td className="px-3 py-2 text-muted-foreground">{row.note}</td>
                </tr>
              ))}
              <tr className="border-t border-border bg-muted/30 font-medium">
                <td className="px-3 py-2">Total</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">$0/mo</td>
                <td className="px-3 py-2 text-muted-foreground">
                  Free tiers, no payment methods, no surprises.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Explore">
        <ul className="space-y-2 text-sm">
          <li>
            <Link className="font-medium hover:underline" href="/papers">
              /papers
            </Link>
            <span className="text-muted-foreground"> — the latest ranked digest</span>
          </li>
          <li>
            <Link className="font-medium hover:underline" href="/status">
              /status
            </Link>
            <span className="text-muted-foreground"> — last 30 days of agent runs</span>
          </li>
          <li>
            <a
              className="font-medium hover:underline"
              href="https://github.com/imtiaj-007/ArxivDigest"
              target="_blank"
              rel="noopener noreferrer"
            >
              source on GitHub
            </a>
          </li>
        </ul>
      </Section>
    </main>
  );
}
