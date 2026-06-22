# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Gridlock — a hackathon web app that visualizes ML-predicted traffic violation hotspots in Bengaluru. Frontend only; the Python ML backend is a separate service.

Full specs: `spec.md` (architecture, API contract, grid system) and `ui-design.md` (wireframes, colors, interactions). Read both before making changes.

## Tech Stack

Vite + React 18 + TypeScript + Tailwind CSS. Zustand for state. Axios for HTTP. React Router v6. Mapbox GL JS for maps (Leaflet fallback when `VITE_MAPBOX_TOKEN` is unset).

## Commands

```bash
npm run dev          # Dev server
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # ESLint
npm run typecheck    # tsc --noEmit
```

## Architecture — The API Seam

The backend contract is unstable. The frontend isolates against this with a strict layered boundary:

```
Backend JSON → api/types.ts (raw types) → api/mappers.ts (conversion) → types/index.ts (domain types) → components
```

**When the backend changes a response shape**, only `api/types.ts` and `api/mappers.ts` change. Components consume domain types and never import from `api/types.ts`. Each API module (`api/predictions.ts`, `api/data.ts`, `api/model.ts`) exports clean async functions — components never call axios directly.

Set `VITE_USE_MOCKS=true` to run against static JSON in `api/mocks/` without a live backend.

## Grid Cell System

The backend divides Bengaluru into 300m × 300m cells (`CELL_KM = 0.3`). `lib/grid.ts` mirrors the backend's grid math. Constants (`CELL_KM`, `KM_PER_DEG_LAT`, `COS_LAT` at 13°N) are the backend's source of truth — if the backend changes them, `grid.ts` must match. The frontend derives lat/lon and GeoJSON polygons from `cell_id` strings (format: `"{i}_{j}"`). No lat/lon comes from the API.

## Code Style

- One thing per file, ~120 line max. Split if exceeded.
- Named exports only, no default exports.
- Functional arrow components. Destructure props in signature.
- Tailwind inline. For repeated combos, `const styles = { ... }` at file top.
- Explicit TypeScript types, no `any`. All interfaces in `types/index.ts`.
- Props over context/stores. Zustand only for truly global state (predictions, model status, datasets).
- No premature abstraction — duplicate twice before extracting.
- Pages are thin composition shells with no logic.
- Map and rankings are fully decoupled — they share data via stores, zero direct imports.

## Routing

Two routes: `/` (dashboard) and `/data` (data management). No nested or dynamic routes.

## Theming

Auto dark/light via `prefers-color-scheme`. Map styles switch between `dark-v11` and `light-v11`. Color tokens in `lib/colors.ts`. Severity palette: green (low) → yellow (moderate) → orange (high) → red (critical), percentile-based.

## Environment Variables

- `VITE_API_BASE_URL` — backend base (default `/api` for same-origin via nginx proxy)
- `VITE_MAPBOX_TOKEN` — Mapbox access token. Empty = Leaflet fallback.
- `VITE_USE_MOCKS` — `true` to use static mock data.
