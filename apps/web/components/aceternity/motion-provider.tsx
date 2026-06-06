"use client";

// Foundation for every Aceternity component in this folder.
//
// - LazyMotion + domAnimation: tree-shakes the motion runtime so only the
//   features actually used by mounted components ship. Cuts roughly 50% off
//   the bundle vs the full `motion` import surface.
// - useRespectMotion: single source of truth for the prefers-reduced-motion
//   media query. Components should call this and degrade to a no-op rather
//   than checking the matchMedia API themselves.
//
// Mount <MotionProvider> high in the app tree (root layout). Components inside
// can use `m.div` / `m.span` etc. from motion/react in place of `motion.div`.

import { LazyMotion, domAnimation, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

export function MotionProvider({ children }: { children: ReactNode }) {
  return <LazyMotion features={domAnimation}>{children}</LazyMotion>;
}

/**
 * `true` when the OS / browser is asking for reduced motion. Components should
 * treat this as a hint to skip animation entirely, not to slow it down — the
 * media query exists for vestibular accessibility, not preference.
 */
export function useRespectMotion(): boolean {
  return useReducedMotion() ?? false;
}
