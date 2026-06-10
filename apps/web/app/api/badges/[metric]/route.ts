import { getDb } from "@repo/db/client";
import { evalRuns } from "@repo/db/schema";
import { desc } from "drizzle-orm";

// shields.io endpoint badges fetch this URL, expect schemaVersion=1, and render
// the returned label/message/color combo. See
// https://shields.io/badges/endpoint-badge
//
// README badge URLs swapped from
//   img.shields.io/badge/dynamic/json?...&url=raw.githubusercontent.com/.../last_report.json
// to
//   img.shields.io/endpoint?url=https://arxiv-digest-preview.vercel.app/api/badges/micro-f1
// so the badge no longer depends on the JSONL-in-git file we just retired.

export const dynamic = "force-dynamic";

type Endpoint = {
  schemaVersion: 1;
  label: string;
  message: string;
  color: string;
  cacheSeconds?: number;
};

type MetricSpec = {
  label: string;
  floor: number;
  // Pull the value out of the latest eval_runs row.
  pick: (row: {
    microF1: number;
    macroF1: number;
    schemaValidityRate: number;
    avgKeywordCoverage: number;
  }) => number;
};

const METRICS: Record<string, MetricSpec> = {
  "micro-f1": {
    label: "micro F1",
    floor: 0.8,
    pick: (r) => r.microF1,
  },
  "macro-f1": {
    label: "macro F1",
    floor: 0.8,
    pick: (r) => r.macroF1,
  },
  "schema-validity": {
    label: "schema validity",
    floor: 0.95,
    pick: (r) => r.schemaValidityRate,
  },
  "kw-coverage": {
    label: "kw coverage",
    floor: 0.65,
    pick: (r) => r.avgKeywordCoverage,
  },
};

function fmt(value: number): string {
  return value.toFixed(3);
}

function colorFor(value: number, floor: number): string {
  if (value >= floor + 0.05) return "brightgreen";
  if (value >= floor) return "green";
  if (value >= floor - 0.05) return "yellow";
  return "red";
}

function jsonResponse(body: Endpoint): Response {
  return new Response(JSON.stringify(body), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      // shields.io respects this for its own cache. 5 min keeps badges
      // reasonably fresh without hammering the DB on every README impression.
      "Cache-Control": "public, s-maxage=300, stale-while-revalidate=3600",
    },
  });
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ metric: string }> },
): Promise<Response> {
  const { metric } = await context.params;
  const spec = METRICS[metric];
  if (!spec) {
    return jsonResponse({
      schemaVersion: 1,
      label: "eval",
      message: "unknown metric",
      color: "lightgrey",
    });
  }

  try {
    const rows = await getDb()
      .select({
        microF1: evalRuns.microF1,
        macroF1: evalRuns.macroF1,
        schemaValidityRate: evalRuns.schemaValidityRate,
        avgKeywordCoverage: evalRuns.avgKeywordCoverage,
      })
      .from(evalRuns)
      .orderBy(desc(evalRuns.ranAt))
      .limit(1);

    const row = rows[0];
    if (!row) {
      return jsonResponse({
        schemaVersion: 1,
        label: spec.label,
        message: "no data",
        color: "lightgrey",
      });
    }

    const value = spec.pick(row);
    return jsonResponse({
      schemaVersion: 1,
      label: spec.label,
      message: fmt(value),
      color: colorFor(value, spec.floor),
    });
  } catch {
    return jsonResponse({
      schemaVersion: 1,
      label: spec.label,
      message: "error",
      color: "lightgrey",
    });
  }
}
