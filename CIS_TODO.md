# CIS — Remaining Work

Items deferred from the initial CIS implementation. Each section describes what's needed and where it plugs in.

---

## JunctionBoost

**Status:** DONE — loaded from `api_data/cis_predictions.csv` (training-derived values).

Values: 1.0 (17 zones), 1.5 (23 zones), and 10 zones with fractional values (1.0–1.5 range).

**Future improvement:** derive junction_boost from OSM intersection density or Mappls Nearby API rather than using static training values. Current values are baked into `backend/data/cis_fallback/{cell_id}.json`.

---

## CamerasPerZone

**Status:** defaulting to 1.0 (no normalization applied).

**What it is:** the number of CCTV/enforcement cameras deployed in each zone. Dividing violations by camera count removes surveillance bias — a zone with 10 cameras will naturally report more violations than one with 1.

**Data needed:** CCTV deployment count per zone (from traffic police or municipal data).

**Where it goes:**
- `scripts/compute_cis.py` — load from a `cameras.csv` (cell_id, camera_count)
- Fallback JSON → `"cameras_per_zone"` field
- Formula: `CIS = (vpd / cameras) * (cr-1)^1.25 * jb`

---

## POI Weight

**Status:** available as `--include-poi` flag in the script, OFF by default.

**What it is:** `1 + ln(1 + poi_count)` — multiplier that boosts zones near hospitals, schools, bus stands etc. Captures footfall/sensitivity not reflected in traffic data alone.

**Decision needed:** the formula image (presentation slide) does NOT include POI weight. The existing `cis_pipeline.py` includes it. Decide if it should be part of the official formula or kept as an analysis-only modifier.

**Data source:** `api_data/api_responses_predict/poi_nearby_all.json` — currently all zones return 30 (API cap). May need per-category weighted scoring for differentiation.

---

## Live API Scheduling

**Current:** script runs manually. Backend reads pre-generated fallback files.

**For production:**
- Run `python -m scripts.compute_cis` on a cron (e.g. daily at 02:00) or trigger after each retrain
- Congestion data is date-specific. For forecasting tomorrow, reference_days should be:
  - `prev_day` = today
  - `same_weekday` = same weekday last week
- Update `REFERENCE_DAYS` in the script or accept as CLI args

---

## Mappls API Quota

**Free tier:** 100 calls/day for distance_matrix, 100 for distance_matrix_eta.

**Current usage per run:** ~5 freeflow batches + ~40 traffic batches = 45 calls. Fits in one daily run.

**Scaling:** for more zones (e.g. top 100), batches double. Would need a paid plan or multi-day fetching strategy.

---

## Location Names

**Status:** DONE — `road_name` + `locality` from reverse geocode data are written into fallback JSON and read by `ranking_snapshot.py` to populate `location_name` on hotspots (e.g. "5th Main Road, Gandhi Nagar").

**Future improvement:** for cells not covered by the 50-zone CIS data, location_name remains null. Could run reverse geocode for all chronic cells on a separate pass.
