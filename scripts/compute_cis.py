"""
CIS Computation Script — standalone entry point.

Computes Congestion Impact Score for predicted violation hotspots using:
  1. Live Mappls Distance Matrix API (if MAPPLS_CLIENT_ID + SECRET set and auth succeeds)
  2. Cached API responses from api_data/ (fallback for demo)

Usage:
    python -m scripts.compute_cis [OPTIONS]

Options:
    --predictions PATH    Input CSV (default: api_data/demo_april1_2024.csv)
    --top-n N             Number of zones to process (default: 50)
    --include-poi         Include POI weight multiplier
    --output-dir PATH     Output directory (default: scripts/output)
    --no-fallback-write   Skip writing backend/data/cis_fallback/ JSON files
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.cis_compute import (
    compute_cis_raw,
    compute_congestion_ratios,
    compute_slot_ratios,
    normalize_cis,
    patrol_slot_for_cell,
)
from scripts.mappls_client import fetch_all_congestion, get_pair, get_token

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DATA_DIR = PROJECT_ROOT / "api_data"
BACKEND_FALLBACK_DIR = PROJECT_ROOT / "backend" / "data" / "cis_fallback"

REFERENCE_DAYS = {
    "prev_day": "2024-03-31",
    "same_weekday": "2024-03-25",
}
HOURS = [6, 12, 18, 0]


def load_predictions(path: Path, top_n: int) -> dict[str, float]:
    """Load predictions CSV. Returns {cell_id: predicted_violations} for top N zones."""
    df = pd.read_csv(path)
    col = "predicted_violations" if "predicted_violations" in df.columns else "predicted_vpd"
    df["cell_id"] = df["cell_id"].astype(str)
    df = df.sort_values(col, ascending=False).head(top_n)
    return dict(zip(df["cell_id"], df[col].astype(float)))


def load_cached_congestion() -> tuple[dict[str, float], dict[str, dict[int, dict[str, float]]]] | None:
    """Load pre-fetched congestion data from api_data/api_responses_predict/all_hourly_data.json."""
    master_path = API_DATA_DIR / "api_responses_predict" / "all_hourly_data.json"
    if not master_path.exists():
        logger.error("Cached data not found: %s", master_path)
        return None

    master = json.loads(master_path.read_text())
    freeflow = {k: float(v) for k, v in master["freeflow"].items()}

    traffic: dict[str, dict[int, dict[str, float]]] = {}
    for day_label, day_data in master["traffic"].items():
        traffic[day_label] = {}
        for hour_str, zone_data in day_data.items():
            hour = int(hour_str)
            traffic[day_label][hour] = {k: float(v) for k, v in zone_data.items()}

    return freeflow, traffic


def load_reverse_geocode() -> dict[str, dict[str, str]]:
    """Load road names from cached reverse geocode data."""
    path = API_DATA_DIR / "api_responses_predict" / "reverse_geocode_predict.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_poi_data() -> dict[str, float]:
    """Load POI scores from cached nearby API data."""
    path = API_DATA_DIR / "api_responses_predict" / "poi_nearby_all.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {cid: float(info.get("score", 0)) for cid, info in raw.items()}


def load_junction_boost() -> dict[str, float]:
    """Load junction_boost values from existing CIS predictions (training-derived)."""
    path = API_DATA_DIR / "cis_predictions.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path, index_col=0)
    if "junction_boost" not in df.columns:
        return {}
    return df["junction_boost"].to_dict()


def try_live_api(zones: list[str]) -> tuple[dict[str, float], dict[str, dict[int, dict[str, float]]]] | None:
    """Attempt live Mappls API. Returns (freeflow, traffic) or None."""
    client_id = os.environ.get("MAPPLS_CLIENT_ID", "").strip()
    client_secret = os.environ.get("MAPPLS_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        logger.info("MAPPLS_CLIENT_ID/SECRET not set — using cached data")
        return None

    token = get_token(client_id, client_secret)
    if not token:
        logger.warning("Mappls auth failed — falling back to cached data")
        return None

    logger.info("Mappls auth OK — fetching live congestion data")
    pairs = {cid: get_pair(cid) for cid in zones}
    result = fetch_all_congestion(
        token, zones, pairs, REFERENCE_DAYS, HOURS,
        cache_dir=Path("scripts/output/api_cache"),
    )
    return result


def write_fallback_json(
    zones: list[str],
    congestion_ratios: dict[str, float],
    slot_ratios_all: dict[str, dict[int, float]],
    geo_data: dict[str, dict[str, str]],
    junction_boost: dict[str, float] | None = None,
) -> None:
    """Write v2 JSON fallback files to backend/data/cis_fallback/."""
    BACKEND_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)

    for cid in zones:
        cr = congestion_ratios.get(cid, 1.0)
        sr = slot_ratios_all.get(cid, {})
        jb = (junction_boost or {}).get(cid, 1.0)
        patrol = patrol_slot_for_cell(sr)
        geo = geo_data.get(cid, {})

        slot_ratios_str = {f"{h:02d}:00": round(r, 4) for h, r in sr.items()}

        data = {
            "version": 2,
            "congestion_ratio": round(cr, 6),
            "junction_boost": round(jb, 6),
            "cameras_per_zone": 1.0,
            "slot_ratios": slot_ratios_str,
            "patrol_slot": patrol,
            "road_name": geo.get("road", None),
            "locality": geo.get("locality", None),
        }

        path = BACKEND_FALLBACK_DIR / f"{cid}.json"
        path.write_text(json.dumps(data, indent=2))

    logger.info("Wrote %d fallback JSON files to %s", len(zones), BACKEND_FALLBACK_DIR)


def print_rankings(df: pd.DataFrame) -> None:
    """Print ranked CIS table to stdout."""
    print("\n" + "=" * 90)
    print(f"{'RANK':>4}  {'ZONE':<16} {'VPD':>8} {'CONG_R':>7} {'CIS_RAW':>10} {'CIS_NORM':>8}  {'PATROL'}")
    print("-" * 90)
    for _, row in df.iterrows():
        print(
            f"{row['rank']:4.0f}  {row.name:<16} {row['predicted_vpd']:8.2f} "
            f"{row['congestion_ratio']:7.3f} {row['cis_raw']:10.4f} "
            f"{row['cis_normalized']:8.1f}  {row.get('patrol_slot', '-')}"
        )
    print("=" * 90)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Congestion Impact Score")
    parser.add_argument("--predictions", type=Path, default=API_DATA_DIR / "demo_april1_2024.csv")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--include-poi", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/output"))
    parser.add_argument("--no-fallback-write", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load predictions
    logger.info("Loading predictions from %s (top %d)", args.predictions, args.top_n)
    predicted_vpd = load_predictions(args.predictions, args.top_n)
    zones = list(predicted_vpd.keys())
    logger.info("Loaded %d zones", len(zones))

    # 2. Get congestion data (live API or cached fallback)
    result = try_live_api(zones)
    if result is None:
        logger.info("Loading cached congestion data from api_data/")
        result = load_cached_congestion()
        if result is None:
            logger.error("No congestion data available. Exiting.")
            sys.exit(1)

    freeflow, traffic = result
    available_zones = [z for z in zones if z in freeflow]
    logger.info("Congestion data available for %d/%d zones", len(available_zones), len(zones))

    # 3. Compute congestion ratios
    congestion_ratios = compute_congestion_ratios(freeflow, traffic)
    slot_ratios_all = compute_slot_ratios(freeflow, traffic)

    # 4. Load junction boost (from training-derived data)
    junction_boost = load_junction_boost()
    jb_available = sum(1 for z in zones if z in junction_boost)
    if jb_available:
        logger.info("Junction boost loaded for %d/%d zones", jb_available, len(zones))
    else:
        logger.info("No junction boost data — using 1.0 default")
        junction_boost = None

    # 5. Compute raw CIS
    cis_raw = compute_cis_raw(predicted_vpd, congestion_ratios, junction_boost=junction_boost)

    # 6. Optional POI weight
    if args.include_poi:
        poi_data = load_poi_data()
        for cid in cis_raw:
            poi_score = poi_data.get(cid, 0)
            poi_weight = 1 + np.log1p(poi_score)
            cis_raw[cid] *= poi_weight

    # 7. Normalize
    cis_normalized = normalize_cis(cis_raw)

    # 8. Build output DataFrame
    df = pd.DataFrame(index=zones)
    df.index.name = "cell_id"
    df["predicted_vpd"] = pd.Series(predicted_vpd)
    df["congestion_ratio"] = pd.Series(congestion_ratios)
    df["junction_boost"] = pd.Series({cid: (junction_boost or {}).get(cid, 1.0) for cid in zones})
    df["cis_raw"] = pd.Series(cis_raw)
    df["cis_normalized"] = pd.Series(cis_normalized)

    for cid in zones:
        sr = slot_ratios_all.get(cid, {})
        df.loc[cid, "patrol_slot"] = patrol_slot_for_cell(sr)

    df["rank"] = df["cis_normalized"].rank(ascending=False).astype(int)
    df = df.sort_values("cis_normalized", ascending=False)

    # 9. Write outputs
    out_csv = args.output_dir / "cis_predictions.csv"
    df.to_csv(out_csv)
    logger.info("Wrote %s", out_csv)

    # 10. Write fallback JSONs for backend
    if not args.no_fallback_write:
        geo_data = load_reverse_geocode()
        write_fallback_json(zones, congestion_ratios, slot_ratios_all, geo_data, junction_boost)

    # 11. Print results
    print_rankings(df)

    print(f"\nFormula: CIS = predicted_vpd x max(congestion_ratio - 1, 0.01)^1.25 x junction_boost")
    if args.include_poi:
        print(f"         (with POI weight: 1 + ln(1 + poi_score))")
    print(f"\nOutput: {out_csv}")
    if not args.no_fallback_write:
        print(f"Backend fallback: {BACKEND_FALLBACK_DIR}/")


if __name__ == "__main__":
    main()
