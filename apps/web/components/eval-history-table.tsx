import { readFileSync } from "node:fs";
import { join } from "node:path";

import { EvalHistoryTableClient, type HistoryRow } from "./eval-history-table-client";

function loadHistory(): HistoryRow[] {
  try {
    const path = join(
      process.cwd(),
      "..",
      "..",
      "evals",
      "metrics",
      "history.jsonl",
    );
    const raw = readFileSync(path, "utf-8");
    const rows: HistoryRow[] = [];
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        rows.push(JSON.parse(trimmed) as HistoryRow);
      } catch {
        // skip malformed line — never block the doc render
      }
    }
    rows.sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
    return rows;
  } catch {
    return [];
  }
}

export function EvalHistoryTable() {
  const rows = loadHistory();
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
