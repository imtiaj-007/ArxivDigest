import defaultMdxComponents from "fumadocs-ui/mdx";
import type { MDXComponents } from "mdx/types";
import { EvalMetricsCard } from "@/components/eval-metrics-card";
import { Mermaid } from "@/components/mermaid";

export function getMDXComponents(components?: MDXComponents) {
  return {
    ...defaultMdxComponents,
    EvalMetricsCard,
    Mermaid,
    ...components,
  } satisfies MDXComponents;
}
