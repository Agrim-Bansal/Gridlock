# Gridlock — API Contract

**Audience:** the Python ML backend team.
**Status:** authoritative. This document is the source of truth for the HTTP boundary between the Gridlock frontend and the backend service.

The frontend is already built against this contract. Every shape below is what the frontend's API layer (`src/api/types.ts` + `src/api/mappers.ts`) parses today. If the backend returns a different shape, the frontend's mapper layer absorbs it — but **only if the backend tells the frontend team first**. Treat field names, casing, types, and enum values as a binding interface. Silent shape changes break the UI.

> Why this matters: the frontend never invents lat/lon, never recomputes severity, and never derives peak hours. It renders exactly what this API returns. The model's output *is* the product. This contract is the seam.

---

## 0. Conventions

| Concern | Rule |
|---|---|
| Base path | All endpoints are served under `/api` (Nginx reverse-proxies `/api/*` → `127.0.0.1:8000`). Paths below are written **with** the `/api` prefix as the client sees them. |
| Encoding | All request/response bodies are `application/json; charset=utf-8`, except file upload which is `multipart/form-data`. |
| Field casing | **`snake_case`** for every JSON field. The frontend maps to `camelCase` internally; do not send `camelCase`. |
| Timestamps | ISO 8601 UTC with `Z` suffix: `"2026-06-20T10:35:00Z"`. Not epoch, not local time. |
| Dates | Calendar dates are `"YYYY-MM-DD"` (no time component). |
| Numbers | `violation_count` and `expected_violations` are integers. `congestion_impact_score` is a float (0–100). |
| Null vs omit | A nullable field may be `null` or omitted entirely — the frontend treats both the same. A required field must always be present and non-null. |
| Times of day | Peak-hour `start`/`end` are 24-hour `"HH:MM"` strings (e.g. `"08:00"`, `"17:30"`). The frontend formats these for display; send raw 24h. |
| CORS | The backend owns CORS headers (Nginx does not add them). Allow the frontend origin, methods `GET, POST, DELETE`, and `Content-Type` headers. |
| Trailing slash | Endpoints are matched **without** trailing slashes (`/api/data`, not `/api/data/`). |

---

## 1. Endpoint summary

| # | Method | Path | Purpose |
|---|---|---|---|
| 1 | `GET` | `/api/predictions?date=YYYY-MM-DD` | Predicted violation hotspots for a date — the core feature. |
| 2 | `GET` | `/api/model/status` | Current model training state. |
| 3 | `GET` | `/api/data` | List uploaded training datasets. |
| 4 | `POST` | `/api/data/upload` | Upload a CSV; triggers retrain. |
| 5 | `DELETE` | `/api/data/{id}` | Delete a dataset; triggers retrain. |

That is the entire surface. The frontend makes no other calls. There is no auth, no pagination, no websockets.

---

## 2. `GET /api/predictions` — the core endpoint

This is the primary driving feature. Everything the dashboard renders — the map overlay, both ranked lists, the cell popups, the peak-hour chips — comes from this single response.

### Request

```
GET /api/predictions?date=2026-06-20
```

| Param | In | Required | Type | Notes |
|---|---|---|---|---|
| `date` | query | **yes** | `YYYY-MM-DD` | The day to predict for. The model produces per-day density estimates; predictions differ weekday vs weekend and seasonally. If missing, return `400` (see §6). |

The frontend always sends a single `date`. No range, no multi-date.

### Response `200`

```json
{
  "date": "2026-06-20",
  "generated_at": "2026-06-20T10:36:00Z",
  "ranked_hotspots": [
    {
      "cell_id": "14345_83842",
      "location_name": "Silk Board Junction",
      "violation_count": 342,
      "violation_types": [
        { "type": "Signal Jumping", "count": 145 },
        { "type": "Wrong Lane", "count": 98 },
        { "type": "Overspeeding", "count": 99 }
      ],
      "severity": "critical",
      "congestion_impact_score": 94.7,
      "patrol_time": "17:30",
      "peak_hours": [
        { "start": "08:00", "end": "09:30", "expected_violations": 85 },
        { "start": "17:30", "end": "19:00", "expected_violations": 120 }
      ]
    }
  ],
  "heatmap_cells": [
    { "cell_id": "14335_83855", "violation_count": 163 },
    { "cell_id": "14310_83820", "violation_count": 142 }
  ]
}
```

### Top-level fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `date` | `string` (`YYYY-MM-DD`) | yes | Echo of the requested date (or the model's default **forecast date** — the day after the last training-data timestamp — when the client has no prior context). Must equal the query param when one was sent. |
| `generated_at` | `string` (ISO 8601 UTC) | yes | When this prediction set was computed. |
| `ranked_hotspots` | `Hotspot[]` | yes | Top 20 cells by predicted violations, **sorted by `congestion_impact_score` descending**. Rendered as colored polygons on the map and in the ranking panel. **May be empty** (`[]`). |
| `heatmap_cells` | `HeatmapCell[]` | yes | All other predicted cells (not in top 20). Rendered as a suppressed background heatmap (violation count only). **May be `[]`**. |
| `hotspots` | `Hotspot[]` | optional | **Legacy.** Single combined array. If `ranked_hotspots` is absent, the frontend treats `hotspots` as `ranked_hotspots` and `heatmap_cells` as `[]`. |

### `Hotspot` object

| Field | Type | Required | Meaning |
|---|---|---|---|
| `cell_id` | `string` | **yes** | Grid cell identifier, format `"{i}_{j}"` (see §5). The frontend derives all geometry from this — no lat/lon is sent. |
| `location_name` | `string \| null` | optional | Nearest landmark name. May be `null` or omitted; the frontend falls back to showing the raw `cell_id`. |
| `violation_count` | `integer` | **yes** | Total predicted violations in this cell on `date`. Drives the "By Violations" ranking and is the basis for severity coloring. |
| `violation_types` | `ViolationType[]` | **yes** | Breakdown of `violation_count` by category. May be `[]`. The counts should sum to (≈) `violation_count`; the frontend does not enforce this but the popup shows both. |
| `severity` | `enum` | **yes** | One of `"low" \| "moderate" \| "high" \| "critical"`. **Computed by the backend** from violation-count percentiles across all cells for this date (see §2.2). The frontend renders this verbatim — it does not recompute. |
| `congestion_impact_score` | `float` | **yes** | 0–100 composite score (road capacity × junction complexity × violation density). Drives map polygon color and ranking order. One decimal place is typical (e.g. `94.7`). |
| `patrol_time` | `string` (`HH:MM`, 24h) \| `null` | optional | Recommended patrol deployment time for this cell (e.g. `"17:30"`). Shown in the ranking panel and ranked-cell popups. May be `null` or omitted. |
| `peak_hours` | `PeakHour[]` | **yes** | Forecasted high-density time windows. **May be `[]`** (a cell can have zero peak windows). |

### `HeatmapCell` object

| Field | Type | Required | Meaning |
|---|---|---|---|
| `cell_id` | `string` | **yes** | Grid cell identifier (§5). |
| `violation_count` | `integer` | **yes** | Predicted violations in this cell on `date`. Used for suppressed heatmap rendering only. |

### `ViolationType` object

| Field | Type | Required | Meaning |
|---|---|---|---|
| `type` | `string` | yes | Human-readable category, e.g. `"Signal Jumping"`, `"Wrong Lane"`, `"Overspeeding"`. Free-form string — the frontend displays it as-is and does not enum-validate. Use Title Case for display quality. |
| `count` | `integer` | yes | Predicted violations of this type in this cell on `date`. |

### `PeakHour` object

| Field | Type | Required | Meaning |
|---|---|---|---|
| `start` | `string` (`HH:MM`, 24h) | yes | Window start, e.g. `"08:00"`. |
| `end` | `string` (`HH:MM`, 24h) | yes | Window end, e.g. `"09:30"`. Must be after `start` on the same day (no overnight wrap). |
| `expected_violations` | `integer` | yes | Expected violations during this window, from rolling averages of historical patterns. Shown on the chip and in the popup. |

### 2.1 Ordering

- **`ranked_hotspots`** must be pre-sorted by `congestion_impact_score` descending. The frontend renders this order as-is (no client re-sort).
- **`heatmap_cells`** ordering is not contractually required.
- Legacy **`hotspots`**: the frontend re-sorted client-side in older builds; prefer the split arrays above.

### 2.2 Map rendering split

- **`ranked_hotspots`** (max 20): drawn as **polygons** on the map, fill color derived from `congestion_impact_score` (not `severity`).
- **`heatmap_cells`**: drawn as a **suppressed background heatmap** from `violation_count` only (muted color, low opacity). Hover shows predicted violations.
- **`severity`** is still returned for ranked cells (ranking row tint) but map polygon color follows CIS bands.

### 2.3 Severity semantics (backend-owned)

`severity` is **not** an absolute threshold — it is percentile-based across the cells returned for the given date, so the palette adapts to any dataset. Recommended mapping (matches the UI design):

| Severity | Percentile band of `violation_count` |
|---|---|
| `critical` | top 10% |
| `high` | 70th–90th percentile |
| `moderate` | 40th–70th percentile |
| `low` | bottom 40% |

The frontend uses this field for ranking-row background tint. If the backend cannot compute percentiles, it must still send a valid enum value for every ranked hotspot.

### 2.4 What NOT to send

- **No `latitude` / `longitude`.** Geometry is derived from `cell_id` client-side (§5). Sending coordinates is ignored.
- **No GeoJSON.** The frontend builds the polygons.
- **No styling/color fields.** Color is derived client-side from `congestion_impact_score` (map) and `severity` (list tint).

### 2.5 Empty result

If the model has no hotspots for the requested date, return `200` with `"ranked_hotspots": []` and `"heatmap_cells": []`. This renders the calm "No hotspots predicted for this date" state — it is **not** an error. Reserve non-2xx codes for the cases in §6 (e.g. no model trained yet → `409`).

---

## 3. `GET /api/model/status`

Drives the status bar pill (`Idle` / `Training…` / `Ready`), the "last trained" label, and dataset count. Polled by the frontend after uploads/deletes to watch the retrain finish.

### Response `200`

```json
{
  "status": "ready",
  "last_trained_at": "2026-06-20T10:35:00Z",
  "dataset_count": 3,
  "total_rows": 46470
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `status` | `enum` | **yes** | `"idle" \| "training" \| "ready"`. `idle` = no model trained yet (no usable predictions). `training` = retrain in progress. `ready` = model is current and `/api/predictions` will return results. |
| `last_trained_at` | `string \| null` (ISO 8601 UTC) | **yes** | Timestamp of last successful train. **`null` when never trained** (i.e. `status` = `idle`). |
| `dataset_count` | `integer` | **yes** | Number of datasets currently contributing to the model. |
| `total_rows` | `integer` | **yes** | Sum of rows across all active datasets. |

### State machine the frontend assumes

```
idle ──upload──▶ training ──success──▶ ready
 ▲                  │                    │
 │                  └──(all data deleted)─┘
 └──────────────── delete last dataset ──┘
```

- After a successful `POST /upload` or `DELETE`, `status` should transition to `training`, then `ready` (or back to `idle` if no datasets remain).
- The frontend polls this endpoint to detect the `training → ready` edge. Make the transition observable (don't jump straight back to `ready` synchronously if a retrain is actually running).

---

## 4. Data management endpoints

### 4.1 `GET /api/data` — list datasets

#### Response `200`

```json
{
  "datasets": [
    {
      "id": "d_abc123",
      "filename": "traffic_jan2024.csv",
      "uploaded_at": "2026-06-20T10:30:00Z",
      "row_count": 15420,
      "status": "active"
    }
  ]
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `datasets` | `Dataset[]` | yes | All uploaded datasets. May be `[]`. |

#### `Dataset` object

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | `string` | yes | Stable unique id. Used as the path param for delete and as the React list key. Convention `"d_..."` but any stable string works. |
| `filename` | `string` | yes | Original uploaded file name. |
| `uploaded_at` | `string` (ISO 8601 UTC) | yes | Upload time. |
| `row_count` | `integer` | yes | Parsed row count of the CSV. |
| `status` | `enum` | yes | `"processing" \| "active"`. `processing` = still ingesting/validating; the frontend disables the delete button and shows a spinner. `active` = ready and contributing to the model. |

### 4.2 `POST /api/data/upload` — upload a CSV

#### Request

```
POST /api/data/upload
Content-Type: multipart/form-data

file: <binary .csv>
```

- The form field name is exactly **`file`**.
- Exactly one file per request.
- Expected content type `text/csv`; accept by extension `.csv` as well.

#### Response `201`

```json
{
  "id": "d_abc123",
  "filename": "traffic_jan2024.csv",
  "uploaded_at": "2026-06-20T10:30:00Z",
  "row_count": 15420,
  "status": "processing"
}
```

Same shape as a single `Dataset` (§4.1). Typically returned with `status: "processing"` since ingest + retrain kick off asynchronously. The frontend then polls `GET /api/model/status` and/or re-fetches `GET /api/data` to observe completion.

> The upload **triggers a model retrain** as a side effect. There is no separate "train" endpoint.

#### Expected CSV input format

The uploaded file is the model's training data. Based on the CSV preview in the UI design, each row is a historical violation event. Recommended/expected columns:

| Column | Type | Notes |
|---|---|---|
| `timestamp` | datetime | When the violation occurred (date + time; the time component feeds peak-hour forecasting). |
| `latitude` | float | Event latitude. The backend maps this to a grid `cell_id` (§5) during ingest. |
| `longitude` | float | Event longitude. |
| `violation` | string | Violation type, e.g. `Signal Jump`, `Wrong Lane`, `Overspeeding`. |
| `severity` | string | Optional source severity (`low`/`moderate`/`high`/`critical`). The model's output severity is recomputed per §2.2 and is independent of this column. |

> **Note:** lat/lon appear only in the *training input*. They never appear in the *prediction output* — output is keyed purely by `cell_id`. If the backend's actual training schema differs, document it here so the frontend's CSV preview/validation can match.

### 4.3 `DELETE /api/data/{id}` — delete a dataset

#### Request

```
DELETE /api/data/d_abc123
```

| Param | In | Required | Notes |
|---|---|---|---|
| `id` | path | yes | The `Dataset.id` from `GET /api/data`. |

#### Response `200`

```json
{
  "message": "Dataset deleted. Model retrain initiated.",
  "retrain_status": "training"
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `message` | `string` | yes | Human-readable confirmation. The frontend may surface it but does not parse it. |
| `retrain_status` | `string` | yes | Post-delete model state, typically `"training"`. The frontend then polls `GET /api/model/status`. |

> The frontend currently **ignores the delete response body** and only checks for a 2xx status. The body above is the contract regardless, so other clients/logs stay consistent. Deleting **triggers a retrain** (or returns the model to `idle` if it was the last dataset).

Deleting a non-existent `id` → `404` (see §6).

---

## 5. Grid cell system (shared source of truth)

Every prediction is tied to a 300m × 300m grid cell, never an arbitrary point. The grid math is **shared** between backend and frontend — the backend is the source of truth, and the frontend mirrors these exact constants in `src/lib/grid.ts`.

```python
CELL_KM        = 0.3
KM_PER_DEG_LAT = 111.0
COS_LAT        = cos(radians(13.0))            # reference latitude 13°N
LAT_STEP       = CELL_KM / KM_PER_DEG_LAT       # ≈ 0.0027027°
LON_STEP       = CELL_KM / (KM_PER_DEG_LAT * COS_LAT)  # ≈ 0.0027738°

# point → cell_id
i = round(lat / LAT_STEP)
j = round(lon / LON_STEP)
cell_id = f"{i}_{j}"

# cell_id → center (frontend recovers this; backend must use the same rule)
lat = i * LAT_STEP
lon = j * LON_STEP
```

### Contract rules

- **`cell_id` format is exactly `"{i}_{j}"`** — two integers joined by a single underscore, no padding, no sign prefix beyond a literal `-` if negative. The frontend does `cellId.split("_").map(Number)`; anything else breaks geometry.
- `i` is the latitude index, `j` is the longitude index. Order matters.
- Example: `"14345_83842"` → center ≈ `(12.917°N, 77.623°E)`.
- **If the backend ever changes `CELL_KM` or the reference latitude (13°N), it must notify the frontend team** so `src/lib/grid.ts` is updated in lockstep. A mismatch silently misplaces every cell on the map.

---

## 6. Errors

The frontend uses a bare Axios client (`src/api/client.ts`) with no custom interceptor today, so it relies on **HTTP status codes** to distinguish success from failure. Use standard codes:

| Code | When | Frontend behavior |
|---|---|---|
| `400 Bad Request` | Missing/invalid `date` on `/predictions`; malformed request. | Error banner + retry. |
| `404 Not Found` | `DELETE` on unknown dataset id. | Error surfaced. |
| `409 Conflict` | `/predictions` requested but no model is trained yet (`status: idle`). | Prefer this over an empty `200` so the UI can show the "train model first" empty state distinctly from "no hotspots for this date". |
| `415 Unsupported Media Type` | Upload of a non-CSV file. | Upload error. |
| `422 Unprocessable Entity` | CSV present but unparseable / missing required columns. | Upload error with detail. |
| `500 Internal Server Error` | Model/inference failure. | Error banner: "Failed to fetch predictions. Check backend connection." + retry. |
| `503 Service Unavailable` | Backend up but model busy/unavailable. | Same banner + retry. |

### Error body shape

For any non-2xx, return a JSON body the frontend (and logs) can read:

```json
{
  "error": "missing_date",
  "message": "Query param 'date' is required (YYYY-MM-DD)."
}
```

| Field | Type | Meaning |
|---|---|---|
| `error` | `string` | Stable machine-readable code (snake_case). |
| `message` | `string` | Human-readable explanation. |

> Distinction that matters for UX: **empty `200` with `ranked_hotspots: []` and `heatmap_cells: []`** = "model ran, nothing predicted for this date" (calm informational state). **`409`** = "no model trained yet" (CTA to upload data). Do not conflate them.

---

## 7. Changing this contract

This contract is provisional and the backend is under active development. When a shape changes:

1. **Tell the frontend team.** The frontend's `src/api/types.ts` (raw types) and `src/api/mappers.ts` (raw → domain conversion) are the only files that must change to absorb it — but they must be changed deliberately.
2. Adding a field is safe (the mapper ignores unknowns). Renaming, retyping, or removing a field is breaking.
3. Keep field casing `snake_case`, timestamps ISO-UTC, and `cell_id` format `"{i}_{j}"` — these are load-bearing across the whole UI.
4. Endpoint URL or split/merge changes are fine as long as the frontend's exported function signatures (`fetchPredictions(date)`, `listDatasets()`, `uploadDataset(file)`, `deleteDataset(id)`, `getModelStatus()`) can stay stable.

---

## 8. Quick reference (copy-paste schemas)

```ts
// GET /api/predictions?date=YYYY-MM-DD  → 200
{
  date: string;                 // "YYYY-MM-DD" — forecast date (day after last training data)
  generated_at: string;         // ISO 8601 UTC
  ranked_hotspots: Array<{
    cell_id: string;            // "{i}_{j}"
    location_name?: string | null;
    violation_count: number;    // int
    violation_types: Array<{ type: string; count: number }>;
    severity: "low" | "moderate" | "high" | "critical";
    congestion_impact_score: number;  // float 0–100, sorted desc
    patrol_time?: string | null;      // "HH:MM" recommended deploy time
    peak_hours: Array<{ start: string; end: string; expected_violations: number }>;
  }>;
  heatmap_cells: Array<{
    cell_id: string;
    violation_count: number;
  }>;
  hotspots?: Array<...>;        // legacy — same shape as ranked_hotspots entry
}

// GET /api/model/status  → 200
{
  status: "idle" | "training" | "ready";
  last_trained_at: string | null;   // ISO 8601 UTC, null if never trained
  dataset_count: number;            // int
  total_rows: number;               // int
}

// GET /api/data  → 200
{
  datasets: Array<{
    id: string;
    filename: string;
    uploaded_at: string;            // ISO 8601 UTC
    row_count: number;              // int
    status: "processing" | "active";
  }>;
}

// POST /api/data/upload  (multipart: file=<.csv>)  → 201
{
  id: string;
  filename: string;
  uploaded_at: string;
  row_count: number;
  status: "processing" | "active";
}

// DELETE /api/data/{id}  → 200
{
  message: string;
  retrain_status: string;           // e.g. "training"
}

// Any non-2xx
{
  error: string;                    // snake_case code
  message: string;
}
```
