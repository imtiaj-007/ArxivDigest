import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";

// Shared nav config. Top-nav strip (HomeLayout + DocsLayout header) uses
// these links; the /docs sidebar gets its own "Portal" section from
// content/docs/meta.json so portal links sit inside a proper group header
// (matching Engineering / Operations).
export const baseOptions: BaseLayoutProps = {
  nav: {
    title: "ArxivDigest",
    url: "/",
  },
  links: [
    { text: "Papers", url: "/papers", on: "nav" },
    { text: "Status", url: "/status", on: "nav" },
    { text: "Docs", url: "/docs", on: "nav" },
    { text: "About", url: "/about", on: "nav" },
  ],
  githubUrl: "https://github.com/imtiaj-007/ArxivDigest",
};
