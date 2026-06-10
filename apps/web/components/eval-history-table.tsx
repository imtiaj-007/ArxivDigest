import { getDb } from "@repo/db/client";
import { evalRuns } from "@repo/db/schema";
import { desc } from "drizzle-orm";

import { EvalHistoryTableClient, type HistoryRow } from "./eval-history-table-client";

const HISTORY_LIMIT = 365;

async function loadHistory(): Promise<HistoryRow[]> {
  try {
    const rows = await getDb()
      .select({
        ranAt: evalRuns.ranAt,
        gitSha: evalRuns.gitSha,
        processed: evalRuns.processed,
        total: evalRuns.total,
        microF1: evalRuns.microF1,
        macroF1: evalRuns.macroF1,
        schemaValidityRate: evalRuns.schemaValidityRate,
        avgKeywordCoverage: evalRuns.avgKeywordCoverage,
        perThemeF1: evalRuns.perThemeF1,
      })
      .from(evalRuns)
      .orderBy(desc(evalRuns.ranAt))
      .limit(HISTORY_LIMIT);

    return rows.map<HistoryRow>((r) => ({
      timestamp: r.ranAt.toISOString(),
      git_sha: r.gitSha,
      processed: r.processed,
      total: r.total,
      micro_f1: r.microF1,
      macro_f1: r.macroF1,
      schema_validity_rate: r.schemaValidityRate,
      avg_keyword_coverage: r.avgKeywordCoverage,
      per_theme_f1: r.perThemeF1 as Record<string, number> | undefined,
    }));
  } catch {
    // DB unavailable (build-time CI without DATABASE_URL, transient outage) →
    // render the empty-state instead of failing the page render.
    return [];
  }
}

export async function EvalHistoryTable() {
  const rows = await loadHistory();
  if (rows.length === 0) {
    return (
      <div className="my-6 rounded-lg border border-dashed border-fd-border bg-fd-card p-6 text-sm text-fd-muted-foreground">
        No history yet. After the first <code>arxivdigest eval</code> run
        the rows will appear here, newest first.
      </div>
    );
  }
  return <EvalHistoryTableClient rows={rows} />;
}
