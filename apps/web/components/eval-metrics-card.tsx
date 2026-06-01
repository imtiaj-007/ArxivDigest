import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Activity, CheckCircle2, Sparkles, TrendingUp } from "lucide-react";

type EvalReport = {
  timestamp: string;
  total: number;
  processed: number;
  schema_validity_rate: number;
  avg_keyword_coverage: number;
  classification: { micro_f1: number; macro_f1: number };
  per_theme_f1?: Record<string, number>;
};

function loadEvalReport(): EvalReport | null {
  try {
    const path = join(process.cwd(), "..", "..", "evals", "last_report.json");
    return JSON.parse(readFileSync(path, "utf-8")) as EvalReport;
  } catch {
    return null;
  }
}

const FLOORS = {
  micro_f1: 0.8,
  macro_f1: 0.8,
  schema_validity_rate: 0.95,
  avg_keyword_coverage: 0.65,
};

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function statusFor(metric: keyof typeof FLOORS, value: number): "ok" | "low" {
  return value >= FLOORS[metric] ? "ok" : "low";
}

export function EvalMetricsCard() {
  const report = loadEvalReport();
  if (!report) {
    return (
      <div className="my-6 rounded-lg border border-dashed border-fd-border bg-fd-card p-6 text-sm text-fd-muted-foreground">
        No eval report yet. After the first <code>arxivdigest eval</code> run
        the latest metrics will appear here.
      </div>
    );
  }

  const ts = new Date(report.timestamp);
  const metrics: Array<{
    label: string;
    value: number;
    floor: number;
    key: keyof typeof FLOORS;
    icon: React.ComponentType<{ className?: string }>;
  }> = [
    {
      label: "Micro F1",
      value: report.classification.micro_f1,
      floor: FLOORS.micro_f1,
      key: "micro_f1",
      icon: TrendingUp,
    },
    {
      label: "Macro F1",
      value: report.classification.macro_f1,
      floor: FLOORS.macro_f1,
      key: "macro_f1",
      icon: Activity,
    },
    {
      label: "Schema validity",
      value: report.schema_validity_rate,
      floor: FLOORS.schema_validity_rate,
      key: "schema_validity_rate",
      icon: CheckCircle2,
    },
    {
      label: "Keyword coverage",
      value: report.avg_keyword_coverage,
      floor: FLOORS.avg_keyword_coverage,
      key: "avg_keyword_coverage",
      icon: Sparkles,
    },
  ];

  const perTheme = report.per_theme_f1
    ? Object.entries(report.per_theme_f1).sort((a, b) => b[1] - a[1])
    : [];

  return (
    <div className="my-6 rounded-lg border border-fd-border bg-fd-card">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-fd-border px-4 py-3">
        <div className="text-sm font-medium">Latest eval run</div>
        <div className="text-xs text-fd-muted-foreground">
          {report.processed}/{report.total} papers ·{" "}
          {ts.toISOString().slice(0, 16).replace("T", " ")}Z
        </div>
      </div>
      <div className="grid grid-cols-2 gap-px bg-fd-border sm:grid-cols-4">
        {metrics.map(({ label, value, floor, key, icon: Icon }) => {
          const status = statusFor(key, value);
          return (
            <div key={label} className="flex flex-col bg-fd-card p-4">
              <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-fd-muted-foreground">
                <Icon className="size-3.5" />
                {label}
              </div>
              <div
                className={`mt-2 font-mono text-2xl font-semibold ${
                  status === "ok"
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-amber-600 dark:text-amber-400"
                }`}
              >
                {fmtPct(value)}
              </div>
              <div className="mt-1 text-[0.7rem] text-fd-muted-foreground">
                floor {fmtPct(floor)}
              </div>
            </div>
          );
        })}
      </div>
      {perTheme.length > 0 && (
        <div className="border-t border-fd-border px-4 py-3">
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-fd-muted-foreground">
            Per-theme F1
          </div>
          <div className="flex flex-wrap gap-1.5">
            {perTheme.map(([theme, f1]) => (
              <span
                key={theme}
                className="inline-flex items-center gap-1.5 rounded-md border border-fd-border bg-fd-background px-2 py-1 font-mono text-[0.7rem]"
                title={`F1 = ${f1.toFixed(3)}`}
              >
                <span className="text-fd-muted-foreground">{theme}</span>
                <span
                  className={
                    f1 >= 0.85
                      ? "text-emerald-600 dark:text-emerald-400"
                      : f1 >= 0.75
                        ? "text-fd-foreground"
                        : "text-amber-600 dark:text-amber-400"
                  }
                >
                  {f1.toFixed(2)}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
