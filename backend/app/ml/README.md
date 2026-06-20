# ML Predictor Seam

This directory is where the real ML model drops in.

## What the model receives

`train(rows: list[ViolationRow])` — every parsed violation row across all active datasets. Each row has:
- `timestamp` (datetime)
- `cell_id` (string, format `"{i}_{j}"`)
- `violation_type` (string or None)
- `severity_src` (string or None — the CSV's source severity, not the output severity)

Raw CSV files are also available on disk under `data/` if the model prefers to read them directly.

## What the model must return

`predict(day: date) -> list[HotspotPrediction]` with these fields per hotspot:
- `cell_id` — grid cell identifier
- `violation_count` — predicted total violations (integer)
- `violation_types` — `[{"type": str, "count": int}]` breakdown
- `congestion_impact_score` — float 0–100
- `peak_hours` — `[{"start": "HH:MM", "end": "HH:MM", "expected_violations": int}]`
- `location_name` — optional landmark name (string or None)

**Do NOT return `severity`.** The service layer computes it from percentiles.

## How to add a real model

1. Create `real.py` in this directory implementing the `Predictor` protocol
2. Add `"real": RealPredictor` to `_REGISTRY` in `__init__.py`
3. Set `PREDICTOR=real` in `.env`

No router, service, or persistence changes needed.
