"use client";

import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";

export type HistoryRow = {
  timestamp: string;
  git_sha: string | null;
  processed: number;
  total: number;
  schema_validity_rate: number;
  micro_f1: number;
  macro_f1: number;
  avg_keyword_coverage: number;
};

type SortKey =
  | "timestamp"
  | "micro_f1"
  | "macro_f1"
  | "schema_validity_rate"
  | "avg_keyword_coverage";

const FLOORS: Record<Exclude<SortKey, "timestamp">, number> = {
  micro_f1: 0.8,
  macro_f1: 0.8,
  schema_validity_rate: 0.95,
  avg_keyword_coverage: 0.65,
};

const PAGE_SIZE = 25;

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function fmtTs(iso: string): string {
  return `${iso.slice(0, 16).replace("T", " ")}Z`;
}

function metricClass(key: keyof typeof FLOORS, v: number): string {
  return v >= FLOORS[key]
    ? "text-emerald-600 dark:text-emerald-400"
    : "text-amber-600 dark:text-amber-400";
}

function ghShaHref(sha: string | null): string | null {
  if (!sha) return null;
  return `https://github.com/imtiaj-007/ArxivDigest/commit/${sha}`;
}

export function EvalHistoryTableClient({ rows }: { rows: HistoryRow[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const out = [...rows];
    out.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === bv) return 0;
      const cmp = av < bv ? -1 : 1;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return out;
  }, [rows, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const visible = sorted.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir(key === "timestamp" ? "desc" : "desc");
    }
    setPage(0);
  }

  const headers: Array<{ key: SortKey; label: string; align: "left" | "right" }> = [
    { key: "timestamp", label: "When", align: "left" },
    { key: "micro_f1", label: "Micro F1", align: "right" },
    { key: "macro_f1", label: "Macro F1", align: "right" },
    { key: "schema_validity_rate", label: "Schema", align: "right" },
    { key: "avg_keyword_coverage", label: "Kw cov", align: "right" },
  ];

  return (
    <div className="my-6">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-fd-border text-xs uppercase tracking-wide text-fd-muted-foreground">
              {headers.map((h) => (
                <th
                  key={h.key}
                  className={`px-4 py-2 font-medium ${
                    h.align === "right" ? "text-right" : "text-left"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => toggleSort(h.key)}
                    className={`inline-flex items-center gap-1 transition hover:text-fd-foreground ${
                      h.align === "right" ? "flex-row-reverse" : ""
                    }`}
                  >
                    {h.label}
                    {sortKey === h.key ? (
                      sortDir === "asc" ? (
                        <ArrowUp className="size-3" />
                      ) : (
                        <ArrowDown className="size-3" />
                      )
                    ) : (
                      <ArrowUpDown className="size-3 opacity-40" />
                    )}
                  </button>
                </th>
              ))}
              <th className="px-4 py-2 text-right font-medium">Papers</th>
              <th className="px-4 py-2 text-right font-medium">Commit</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => {
              const href = ghShaHref(r.git_sha);
              return (
                <tr
                  key={`${r.timestamp}-${i}`}
                  className="border-b border-fd-border/60 last:border-b-0 hover:bg-fd-background/30"
                >
                  <td className="px-4 py-2 font-mono text-xs text-fd-muted-foreground">
                    {fmtTs(r.timestamp)}
                  </td>
                  <td
                    className={`px-4 py-2 text-right font-mono ${metricClass(
                      "micro_f1",
                      r.micro_f1,
                    )}`}
                  >
                    {fmtPct(r.micro_f1)}
                  </td>
                  <td
                    className={`px-4 py-2 text-right font-mono ${metricClass(
                      "macro_f1",
                      r.macro_f1,
                    )}`}
                  >
                    {fmtPct(r.macro_f1)}
                  </td>
                  <td
                    className={`px-4 py-2 text-right font-mono ${metricClass(
                      "schema_validity_rate",
                      r.schema_validity_rate,
                    )}`}
                  >
                    {fmtPct(r.schema_validity_rate)}
                  </td>
                  <td
                    className={`px-4 py-2 text-right font-mono ${metricClass(
                      "avg_keyword_coverage",
                      r.avg_keyword_coverage,
                    )}`}
                  >
                    {fmtPct(r.avg_keyword_coverage)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-fd-muted-foreground">
                    {r.processed}/{r.total}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs">
                    {href ? (
                      <a
                        href={href}
                        target="_blank"
                        rel="noreferrer"
                        className="text-fd-primary hover:underline"
                      >
                        {r.git_sha?.slice(0, 7)}
                      </a>
                    ) : (
                      <span className="text-fd-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="mt-2 flex items-center justify-between gap-2 text-xs text-fd-muted-foreground">
          <div>
            Page {safePage + 1} of {totalPages}
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setPage(Math.max(0, safePage - 1))}
              disabled={safePage === 0}
              className="inline-flex items-center gap-1 rounded-md border border-fd-border bg-fd-background px-2 py-1 transition hover:bg-fd-accent disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="size-3" />
              Prev
            </button>
            <button
              type="button"
              onClick={() => setPage(Math.min(totalPages - 1, safePage + 1))}
              disabled={safePage >= totalPages - 1}
              className="inline-flex items-center gap-1 rounded-md border border-fd-border bg-fd-background px-2 py-1 transition hover:bg-fd-accent disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
              <ChevronRight className="size-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
