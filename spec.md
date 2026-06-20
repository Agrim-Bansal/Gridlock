# Flipkart Gridlock Challenge — Product & Architecture Spec

> **Status:** living document. The backend and the ML model are under active development and *will* change shape. This spec is written to survive that churn — it separates the **stable contract** (what the system promises) from the **swappable internals** (how each side keeps that promise). When something changes, change it in the one place this spec points to.
>
> **Companion docs:**
> - [`API_CONTRACT.md`](./API_CONTRACT.md) — authoritative source of truth for the HTTP boundary (request/response shapes, casing, error codes). If this spec and the contract ever disagree about a wire shape, the contract wins.
> - [`ui-design.md`](./frontend/ui-design.md) — wireframes, colors, interaction detail.
> - [`PHILOSOPHY.md`](./PHILOSOPHY.md) — the why: feel, build values, definition of success.

---

## 1. Overview

A web application that visualizes **ML-predicted traffic violation hotspots** across Bengaluru. Users upload CSV training data to manage the model's dataset. The model retrains on data changes and produces **per-day violation density predictions** with **peak-hour forecasts** derived from historical rolling averages.

A dashboard displays date-specific predictions as color-coded 100m grid cells on an interactive map, alongside two tab-switchable ranked lists (by violation count and by congestion impact), each row carrying peak-hour forecasts.

The product is two cooperating services with one narrow contract between them:

- **Frontend** — Vite + React SPA. Renders predictions; never computes geometry-from-scratch beyond the shared grid math, never invents severity, never derives peak hours. *It renders exactly what the API returns.*
- **Backend** — Python (FastAPI) service. Ingests CSVs, owns the database, computes severity, and exposes a clean **seam** where the ML model plugs in. *The model's output is the product.*

The ML model itself is **not yet built**. The backend ships today with a **stub predictor** behind the same interface the real model will implement, so the entire app is demoable end-to-end before any model exists. Swapping the real model in is a one-class change (§8.4).

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          AWS Lightsail VM                              │
│                                                                        │
│  Browser ──443──▶ Nginx                                                │
│                     ├─ /        → static React build (dist/)           │
│                     └─ /api/*   → reverse proxy → 127.0.0.1:8000       │
│                                                                        │
│                   FastAPI backend (uvicorn :8000, systemd-managed)     │
│                     │                                                   │
│                     ├─ routers/      HTTP boundary (mirrors contract)  │
│                     ├─ services/     ingest · severity · retrain · state│
│                     ├─ ml/           Predictor seam ◀── REAL MODEL drops in here
│                     │     ├─ StubPredictor   (ships now)               │
│                     │     └─ RealPredictor   (lands later)             │
│                     └─ db.py / models.py                               │
│                                                                        │
│                   SQLite (metadata + parsed rows)  +  data/*.csv (raw) │
└──────────────────────────────────────────────────────────────────────┘
```

**The two seams that absorb change:**

| Seam | Location | Absorbs |
|---|---|---|
| **API mapper seam** | frontend `src/api/types.ts` + `mappers.ts` | Backend changing wire shapes. Components never see raw JSON. |
| **Predictor seam** | backend `app/ml/predictor.py` (Protocol) | The ML model changing — or not existing yet. Routers/services never see model internals. |

These two seams are why the system tolerates an unstable backend and a not-yet-built model. Everything outside them stays put.

---

## 3. User Flow

```
App loads → Dashboard (default view)
Nav: • Dashboard (predictions map + rankings)   • Data Management (upload/delete CSVs)

Data Management:
  1. Upload data.csv (drag-and-drop, preview first 5 rows)
  2. See list of uploaded datasets
  3. Delete a dataset
  4. Any upload/delete triggers model retrain
  5. Retrain status shown (idle / training / ready)

Dashboard:
  1. Date picker (defaults to today)
  2. Interactive map of Bengaluru
  3. Hotspot grid cells, color-coded by severity
  4. Two tabbed ranked lists:
       a. By violation count (desc)
       b. By congestion impact (desc)
       c. Each row shows peak-hour forecast
  5. Click list item  → highlight + fly to cell, open popup
  6. Click map cell    → detail popup
  7. "Fetch Predictions" button (explicit, on-demand)

States the UI must handle:
  • No model trained yet  → empty-state prompt (backend returns 409)
  • Model training        → disabled fetch + spinner
  • No hotspots for date  → calm "no data" message (backend returns 200, [])
  • Backend unreachable   → error banner + retry
```

The **409 vs empty-200** distinction is load-bearing: 409 = "train a model first" (CTA to upload), empty 200 = "model ran, nothing predicted for this date" (calm informational). The backend must never conflate them (§8.9).

---

## 4. UI / UX Design

Full wireframes and visual specs: [`ui-design.md`](./frontend/ui-design.md). Summary:

- **Layout:** top bar (logo / nav / theme) · 280px fixed side panel · main content · status bar (model pill · last trained · dataset count).
- **Dashboard map:** full-bleed, centered on Bengaluru (12.9716°N, 77.5946°E, zoom 11). Hotspots are **GeoJSON polygon fill cells** (not circles), one per 100m grid cell. Fill gradient green→yellow→orange→red by percentile; opacity 0.6 base / 0.85 hover. Adjacent hot cells merge into heatmap-like blobs at low zoom; individual squares at high zoom. Click → popup (location name, cell ID, count, type breakdown, impact score, peak windows).
- **Toolbar:** floating date picker + "Fetch Predictions"; disabled with spinner while training.
- **Side panel:** two tabs — **By Violations** and **By Congestion Impact** — each row: rank, location name, metric badge, peak-hour chips. Click a row → highlight cell + fly + open popup.
- **Data Management:** drag-and-drop `.csv` upload zone with 5-row preview; dataset table (filename, upload date, row count, status, delete); retrain pill in status bar.
- **Theming:** auto dark/light via `prefers-color-scheme`. Map style `dark-v11` / `light-v11`. Severity palette percentile-based.
- **Responsiveness:** desktop-first; side panel → bottom sheet below 1024px; map interactive at all breakpoints.

---

## 5. Grid Cell System (shared source of truth)

Every prediction is tied to a uniform **100m × 100m grid cell**, never an arbitrary point. The grid math is **shared** between backend and frontend. **The backend is the source of truth; the frontend mirrors it** in `src/lib/grid.ts`. A mismatch silently misplaces every cell on the map — treat these constants as a binding interface.

| Parameter | Value |
|---|---|
| Cell size | 0.1 km × 0.1 km |
| `KM_PER_DEG_LAT` | 111.0 |
| Reference latitude | 13.0°N (`COS_LAT = cos(radians(13))`) |
| Latitude step | `0.1 / 111.0 ≈ 0.0009009°` |
| Longitude step | `0.1 / (111.0 × cos 13°) ≈ 0.0009246°` |
| Cell ID format | `"{i}_{j}"`, `i = round(lat / LAT_STEP)`, `j = round(lon / LON_STEP)` |
| Center recovery | `lat = i × LAT_STEP`, `lon = j × LON_STEP` |

Example: `"14345_83842"` → center ≈ (12.917°N, 77.623°E).

**Rules:**
- `cell_id` is exactly two integers joined by one underscore — no padding, no extra signs. The frontend does `cellId.split("_").map(Number)`.
- `i` is latitude index, `j` is longitude index. Order matters.
- **Lat/lon appear only in training input (CSV), never in prediction output.** Output is keyed purely by `cell_id`; the frontend derives all geometry.
- If the backend changes `CELL_KM` or the reference latitude, it **must** notify the frontend so `lib/grid.ts` updates in lockstep. A backend test (`tests/test_grid.py`) and the frontend mirror pin this invariant on both sides.

---

## 6. API Contract (the HTTP boundary)

> **`API_CONTRACT.md` is authoritative.** This section is a navigational summary; defer to the contract for exact shapes, casing, nullability, and error bodies.

Five endpoints, all under `/api`, all `snake_case` JSON, ISO-8601-UTC timestamps. No auth, no pagination, no websockets.

| # | Method | Path | Purpose |
|---|---|---|---|
| 1 | `GET` | `/api/predictions?date=YYYY-MM-DD` | Predicted hotspots for a date — the core feature. |
| 2 | `GET` | `/api/model/status` | Model training state (`idle`/`training`/`ready`) + dataset/row counts. |
| 3 | `GET` | `/api/data` | List uploaded datasets. |
| 4 | `POST` | `/api/data/upload` | Upload a CSV (`multipart`, field `file`); triggers retrain. |
| 5 | `DELETE` | `/api/data/{id}` | Delete a dataset; triggers retrain. |

**Contract invariants the backend must honor:**
- `/predictions` returns everything per cell per date in one call: `violation_count`, `violation_types[]`, `severity`, `congestion_impact_score`, `peak_hours[]`.
- `severity` is **backend-computed** from percentiles across the day's cells (§8.8) — never sent by the model, never recomputed by the frontend.
- Empty result = `200 {hotspots: []}`. No model = `409`. (§8.9)
- Errors return `{ "error": "<snake_code>", "message": "<human>" }` with a standard status code.

**Handling contract changes (frontend side):** add field → raw type + mapper; rename → raw type + mapper; URL change → one fetch call; split/merge → API module internals, keep exported signatures (`fetchPredictions`, `listDatasets`, `uploadDataset`, `deleteDataset`, `getModelStatus`) stable. Components never change.

**Handling contract changes (process):** the backend tells the frontend team *before* shipping a shape change. Additive changes are safe (mapper ignores unknowns); rename/retype/remove are breaking. Casing, ISO-UTC timestamps, and `cell_id` format are load-bearing — do not drift them.

---

## 7. Frontend Architecture

```
src/
├── main.tsx · App.tsx                 # entry + router/layout shell
├── api/
│   ├── client.ts                      # axios instance, base URL
│   ├── types.ts                       # RAW response types (mirror backend JSON)
│   ├── mappers.ts                     # raw → domain — THE seam for backend churn
│   ├── data.ts · model.ts · predictions.ts   # clean async functions, no axios leaks
│   └── mocks/*.json                   # static data for VITE_USE_MOCKS=true
├── components/  layout · map · rankings · data · shared
├── pages/  DashboardPage · DataManagementPage     # thin composition shells
├── stores/  predictionStore · dataStore · modelStore   # Zustand, global only
├── hooks/  useMapbox · useTheme
├── types/index.ts                     # DOMAIN types — what components see
└── lib/  grid.ts · colors.ts · mapConfig.ts
```

**Data flow:** `Backend JSON → api/types.ts → api/mappers.ts → api/*.ts → stores → components`.

Map and rankings are **fully decoupled** — they share data only through stores, with zero direct imports. Either can be replaced without touching the other.

---

## 8. Backend Architecture

The backend is a thin FastAPI service whose real job is: **honor the contract exactly, persist data durably, and expose the Predictor seam.** It is built so the not-yet-existent ML model can land without touching routers, persistence, or the wire shape.

### 8.1 Layered boundary

```
HTTP request
  → routers/      (validate, map to/from contract shapes — Pydantic == contract)
  → services/     (ingest, severity, model-state, retrain orchestration)
  → ml/           (Predictor seam — stub now, real model later)
  → db / disk     (SQLite metadata + rows; raw CSVs on disk)
```

Routers know HTTP. Services know business rules. The `ml/` layer knows prediction. Persistence knows storage. No layer reaches past its neighbor — the same discipline the frontend applies to its API seam.

### 8.2 Directory layout (`./backend/`)

```
backend/
├── app/
│   ├── main.py            # FastAPI app, CORS, routers, startup
│   ├── config.py          # settings: paths, retrain delay, db url (env-driven)
│   ├── schemas.py         # Pydantic models == API_CONTRACT shapes (snake_case)
│   ├── errors.py          # {error,message} body + exception handlers (§8.9)
│   ├── db.py · models.py  # SQLite engine/session; Dataset, ViolationRow tables
│   ├── grid.py            # EXACT mirror of §5 — point→cell_id, cell_id→center
│   ├── routers/  predictions.py · model.py · data.py
│   ├── services/ ingest.py · model_state.py · retrain.py · severity.py
│   └── ml/  predictor.py (Protocol) · stub.py (StubPredictor) · README.md
├── data/                  # runtime: uploaded CSVs + gridlock.db (gitignored)
├── tests/  test_contract.py · test_grid.py
├── requirements.txt · .env.example · README.md
├── Dockerfile · .dockerignore
└── deploy/  gridlock-backend.service · nginx-gridlock.conf · DEPLOY.md
```

Style mirrors the frontend: one thing per file, small files, flat obvious names, explicit types.

### 8.3 Data model

- **SQLite** for metadata + parsed rows; **raw CSVs on disk** under `data/`. Zero extra infra, survives restarts, trivial to back up — right-sized for a single Lightsail VM.
- `datasets`: `id` (`d_<uuid8>`), `filename`, `uploaded_at`, `row_count`, `status` (`processing|active`), `path`.
- `violation_rows`: `dataset_id` (FK, cascade delete), `timestamp`, `cell_id`, `violation_type`, `severity_src`. **Lat/lon are converted to `cell_id` at ingest and discarded from output** (§5, §2.3 of contract).
- `/model/status` `dataset_count` and `total_rows` are SQL aggregates over active datasets — never hand-maintained counters.

### 8.4 The ML seam — `Predictor` Protocol

This is the single interface the real model must satisfy. Everything else is stable around it.

```python
class Predictor(Protocol):
    def train(self, rows: list[ViolationRow]) -> None: ...
    def predict(self, day: date) -> list[HotspotPrediction]: ...
    #   HotspotPrediction carries RAW model output:
    #   cell_id, violation_count, violation_types[], congestion_impact_score,
    #   peak_hours[], optional location_name.
    #   It does NOT carry severity — the service layer assigns that (§8.8).
```

- A small **registry** in `app/ml/__init__.py` selects the active predictor (`StubPredictor` today). Dropping in the real model = add `RealPredictor(Predictor)`, flip one registry line. No router/service/persistence change.
- `app/ml/README.md` documents exactly what the model receives (parsed `ViolationRow`s and/or the on-disk CSV paths) and must return.
- The model stays ignorant of HTTP, of the severity palette, and of the grid — those are owned outside the seam. This keeps the data-science work as decoupled from the web service as possible while the model is in flux.

### 8.5 Model lifecycle & retrain

In-process, observable state machine — no external queue.

```
idle ──upload──▶ training ──train() ok──▶ ready
 ▲                                          │
 └────────────── delete last dataset ───────┘   (otherwise stays ready after retrain)
```

- Upload/delete flips `status = training` **immediately**, then a **FastAPI background task** ingests rows, calls `predictor.train(...)`, waits a small configurable real delay (~2s, `RETRAIN_DELAY_S`) so the frontend's polling reliably observes the `training → ready` edge, then sets `status = ready` and stamps `last_trained_at`. If no datasets remain → `idle`, `last_trained_at` stays null.
- Model state lives in `services/model_state.py` (in-memory, single process). This is intentional hackathon simplicity; if the service ever scales horizontally this moves to the DB — called out in §13.

### 8.6 CSV ingest

- `multipart` field name exactly `file`; one file per request. Non-CSV → `415`. Unparseable / missing required columns → `422` with detail.
- **Flexible column mapping:** case-insensitive header matching with aliases (e.g. `lat`/`latitude`, `lng`/`lon`/`longitude`, `time`/`timestamp`, `violation`/`violation_type`). **Required:** timestamp, latitude, longitude. Optional: violation type, source severity. Extra columns tolerated and ignored.
- Each row → `cell_id` via `grid.py` at ingest time; lat/lon not persisted to output. Row count recorded for the contract.
- Ingest runs inside the retrain background task; dataset shows `processing` until rows are in and the model has retrained, then `active`.

### 8.7 Stub predictor (because the model is under development)

Ships today so the whole app is demoable with no ML model.

- Generates hotspots over Bengaluru, **seeded by the requested date** so the same date returns stable numbers across repeated fetches (a model that reshuffles its prediction every click reads as broken to a judge), while different dates differ and a retrain visibly shifts output. *This is the one deliberate refinement over "pure random" — same randomness, made reproducible-per-date. Flipping back to reroll-every-call is a one-line change, clearly marked.*
- When datasets are present, the stub can bias toward cells that actually appear in uploaded rows, so "upload data → fetch → predictions shifted" tells a real story in the demo loop.
- Emits **raw counts only**; the service layer assigns severity. This proves the seam: the real model will produce the same shape and need no downstream changes.

### 8.8 Severity ownership (backend, not model)

`severity` is computed **per request** by `services/severity.py` from `violation_count` percentiles across all cells returned for that date — adaptive to any dataset, never an absolute threshold:

| Severity | Percentile band of `violation_count` |
|---|---|
| `critical` | top 10% |
| `high` | 70th–90th |
| `moderate` | 40th–70th |
| `low` | bottom 40% |

Keeping this out of the model means the data-science team never owns the palette, and the frontend trusts the field verbatim for fill color.

### 8.9 Errors

Global exception handler returns `{ "error": "<snake_code>", "message": "<human>" }` for every non-2xx.

| Code | When |
|---|---|
| `400` | missing/invalid `date` on `/predictions` |
| `404` | `DELETE` unknown dataset id |
| `409` | `/predictions` while model `idle` (no model trained) — **distinct from empty 200** |
| `415` | upload of non-CSV |
| `422` | CSV present but unparseable / missing required columns |
| `500` / `503` | inference/model failure / model busy |

CORS owned by the backend (Nginx adds none): allow the frontend origin, methods `GET, POST, DELETE`, `Content-Type`. Endpoints matched **without** trailing slashes.

---

## 9. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Default page | Dashboard | Most visits are to see predictions, not upload. |
| Map library | Mapbox + Leaflet fallback | Superior fill layers; fallback keeps the demo alive without a token. |
| Frontend state | Zustand | Minimal boilerplate for 3 small global stores. |
| No WebSocket | Manual fetch | Simpler; user picks a date and clicks fetch. |
| One predictions endpoint | `/predictions?date=` returns everything | Count, impact, peaks are all per-cell-per-date — one call. |
| Severity | Percentile-based, backend-owned | Adapts to any dataset; single owner; frontend renders verbatim. |
| Grid cells not circles | Fill-layer rectangles on 100m grid | Accurate; merges into heatmap at low zoom. |
| Raw/domain split (FE) | `api/types.ts` vs `types/index.ts` | Contract churn stays in `api/`. |
| **Backend framework** | **FastAPI** | Pydantic models mirror the contract for free; BackgroundTasks for retrain; auto `/docs`; best fit for typed JSON + ML. |
| **Persistence** | **SQLite + CSVs on disk** | No infra; restart-durable; right size for one VM. |
| **ML integration** | **`Predictor` Protocol + stub** | Model is under development — code the seam, ship a stub, swap one class later. |
| **Severity placement** | **Service layer, not model** | Decouples data science from presentation policy. |
| **Retrain** | **In-process background task** | Observable `idle→training→ready`; no queue infra. |
| **Stub generation** | **Date-seeded random, data-biased** | Stable per date, reactive to uploads — reads as a real model. |

---

## 10. Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Vite + React 18 + TypeScript + Tailwind CSS |
| Map | Mapbox GL JS (primary), Leaflet + OSM (fallback) |
| FE state / HTTP / routing | Zustand · Axios · React Router v6 |
| Backend | Python 3.11+ · FastAPI · Uvicorn |
| Persistence | SQLite (SQLAlchemy) · raw CSVs on disk |
| ML seam | `Predictor` Protocol — `StubPredictor` now, real model later |
| Deployment | AWS Lightsail VM · Nginx · systemd (optionally Docker) |

---

## 11. Deployment Architecture (AWS Lightsail)

Single VM. Nginx serves the static React build and reverse-proxies `/api/*` to the backend on `:8000`; the backend runs under systemd (or Docker).

```
Internet ─443─▶ Nginx ┬─ /        → /var/www/gridlock/dist/ (SPA fallback → index.html)
                      └─ /api/*   → http://127.0.0.1:8000
                 Backend: uvicorn app.main:app --port 8000  (systemd: gridlock-backend.service)
```

**Provided artifacts** (`backend/deploy/`):
- `nginx-gridlock.conf` — static serve + SPA fallback + `/api` proxy + gzip; **no CORS in Nginx** (backend owns it).
- `gridlock-backend.service` — systemd unit (auto-restart, env file, working dir).
- `Dockerfile` + `.dockerignore` — containerized run as an alternative to bare systemd.
- `DEPLOY.md` — step-by-step: build frontend → SCP `dist/` → install backend deps / run container → write Nginx config → reload. Optional Let's Encrypt (certbot) if a domain exists, else HTTP for the demo.

A `deploy.sh` (frontend build → SCP → nginx write → reload) is in scope as a convenience wrapper.

---

## 12. Environment Variables

**Frontend** (`.env`):

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend base (default `/api`, same-origin via Nginx). |
| `VITE_MAPBOX_TOKEN` | Mapbox token; empty → Leaflet + OSM fallback. |
| `VITE_USE_MOCKS` | `true` → static mock JSON, no live backend. |

**Backend** (`.env`, see `.env.example`):

| Variable | Purpose |
|---|---|
| `DATA_DIR` | Where raw CSVs + SQLite db live (default `./data`). |
| `DATABASE_URL` | SQLite URL (default `sqlite:///./data/gridlock.db`). |
| `RETRAIN_DELAY_S` | Artificial retrain delay so `training` is observable (default ~2). |
| `CORS_ORIGINS` | Allowed frontend origin(s). |
| `PREDICTOR` | Active predictor key (`stub` now; `real` later). |

---

## 13. Change Management — built for overhaul

This is a hackathon. The backend is mid-build and the model does not exist yet. The design assumes both will change and isolates the blast radius:

- **Backend wire shape changes** → frontend touches only `api/types.ts` + `api/mappers.ts`. Process: backend notifies frontend first; additive is safe, rename/retype/remove is breaking; never drift casing, ISO-UTC, or `cell_id` format.
- **The ML model lands or changes** → backend touches only `app/ml/` (implement `Predictor`, flip the registry). Routers, persistence, severity, and the contract are untouched.
- **Grid constants change** → update `backend/app/grid.py` *and* `frontend/src/lib/grid.ts` together; both have tests pinning parity. Never change one alone.
- **UI rearrangement** → pages are thin shells; move JSX in one file. Map and rankings are independent.
- **Storage outgrows SQLite** → swap the persistence layer behind `db.py`/`models.py`; nothing above it changes. (Model state moves from in-memory to DB only if the service scales horizontally — not before.)

When in doubt, change the thing the relevant seam points to, and nothing else.

---

## 14. Scope Boundaries

**In scope (hackathon):**
- CSV upload / delete / listing; model retrain trigger + observable status.
- Date-parameterized hotspot map with percentile severity coloring.
- Two ranked lists (count, congestion impact) with peak-hour forecasts.
- List↔map click interaction; empty / loading / error states.
- Frontend mock mode; **backend stub predictor** so the app runs with no model.
- Single Lightsail VM deployment (Nginx + systemd/Docker).
- Laptop-demo responsive.

**Out of scope:**
- Auth / multi-tenancy; real-time streaming / WebSockets.
- Mobile-optimized UI; multiple cities.
- Historical trend charts / time-series.
- CI/CD; horizontal scaling; job-queue infrastructure.

---

## 15. Code Style & Build Philosophy

Optimize for **readability, modularity, and speed of change** — not longevity or scale. (Full rationale in [`PHILOSOPHY.md`](./PHILOSOPHY.md).)

- **One thing per file**, ~120-line max — frontend and backend alike. Split if exceeded.
- **Flat, obvious names.** A reader knows what a file does from its name.
- **No premature abstraction** — duplicate twice before extracting.
- **Explicit types, no `any`** (TS) / typed Pydantic + signatures (Py).
- **Named exports only** (TS); thin pages/routers, logic in services/stores.
- **Seams are sacred.** The two seams (API mapper, Predictor) are the whole point — keep churn inside them.
- **Prototype-grade, not production-grade.** Handle the happy path well, surface errors visibly (banner / structured error body), and move on.
