"use client";

// Source (concept): https://ui.aceternity.com/components/background-beams
// Adapted for ArxivDigest:
//  - paths redrawn to fit a 0..1000 × 0..400 viewBox so they actually trace
//    across the visible section (upstream coords went off-frame),
//  - bumped stroke + opacity so the beams are clearly visible against the
//    page background on both themes (upstream is very subtle and disappears
//    on light backgrounds with low ambient contrast),
//  - swapped upstream's hard-coded near-black for a cyan→indigo→magenta
//    gradient that reads on dark AND light surfaces,
//  - prefers-reduced-motion → static beams (no animation) instead of going
//    blank, so the visual still tells a story for accessibility users.

import { m } from "motion/react";
import { memo } from "react";

import { cn } from "@/lib/utils";

import { useRespectMotion } from "./motion-provider";

// Diagonal paths sweeping across the hero. Coordinates designed for a
// 0..1000 horizontal × 0..400 vertical viewBox, so each beam starts off
// the left edge and curves up across the visible area.
const PATHS = [
  "M-100 360 C 200 280, 500 200, 1100 60",
  "M-100 320 C 200 250, 500 170, 1100 40",
  "M-100 280 C 200 220, 500 140, 1100 20",
  "M-100 240 C 200 190, 500 120, 1100 10",
  "M-100 200 C 200 160, 500 100, 1100 0",
  "M-100 160 C 200 130, 500 80, 1100 -10",
  "M-100 120 C 200 100, 500 60, 1100 -20",
  "M-100 80 C 200 70, 500 40, 1100 -30",
  "M-100 40 C 200 40, 500 20, 1100 -40",
];

export const BackgroundBeams = memo(function BackgroundBeams({
  className,
}: {
  className?: string;
}) {
  const reduced = useRespectMotion();

  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden",
        className,
      )}
    >
      {/* Subtle radial wash behind the beams so they sit on a coloured field
          rather than the bare page background. Quiet on light, deeper on dark. */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_color-mix(in_oklab,_var(--fd-primary)_8%,_transparent),_transparent_60%)] dark:bg-[radial-gradient(ellipse_at_top,_color-mix(in_oklab,_var(--fd-primary)_18%,_transparent),_transparent_60%)]" />

      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 1000 400"
        fill="none"
        preserveAspectRatio="xMidYMid slice"
      >
        {PATHS.map((d, idx) => (
          <m.path
            key={idx}
            d={d}
            stroke="url(#background-beams-gradient)"
            strokeOpacity={reduced ? 0.5 : 0.8}
            strokeWidth={1.5}
            strokeLinecap="round"
            initial={reduced ? false : { pathLength: 0.0, opacity: 0 }}
            animate={
              reduced
                ? undefined
                : { pathLength: [0.0, 1.0, 1.0], opacity: [0, 0.9, 0] }
            }
            transition={
              reduced
                ? undefined
                : {
                    duration: 6,
                    delay: idx * 0.55,
                    repeat: Infinity,
                    repeatType: "loop",
                    ease: "easeInOut",
                  }
            }
          />
        ))}
        <defs>
          <linearGradient
            id="background-beams-gradient"
            x1="0"
            y1="0"
            x2="1"
            y2="0"
          >
            <stop offset="0%" stopColor="#18CCFC" stopOpacity="0" />
            <stop offset="20%" stopColor="#18CCFC" />
            <stop offset="50%" stopColor="#6344F5" />
            <stop offset="80%" stopColor="#AE48FF" />
            <stop offset="100%" stopColor="#AE48FF" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
});
