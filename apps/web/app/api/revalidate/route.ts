import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

// Token-gated revalidation hook. The agent posts here after a successful
// daily run; we bust the cache on the data-driven pages so the freshly
// published digest shows up immediately instead of waiting for the ISR
// revalidate interval. Pages declared `force-dynamic` ignore the call
// harmlessly — listing them is forward-compatible if their mode changes.

const PATHS = [
  "/papers",
  "/status",
] as const;

const DYNAMIC_PATHS: Array<{ path: string; type: "page" }> = [
  { path: "/papers/[arxiv_id]", type: "page" },
  { path: "/themes/[slug]", type: "page" },
  { path: "/archive/[year]/[month]", type: "page" },
];

export async function POST(request: Request) {
  const expected = process.env.REVALIDATE_TOKEN;
  if (!expected) {
    return NextResponse.json({ error: "revalidation not configured" }, { status: 503 });
  }
  const auth = request.headers.get("authorization");
  if (auth !== `Bearer ${expected}`) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  for (const path of PATHS) {
    revalidatePath(path);
  }
  for (const { path, type } of DYNAMIC_PATHS) {
    revalidatePath(path, type);
  }

  return NextResponse.json({
    revalidated: true,
    paths: [...PATHS, ...DYNAMIC_PATHS.map((p) => p.path)],
    ts: Date.now(),
  });
}
