export type StructuredSummary = {
  problem: string;
  approach: string;
  result: string;
  why_it_matters: string;
};

/** Decode the JSON-encoded summary stored in papers.summary; null if missing or unstructured. */
export function parseSummary(raw: string | null): StructuredSummary | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<StructuredSummary>;
    if (typeof parsed.problem === "string") {
      return parsed as StructuredSummary;
    }
  } catch {
    /* older plain-text rows fall through */
  }
  return null;
}
