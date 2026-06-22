# Gridlock — Full Pipeline Guide

This document explains how data flows from a CSV upload to the map and ranking panel. Read this before touching the ML layer, CIS logic, or deployment.

**Audience:** backend, ML, and frontend teammates.  
**Related docs:** `API_CONTRACT.md` (HTTP shapes), `STATUS.md` (deploy checklist), `backend/app/ml/README.md` (predictor seam).

---

## What the system does

Gridlock predicts **where illegal parking is likely tomorrow** and **when to send patrols**, so enforcement can prioritize the highest-impact zones.

The pipeline has three stages:

1. **Violation forecasting** — Spectral Ridge model predicts next-day violations per grid cell.
2. **Impact scoring (CIS)** — Congestion Impact Score ranks the top predicted hotspots by road impact, using external zone data at four times of day.
3. **Display** — Map shows CIS-colored polygons for the top 20 patrol targets; all other cells appear as a muted violation heatmap.

---

## End-to-end flow

```
User uploads CSV (lat, lon, timestamp, violation type)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│  INGEST (synchronous)                                     │
│  • Parse CSV → ViolationRow records in SQLite             │
│  • Map each point to cell_id (300 m × 300 m grid)         │
│  • Dataset status: processing                             │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│  RETRAIN (background, ~2 s delay)                        │
│  1. SpectralRidgePredictor.train(all rows)                  │
│  2. forecast_date = day after last timestamp in data      │
│  3. predict(forecast_date) for all chronic cells            │
│  4. Shortlist top 20 by predicted violations              │
│  5. CIS enrich those 20 only (4 time slots each)          │
│  6. Sort shortlist by CIS → assign ranks 1–20               │
│  7. Save prediction snapshot to disk                      │
│  8. Model status → ready                                  │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│  READ (GET /api/predictions?date=YYYY-MM-DD)              │
│  • Serves stored snapshot — no ML or API calls on read    │
│  • Returns ranked_hotspots + heatmap_cells                │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│  FRONTEND                                                 │
│  • Ranking panel: top 20, ordered by CIS, patrol time     │
│  • Map: CIS-colored polygons (top 20) + violation heatmap │
│  • Hover: violations for heatmap cells; full detail top 20│
└───────────────────────────────────────────────────────────┘
```

---

## Forecast date rule

**The model always predicts the day after the last timestamp in the uploaded data.**

| Last data in CSV | Forecast date | Example use |
|---|---|---|
| 2024-03-31 23:00 | 2024-04-01 | Hackathon demo |

The frontend syncs its date picker to the `date` field returned by the API after fetch.

**No data leakage:** training and features use only hours **up to and including** the last hour of the day before the forecast. The forecast day itself is never used as training input.

---

## Stage 1 — Data ingest

**Entry point:** `POST /api/data/upload`  
**Code:** `backend/app/services/ingest.py`, `backend/app/routers/data.py`

### Expected CSV columns

| Column | Aliases | Required |
|---|---|---|
| `timestamp` | `time`, `datetime`, `date_time` | yes |
| `latitude` | `lat` | yes |
| `longitude` | `lon`, `lng`, `long` | yes |
| `violation` | `violation_type`, `type` | optional |
| `severity` | `severity_src` | optional (not used for output severity) |

### What happens

1. Each row is parsed and assigned a `cell_id` via `point_to_cell_id(lat, lon)`.
2. Rows are stored in SQLite (`violation_rows` table).
3. A background retrain is scheduled (`run_retrain()` in `backend/app/services/retrain.py`).
4. Model status transitions: `ready` → `training` → `ready` (or `idle` if all data deleted).

---

## Stage 2 — Spatial grid

**Shared constants** (backend and frontend must match):

| Constant | Value |
|---|---|
| `CELL_KM` | **0.3** (300 m × 300 m cells) |
| Reference latitude | 13°N (Bangalore) |
| `cell_id` format | `"{i}_{j}"` e.g. `"14345_83842"` |

**Backend:** `backend/app/grid.py`  
**Frontend:** `frontend/src/lib/grid.ts`

The API never sends lat/lon. The frontend derives cell centers and polygon geometry from `cell_id`.

---

## Stage 3 — Violation forecasting (Spectral Ridge)

**Code:** `backend/app/ml/spectral_ridge.py`  
**Config:** `PREDICTOR=spectral` in `.env`

### Model summary

| Parameter | Value |
|---|---|
| Algorithm | Recency-weighted Ridge regression on DFT features |
| Feature window | 72 hours |
| Recency half-life | 2 days (exponential sample weights) |
| Ridge α | 100 |
| Target | `log1p(next-day total violations per cell)` |
| Cells modeled | Chronic only (≥ 30 total violations over history) |

### Feature vector (19 dimensions per cell)

**Spectral (DFT of 72 h hourly counts):**
- DC magnitude, band energies at 24 h / 12 h / 8 h / 6 h periods
- High-frequency residual, total energy
- sin/cos phase at 24 h and 12 h peaks

**Change detection (fast adaptation after interventions):**
- DC ratio (recent 48 h mean / full window mean)
- Spectral flux (recent vs full spectrum distance)
- Band decay at 24 h and 12 h

**Non-spectral:**
- Day-of-week sin/cos, weekend flag
- log1p(2-week rolling cell mean)

### Training (`train(rows)`)

1. Build hourly matrix `(T, N)` from all `ViolationRow` records.
2. Walk forward over historical day-anchors.
3. For each anchor: extract features from preceding 72 h; target = sum of next 24 h.
4. Fit `StandardScaler → Ridge` with recency-weighted samples.

### Inference (`predict(day)`)

1. Anchor = last hour of `day - 1` (e.g. March 31 23:00 for April 1 forecast).
2. Extract features from `[anchor - 71, anchor]`.
3. Predict `log1p(daily total)` per cell → `expm1` → non-negative integer counts.
4. Return `HotspotPrediction` for every chronic cell.

---

## Stage 4 — Shortlist and CIS enrichment

**Code:** `backend/app/services/ranking_snapshot.py`, `backend/app/services/cis.py`

CIS is only computed for the **top 20 cells by predicted violations** to stay within API call limits (20 cells × 4 time slots = 80 calls per ingest).

### Shortlist

```
all predictions  →  sort by violation_count desc  →  take top 20
```

### CIS computation (per shortlisted cell)

Four fixed time slots (configurable via `CIS_TIME_SLOTS` in settings):

```
08:00, 12:00, 17:00, 21:00
```

For each cell:

1. Fetch zone data per slot (API, file fallback, or synthetic placeholder).
2. Compute a score per slot (0–100).
3. **CIS** = average of the 4 slot scores.
4. **Patrol time** = slot with the highest score (shown in the UI as “Deploy: HH:MM”).

### Data source priority

| Priority | Source | When |
|---|---|---|
| 1 | Live CIS API | `CIS_API_KEY` set (stub — not wired yet) |
| 2 | File fallback | `data/cis_fallback/{cell_id}.json` |
| 3 | Synthetic | Deterministic placeholder from violation count |

**Demo note:** place March 31 zone JSON files in `backend/data/cis_fallback/` before ingest. This directory is gitignored (runtime data).

### Final ranking

```
top 20 by violations  →  sort by CIS desc  →  ranks 1–20
```

Severity labels (`low` / `moderate` / `high` / `critical`) are assigned from **CIS percentiles** across the top 20, not from violation count.

### Heatmap cells

All chronic cells **not** in the top 20 are returned as `heatmap_cells` with `violation_count` only (no CIS, no patrol time).

---

## Stage 5 — Snapshot storage

**File:** `data/prediction_snapshot.json` (gitignored)  
**Code:** `backend/app/services/ranking_snapshot.py`

The snapshot is built **once at ingest** and served on every `GET /predictions` without re-running ML or CIS.

```json
{
  "date": "2024-04-01",
  "generated_at": "2026-06-22T18:30:00Z",
  "ranked_hotspots": [
    {
      "cell_id": "14345_83842",
      "violation_count": 142,
      "congestion_impact_score": 87.3,
      "patrol_time": "17:00",
      "rank": 1,
      "severity": "critical",
      "violation_types": [{ "type": "No Parking", "count": 142 }],
      "location_name": null
    }
  ],
  "heatmap_cells": [
    { "cell_id": "14340_83830", "violation_count": 12 }
  ]
}
```

If the requested `date` query param does not match the snapshot date, the API returns empty arrays (not an error).

---

## Stage 6 — API surface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/data/upload` | Upload CSV, trigger retrain |
| `GET` | `/api/model/status` | `idle` / `training` / `ready` |
| `GET` | `/api/predictions?date=YYYY-MM-DD` | Serve snapshot |
| `GET` | `/api/data` | List datasets |
| `DELETE` | `/api/data/{id}` | Delete dataset, retrain |

Full field definitions: `API_CONTRACT.md`.

### Common errors

| Status | Meaning |
|---|---|
| `409` | No model trained yet — upload CSV first |
| `200` + empty arrays | Model trained, but wrong date requested |
| `404` on `/` | Normal — API lives under `/api/*` |

---

## Stage 7 — Frontend display

**Code:** `frontend/src/pages/DashboardPage.tsx`, `HotspotMap.tsx`, `RankingPanel.tsx`

| UI element | Data source | Behavior |
|---|---|---|
| Ranking panel | `ranked_hotspots` | Top 20, CIS order, “Deploy: HH:MM” chip per row |
| Map polygons | `ranked_hotspots` | Top 20 cells, fill colored by CIS |
| Map heatmap | `heatmap_cells` | Muted background, opacity ∝ violation count |
| Hover (heatmap) | `violation_count` only | No CIS shown |
| Hover (ranked) | Full hotspot detail | Violations + CIS + patrol time |
| Date picker | Synced from API `date` | After each successful fetch |

Set `VITE_USE_MOCKS=false` in `frontend/.env` to hit the real backend.

---

## Configuration

### Backend (`.env`)

```env
PREDICTOR=spectral          # use real model (stub still available for tests)
CIS_API_KEY=                # leave empty for fallback/synthetic CIS
CIS_TOP_K=20                # shortlist size
RETRAIN_DELAY_S=2.0         # seconds before retrain starts (UI observable)
CORS_ORIGINS=["http://localhost:5173"]
```

### Frontend (`.env`)

```env
VITE_API_BASE_URL=/api
VITE_USE_MOCKS=false        # true = static JSON, no backend needed
VITE_MAPBOX_TOKEN=          # optional; Leaflet/OSM fallback if empty
```

---

## Local development

### Terminal 1 — Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/api/model/status`

### Terminal 2 — Frontend

```bash
cd frontend
npm ci
# set VITE_USE_MOCKS=false in .env
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` → `localhost:8000` (see `frontend/vite.config.ts`).

### Test flow

1. Go to **Data Management** → upload violations CSV.
2. Wait for status pill: **Training…** → **Ready** (~2–5 s).
3. Dashboard loads predictions for the forecast date.
4. Confirm map polygons + ranking panel match expectations.

### Run tests

```bash
cd backend && python -m pytest tests/ -v
cd frontend && npm run typecheck
```

---

## Deployment

Push to the Gridlock repo does **not** auto-deploy. Follow `STATUS.md` and `backend/deploy/DEPLOY.md`:

1. Build frontend: `npm run build` → `dist/`
2. Copy `dist/` + backend to Lightsail VM
3. Nginx serves SPA at `/`, proxies `/api` → uvicorn on port 8000
4. Set `PREDICTOR=spectral`, `VITE_USE_MOCKS=false` (at build time for frontend)
5. Upload CSV on the live site (or pre-seed data on the VM)

---

## Code map

| Concern | Location |
|---|---|
| CSV parsing | `backend/app/services/ingest.py` |
| Grid math | `backend/app/grid.py`, `frontend/src/lib/grid.ts` |
| Retrain orchestration | `backend/app/services/retrain.py` |
| Spectral Ridge model | `backend/app/ml/spectral_ridge.py` |
| CIS provider | `backend/app/services/cis.py` |
| Snapshot build/serve | `backend/app/services/ranking_snapshot.py` |
| Severity (CIS percentiles) | `backend/app/services/severity.py` |
| Predictions endpoint | `backend/app/routers/predictions.py` |
| Predictor registry | `backend/app/ml/__init__.py` |
| API types (frontend) | `frontend/src/api/types.ts`, `mappers.ts` |
| Map + rankings UI | `frontend/src/components/map/`, `rankings/` |

---

## What is real vs stubbed

| Component | Status |
|---|---|
| CSV ingest + SQLite | ✅ Production-ready |
| 300 m grid | ✅ Aligned backend + frontend |
| Spectral Ridge forecaster | ✅ Implemented |
| Top-20 shortlist + snapshot | ✅ Implemented |
| CIS ranking + patrol time | ✅ Pipeline wired |
| CIS formula | ⚠️ Synthetic placeholder — replace in `cis.py` |
| CIS live API | ⚠️ Stub — wire when API spec + key available |
| March 31 demo fallback files | ⚠️ Manual drop into `data/cis_fallback/` |
| Location names | ⚠️ Always `null` for now |

---

## Open TODOs for the team

1. **CIS script integration** — replace `_synthetic_slot_scores()` in `backend/app/services/cis.py` with the real formula (road capacity × junction complexity × violation density).
2. **API client** — implement `_fetch_cis_api()` when the external API spec is available.
3. **Demo fallback data** — bundle March 31 zone JSON per cell into `data/cis_fallback/` on the deploy VM.
4. **Sample CSV** — add `sample_data/bengaluru_violations.csv` for zero-setup demos.
5. **Pre-seed on startup** (optional) — auto-ingest bundled CSV so judges don't need to upload manually.

---

## Design decisions (why it works this way)

**Why predict at ingest, not on every page load?**  
Retraining and CIS API calls are expensive. The snapshot pattern makes `/api/predictions` fast and predictable for the demo.

**Why top 20 by violations, then rank by CIS?**  
Violations identify *where* activity is likely. CIS identifies *where enforcement matters most* among those candidates. API budget limits CIS to 20 cells.

**Why 300 m cells?**  
Finer spatial resolution for patrol targeting. Matches the ML research pipeline (`CELL_KM = 0.3`).

**Why spectral features?**  
Captures daily/weekly rhythms and adapts quickly when enforcement suppresses a hotspot (change-detection features + recency weighting).

---

## Quick reference — one ingest cycle

```
upload CSV
  → parse rows, assign cell_ids
  → background retrain starts (status: training)
  → spectral ridge fits on all history
  → forecast tomorrow (day after last timestamp)
  → top 20 by predicted violations
  → CIS for those 20 (4 slots → avg + patrol time)
  → sort by CIS, save snapshot
  → status: ready
  → frontend fetches GET /api/predictions?date=<forecast_date>
  → map + ranking panel render
```
