import { source } from "@/lib/source";
import { DocsLayout } from "fumadocs-ui/layouts/docs";
import type { ReactNode } from "react";
import { baseOptions } from "@/lib/layout-options";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout {...baseOptions} tree={source.getPageTree()}>
      {children}
    </DocsLayout>
  );
}
