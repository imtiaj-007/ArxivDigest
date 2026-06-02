"use client";

import { useEffect, useId, useState } from "react";

function readDarkMode(): boolean {
  if (typeof document === "undefined") return false;
  return document.documentElement.classList.contains("dark");
}

export function Mermaid({ chart }: { chart: string }) {
  const id = useId().replace(/[:]/g, "_");
  const [svg, setSvg] = useState<string | null>(null);
  const [isDark, setIsDark] = useState<boolean>(false);

  // Track <html class="dark"> toggles so diagrams re-render with the right theme.
  useEffect(() => {
    setIsDark(readDarkMode());
    const observer = new MutationObserver(() => setIsDark(readDarkMode()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const m = (await import("mermaid")).default;
      // Re-init every render — mermaid bakes theme at init, so toggle pulls
      // require a fresh initialize before render.
      m.initialize({
        startOnLoad: false,
        theme: isDark ? "dark" : "neutral",
        // 'handDrawn' gives a pencil-sketch aesthetic; built-in to mermaid v11.
        look: "handDrawn",
        handDrawnSeed: 7,
        fontFamily: "var(--font-geist-sans), ui-sans-serif, system-ui",
        flowchart: { curve: "basis", htmlLabels: true, useMaxWidth: true },
        sequence: { useMaxWidth: true },
        er: { useMaxWidth: true },
      });
      try {
        const { svg } = await m.render(`mmd_${id}_${isDark ? "d" : "l"}`, chart);
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
  }, [chart, id, isDark]);

  return (
    <div
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
