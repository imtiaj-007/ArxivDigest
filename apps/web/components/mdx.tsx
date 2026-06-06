import defaultMdxComponents from "fumadocs-ui/mdx";
import type { MDXComponents } from "mdx/types";
import { EvalHistoryTable } from "@/components/eval-history-table";
import { EvalMetricsCard } from "@/components/eval-metrics-card";
import { Mermaid } from "@/components/mermaid";

export function getMDXComponents(components?: MDXComponents) {
  return {
    ...defaultMdxComponents,
    EvalHistoryTable,
    EvalMetricsCard,
    Mermaid,
    ...components,
  } satisfies MDXComponents;
}
