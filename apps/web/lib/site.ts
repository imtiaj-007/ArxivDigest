/** Canonical base URL for absolute links (RSS items, OG tags, sitemaps).
 *
 * Overridable via NEXT_PUBLIC_SITE_URL so preview deploys can announce their
 * own host in feeds; falls back to the production Vercel URL otherwise.
 */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/+$/, "") ??
  "https://arxiv-digest-preview.vercel.app";

export const SITE_NAME = "ArxivDigest";

export const SITE_DESCRIPTION =
  "Autonomous daily AI agent that summarises new arxiv submissions, classifies them by theme, and ranks them by novelty and impact.";
