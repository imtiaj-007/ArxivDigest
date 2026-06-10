# Aceternity components

Copy-paste components from [aceternity.com/components](https://ui.aceternity.com/components) live here, namespaced so they're discoverable and contained.

## Why this folder exists separately

- **Motion-heavy.** These all depend on `motion` (Framer Motion v12+). Isolating them keeps that import surface obvious so we can audit bundle weight at PR review time.
- **Copy-paste, not a package.** Aceternity is shadcn-model: source is forked into the repo, owned and modified locally. No version pin, no migration story; if upstream changes, we don't get it unless we re-copy.
- **Distinct from `components/ui/`.** That folder holds base-nova shadcn primitives (`Button`, `Card`, `Badge`) — those are non-animated and reused across the app. Aceternity primitives are showcase / narrative pieces.

## House rules

1. **Respect `prefers-reduced-motion`.** Every animated component must wrap its motion in a guard. Use the shared `useRespectMotion()` hook from `motion-provider.tsx` (added in Phase 3 polish).
2. **One motion moment per page.** Don't compose multiple Aceternity components on the same route unless you've measured the cost.
3. **Keep them server-component-friendly where possible.** Mark the file `"use client"` only if motion or hooks require it. Layout-only primitives (e.g. Bento Grid) should stay server components.
4. **Cite the upstream URL** at the top of each component file so the original source is one click away.
5. **Theme-aware.** Aceternity defaults are dark-mode-first. Light-mode overrides go in the same file, not a sibling stylesheet.

## Roster

Add new components below as they land.

| Component | Page using it | Notes |
|---|---|---|
| `motion-provider.tsx` | site root | LazyMotion + reduced-motion hook (Phase 1.0 foundation) |
| `background-beams.tsx` | `/` hero | 19 staggered SVG paths, gradient-stroked, reduced-motion-aware. Local fork of [ui.aceternity.com/components/background-beams](https://ui.aceternity.com/components/background-beams) |
