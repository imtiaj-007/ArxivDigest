import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";

// Shared nav config so HomeLayout (non-docs pages) and DocsLayout (/docs)
// render the same wordmark + link bar across the site.
export const baseOptions: BaseLayoutProps = {
  nav: {
    title: "ArxivDigest",
    url: "/",
  },
  links: [
    { text: "Papers", url: "/papers" },
    { text: "Status", url: "/status" },
    { text: "Docs", url: "/docs" },
    { text: "About", url: "/about" },
  ],
  githubUrl: "https://github.com/imtiaj-007/ArxivDigest",
};
