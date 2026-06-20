# Gridlock — Project Philosophy

## The Aim

Predict where traffic violations will happen in Bengaluru before they happen. Not a retrospective dashboard — a forward-looking tool. Give a date, get a heatmap of the city showing which 100-meter patches will be dangerous, how dangerous, and when during the day they'll peak.

The audience is a hackathon judging panel. The first impression is the map lighting up with color. The second impression is clicking a hotspot and seeing it's not just a blob — it's a specific prediction with a violation count, a congestion impact score, and forecasted peak hours. The third impression is realizing the model retrained on fresh data they just uploaded.

## The Feel

**Dense but not cluttered.** The dashboard shows a lot — a full city map, colored grid cells, a ranked list, peak hour chips — but every element earns its space. Nothing decorative. If it's on screen, it's answerable: "what's the worst spot?", "when does it peak?", "how bad is the congestion impact?".

**Analytical, not flashy.** This is a tool for understanding a city, not a marketing page. The aesthetic is closer to a Bloomberg terminal or a Grafana board than a landing page. Dark mode default feel. Data-forward. The map does the talking.

**Responsive to the question, not the clock.** Predictions are fetched on demand — pick a date, click fetch. There's no auto-refresh, no real-time ticker, no streaming. The user is in control. The system answers when asked.

## The Build Philosophy

**Speed of change over correctness of architecture.** This is a hackathon. The backend is being built simultaneously and will change shape. The UI will get rearranged mid-sprint. The spec will drift. Every architectural choice optimizes for "how fast can I adapt when something changes" — not "how clean is this abstraction".

Concretely:
- The API layer exists to absorb backend churn. A mapper file is the seam. When the backend renames a field or merges two endpoints, one file changes. Components never know.
- Mock data is built in from day one. The frontend must be demoable without the backend running. No blocked work.
- Pages are thin shells. Rearranging the dashboard layout means moving JSX in one file, not refactoring a component tree.
- Components are independent. The map doesn't import from rankings. Rankings don't import from the map. They share a Zustand store and that's it. Either can be ripped out or replaced without touching the other.

**Readable over clever.** One thing per file. Obvious names. No abstractions until the third copy-paste. A new teammate should be able to open any file and understand it without reading three others first. The codebase is small enough that this is achievable — don't sacrifice it for elegance.

**Prototype-grade, not production-grade.** No auth, no CI/CD, no error boundaries wrapping every component, no retry logic with exponential backoff. Handle the happy path well, handle errors visibly (a banner, not a silent console.log), and move on. The goal is a working demo, not a deployable product.

## What Success Looks Like

A judge opens the app. The map of Bengaluru is already showing predicted hotspots for today. Silk Board Junction is glowing red. They click it — 342 predicted violations, peaks at 8–9:30 AM and 5:30–7 PM, congestion impact 94.7. They glance at the ranked list, switch to the congestion impact tab, see the same data from a different angle. They go to Data Management, upload a new CSV, watch the model status flip to "Training...", come back, fetch again, and the predictions have shifted.

The whole loop takes under two minutes. Nothing broke. Nothing was confusing. The data told a story.
