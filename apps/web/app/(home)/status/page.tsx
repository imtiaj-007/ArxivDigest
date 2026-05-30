import { getDb } from "@repo/db/client";
import { runs, type Run } from "@repo/db/schema";
import { desc, gte } from "drizzle-orm";

export const dynamic = "force-dynamic";

const DAYS = 30;
const STATUS_ORDER: Record<string, number> = {
  failed: 3,
  running: 2,
  completed: 1,
  none: 0,
};

type DayStatus = "failed" | "running" | "completed" | "none";

function dayKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function pickWorst(rs: readonly Run[]): DayStatus {
  if (rs.length === 0) return "none";
  let worst: DayStatus = "completed";
  for (const r of rs) {
    const s = r.status as DayStatus;
    if ((STATUS_ORDER[s] ?? 0) > (STATUS_ORDER[worst] ?? 0)) worst = s;
  }
  return worst;
}

function DaySquare({ status, label }: { status: DayStatus; label: string }) {
  const color = {
    failed: "bg-destructive",
    running: "bg-yellow-500",
    completed: "bg-emerald-500",
    none: "bg-muted",
  }[status];
  return (
    <span
      title={label}
      className={`inline-block h-4 w-4 rounded-sm ${color}`}
      aria-label={label}
    />
  );
}

function StatusPill({ status }: { status: string }) {
  const styles =
    {
      completed: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
      failed: "bg-destructive/15 text-destructive",
      running: "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400",
    }[status] ?? "bg-muted text-muted-foreground";
  return (
    <span
      className={`inline-flex h-5 items-center rounded-full px-2 text-xs font-medium ${styles}`}
    >
      {status}
    </span>
  );
}

function formatDuration(start: Date, end: Date | null): string {
  if (!end) return "—";
  const s = Math.round((end.getTime() - start.getTime()) / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r ? `${m}m ${r}s` : `${m}m`;
}

export default async function StatusPage() {
  const since = new Date(Date.now() - DAYS * 86_400_000);
  const rows = await getDb()
    .select()
    .from(runs)
    .where(gte(runs.startedAt, since))
    .orderBy(desc(runs.startedAt));

  // Bucket runs by UTC day for the grid.
  const byDay = new Map<string, Run[]>();
  for (const r of rows) {
    const k = dayKey(r.startedAt);
    const list = byDay.get(k);
    if (list) list.push(r);
    else byDay.set(k, [r]);
  }

  const today = new Date();
  const grid: Array<{ key: string; status: DayStatus; count: number }> = [];
  for (let i = DAYS - 1; i >= 0; i--) {
    const d = new Date(today.getTime() - i * 86_400_000);
    const k = dayKey(d);
    const dayRuns = byDay.get(k) ?? [];
    grid.push({ key: k, status: pickWorst(dayRuns), count: dayRuns.length });
  }

  const recent = rows.slice(0, 10);
  const counts = {
    total: rows.length,
    completed: rows.filter((r) => r.status === "completed").length,
    failed: rows.filter((r) => r.status === "failed").length,
  };

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
      <h1 className="mb-2 text-3xl font-semibold tracking-tight">Status</h1>
      <p className="mb-8 text-sm text-muted-foreground">
        {counts.total} run{counts.total === 1 ? "" : "s"} in the last {DAYS} days
        {counts.total > 0 && (
          <>
            : <span className="text-emerald-600 dark:text-emerald-400">{counts.completed} completed</span>,{" "}
            <span className="text-destructive">{counts.failed} failed</span>
          </>
        )}
        .
      </p>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted-foreground">
          Last {DAYS} days
        </h2>
        <div className="flex flex-wrap gap-1">
          {grid.map((d) => (
            <DaySquare
              key={d.key}
              status={d.status}
              label={`${d.key}: ${d.status}${d.count > 1 ? ` (${d.count} runs)` : ""}`}
            />
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm bg-emerald-500" /> completed
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm bg-yellow-500" /> running
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm bg-destructive" /> failed
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm bg-muted" /> none
          </span>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted-foreground">
          Recent runs
        </h2>
        {recent.length === 0 ? (
          <p className="text-sm text-muted-foreground">No runs recorded yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Started (UTC)</th>
                  <th className="px-3 py-2 text-left font-medium">Status</th>
                  <th className="px-3 py-2 text-right font-medium">Duration</th>
                  <th className="px-3 py-2 text-right font-medium">Crawled</th>
                  <th className="px-3 py-2 text-right font-medium">Ranked</th>
                  <th className="px-3 py-2 text-right font-medium">Published</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((r) => (
                  <tr key={r.id} className="border-t border-border">
                    <td className="px-3 py-2 font-mono text-xs">
                      {r.startedAt.toISOString().replace("T", " ").slice(0, 19)}
                    </td>
                    <td className="px-3 py-2">
                      <StatusPill status={r.status} />
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {formatDuration(r.startedAt, r.completedAt)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{r.papersCrawled}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{r.papersRanked}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{r.papersPublished}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
