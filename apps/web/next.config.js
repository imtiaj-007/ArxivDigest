import { createMDX } from "fumadocs-mdx/next";
import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@repo/db"],
};

const withMDX = createMDX();

// Sentry's webpack work (source map upload, tunneling) is gated by SENTRY_AUTH_TOKEN at build time.
// Without the token it's effectively a no-op wrapper, safe to leave on.
export default withSentryConfig(withMDX(nextConfig), {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: !process.env.CI,
  widenClientFileUpload: true,
});
