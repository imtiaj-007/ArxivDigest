"use client";

import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
} from "lucide-react";
import { Fragment, useMemo, useState } from "react";

export type HistoryRow = {
  timestamp: string;
  git_sha: string | null;
  processed: number;
  total: number;
  schema_validity_rate: number;
  micro_f1: number;
  macro_f1: number;
  avg_keyword_coverage: number;
  // Optional — older rows (pre-2026-06-06) won't have this field.
  per_theme_f1?: Record<string, number>;
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

function themeChipColor(f1: number): string {
  if (f1 >= 0.85) return "text-emerald-600 dark:text-emerald-400";
  if (f1 >= 0.75) return "text-fd-foreground";
  return "text-amber-600 dark:text-amber-400";
}

type SparklineSeries = {
  label: string;
  values: number[];
  color: string;
  endValue: number;
};

function Sparkline({ rows }: { rows: HistoryRow[] }) {
  // rows are chronological (oldest → newest) for the line direction.
  const ordered = [...rows].sort((a, b) => (a.timestamp < b.timestamp ? -1 : 1));
  if (ordered.length < 2) return null;
  const first = ordered[0];
  const last = ordered[ordered.length - 1];
  if (!first || !last) return null;

  const series: SparklineSeries[] = [
    {
      label: "Micro F1",
      values: ordered.map((r) => r.micro_f1),
      color: "stroke-emerald-500 dark:stroke-emerald-400",
      endValue: last.micro_f1,
    },
    {
      label: "Macro F1",
      values: ordered.map((r) => r.macro_f1),
      color: "stroke-sky-500 dark:stroke-sky-400",
      endValue: last.macro_f1,
    },
  ];

  const width = 480;
  const height = 80;
  const padX = 8;
  const padY = 12;
  const yMin = 0.6;
  const yMax = 1.0;

  function scaleX(i: number): number {
    if (ordered.length === 1) return padX;
    return padX + ((width - padX * 2) * i) / (ordered.length - 1);
  }
  function scaleY(v: number): number {
    const clamped = Math.max(yMin, Math.min(yMax, v));
    return padY + (height - padY * 2) * (1 - (clamped - yMin) / (yMax - yMin));
  }
  function path(values: number[]): string {
    return values
      .map((v, i) => `${i === 0 ? "M" : "L"}${scaleX(i).toFixed(1)},${scaleY(v).toFixed(1)}`)
      .join(" ");
  }

  const floorY = scaleY(FLOORS.micro_f1);

  return (
    <div className="mb-4 rounded-md border border-fd-border bg-fd-card/40 px-3 py-2">
      <div className="mb-1 flex items-baseline justify-between text-xs text-fd-muted-foreground">
        <span>Trend ({ordered.length} run{ordered.length === 1 ? "" : "s"}, oldest → newest)</span>
        <span className="flex items-center gap-3">
          {series.map((s) => (
            <span key={s.label} className="inline-flex items-center gap-1">
              <span
                aria-hidden
                className={`inline-block h-0.5 w-3 ${s.color.replace("stroke-", "bg-")}`}
              />
              <span>
                {s.label} <span className="font-mono">{fmtPct(s.endValue)}</span>
              </span>
            </span>
          ))}
        </span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-16 w-full"
        preserveAspectRatio="none"
        role="img"
        aria-label="Eval F1 trend over time"
      >
        <line
          x1={padX}
          x2={width - padX}
          y1={floorY}
          y2={floorY}
          className="stroke-fd-muted-foreground/40"
          strokeWidth={1}
          strokeDasharray="3 3"
        />
        {series.map((s) => (
          <Fragment key={s.label}>
            <path
              d={path(s.values)}
              fill="none"
              className={s.color}
              strokeWidth={1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            <circle
              cx={scaleX(s.values.length - 1)}
              cy={scaleY(s.endValue)}
              r={2.5}
              className={s.color.replace("stroke-", "fill-")}
            />
          </Fragment>
        ))}
      </svg>
      <div className="mt-0.5 flex justify-between text-[0.65rem] text-fd-muted-foreground">
        <span>{fmtTs(first.timestamp)}</span>
        <span>floor {fmtPct(FLOORS.micro_f1)}</span>
        <span>{fmtTs(last.timestamp)}</span>
      </div>
    </div>
  );
}

function PerThemeRow({ row, colSpan }: { row: HistoryRow; colSpan: number }) {
  const entries = Object.entries(row.per_theme_f1 ?? {}).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) {
    return (
      <tr>
        <td colSpan={colSpan} className="bg-fd-background/30 px-4 py-2 text-xs text-fd-muted-foreground">
          No per-theme breakdown recorded for this run (predates the JSONL
          schema update on 2026-06-06).
        </td>
      </tr>
    );
  }
  return (
    <tr>
      <td colSpan={colSpan} className="bg-fd-background/30 px-4 py-2">
        <div className="mb-1 text-[0.65rem] uppercase tracking-wide text-fd-muted-foreground">
          Per-theme F1 (sorted desc)
        </div>
        <div className="flex flex-wrap gap-1.5">
          {entries.map(([theme, f1]) => (
            <span
              key={theme}
              className="inline-flex items-center gap-1.5 rounded-md border border-fd-border bg-fd-card px-2 py-1 font-mono text-[0.7rem]"
              title={`F1 = ${f1.toFixed(3)}`}
            >
              <span className="text-fd-muted-foreground">{theme}</span>
              <span className={themeChipColor(f1)}>{f1.toFixed(2)}</span>
            </span>
          ))}
        </div>
      </td>
    </tr>
  );
}

export function EvalHistoryTableClient({ rows }: { rows: HistoryRow[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

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
      setSortDir("desc");
    }
    setPage(0);
  }

  function toggleExpand(rowKey: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(rowKey)) next.delete(rowKey);
      else next.add(rowKey);
      return next;
    });
  }

  const headers: Array<{ key: SortKey; label: string; align: "left" | "right" }> = [
    { key: "timestamp", label: "When", align: "left" },
    { key: "micro_f1", label: "Micro F1", align: "right" },
    { key: "macro_f1", label: "Macro F1", align: "right" },
    { key: "schema_validity_rate", label: "Schema", align: "right" },
    { key: "avg_keyword_coverage", label: "Kw cov", align: "right" },
  ];
  // 1 expand chevron + 5 metric headers + Papers + Commit = 8 cols
  const totalCols = headers.length + 3;

  return (
    <div className="my-6">
      <Sparkline rows={sorted} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-fd-border text-xs uppercase tracking-wide text-fd-muted-foreground">
              <th className="w-8 px-2 py-2" aria-label="expand row" />
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
              const rowKey = `${r.timestamp}-${i}`;
              const isOpen = expanded.has(rowKey);
              return (
                <Fragment key={rowKey}>
                  <tr className="border-b border-fd-border/60 hover:bg-fd-background/30">
                    <td className="px-2 py-2">
                      <button
                        type="button"
                        onClick={() => toggleExpand(rowKey)}
                        className="inline-flex size-5 items-center justify-center rounded text-fd-muted-foreground transition hover:bg-fd-accent hover:text-fd-foreground"
                        aria-label={isOpen ? "Hide per-theme breakdown" : "Show per-theme breakdown"}
                        aria-expanded={isOpen}
                      >
                        {isOpen ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
                      </button>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-fd-muted-foreground">
                      {fmtTs(r.timestamp)}
                    </td>
                    <td className={`px-4 py-2 text-right font-mono ${metricClass("micro_f1", r.micro_f1)}`}>
                      {fmtPct(r.micro_f1)}
                    </td>
                    <td className={`px-4 py-2 text-right font-mono ${metricClass("macro_f1", r.macro_f1)}`}>
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
                  {isOpen && <PerThemeRow row={r} colSpan={totalCols} />}
                </Fragment>
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
