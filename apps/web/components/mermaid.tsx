"use client";

import { useEffect, useId, useRef, useState } from "react";

declare global {
  interface Window {
    __arxivdigestMermaidInit?: boolean;
  }
}

export function Mermaid({ chart }: { chart: string }) {
  const id = useId().replace(/[:]/g, "_");
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const m = (await import("mermaid")).default;
      if (!window.__arxivdigestMermaidInit) {
        m.initialize({
          startOnLoad: false,
          theme: "default",
          fontFamily: "var(--font-geist-sans), ui-sans-serif, system-ui",
          themeVariables: {
            primaryColor: "#fafafa",
            primaryTextColor: "#0a0a0a",
            primaryBorderColor: "#d4d4d8",
            lineColor: "#71717a",
            secondaryColor: "#f4f4f5",
            tertiaryColor: "#fafafa",
          },
          flowchart: { curve: "basis", htmlLabels: true, useMaxWidth: true },
          sequence: { useMaxWidth: true },
        });
        window.__arxivdigestMermaidInit = true;
      }
      try {
        const { svg } = await m.render(`mmd_${id}`, chart);
        if (!cancelled) setSvg(svg);
      } catch (err) {
        if (!cancelled) {
          setSvg(
            `<pre style="color:#dc2626;font-size:0.8rem;">Mermaid render error: ${String(err).replace(/</g, "&lt;")}</pre>`,
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  return (
    <div
      ref={ref}
      className="my-6 flex justify-center overflow-x-auto rounded-lg border border-fd-border bg-fd-card p-4"
      // biome-ignore lint/security/noDangerouslySetInnerHtml: mermaid emits sanitized SVG
      dangerouslySetInnerHTML={svg ? { __html: svg } : undefined}
    >
      {svg ? null : (
        <div className="text-sm text-fd-muted-foreground">Rendering diagram…</div>
      )}
    </div>
  );
}
