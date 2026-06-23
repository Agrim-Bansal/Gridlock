"""Mappls Distance Matrix API client with caching and graceful quota handling."""

from __future__ import annotations

import json
import math
import os
import time
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

MAPPLS_TOKEN_URL = "https://outpost.mappls.com/api/security/oauth/token"
MAPPLS_DM_BASE = "https://apis.mappls.com/advancedmaps/v1"

CELL_M = 300.0
LAT_STEP = CELL_M / 111_000.0
LON_STEP = CELL_M / (111_000.0 * math.cos(math.radians(13.0)))


def get_token(client_id: str, client_secret: str) -> str | None:
    """Authenticate with Mappls OAuth. Returns access token or None on failure."""
    try:
        resp = requests.post(
            MAPPLS_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.warning("Mappls auth failed: %s", e)
        return None


def cell_center(cell_id: str) -> tuple[float, float]:
    i, j = map(int, cell_id.split("_"))
    return (i * LAT_STEP, j * LON_STEP)


def get_pair(cell_id: str, shift_m: float = 300.0) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return (src, dst) coordinate pair for diagonal duration measurement."""
    lat, lon = cell_center(cell_id)
    dlon = shift_m / (111_000 * math.cos(math.radians(lat)))
    return (lat, lon), (lat, lon + dlon)


def group_zones_by_locality(zones: list[str], batch_size: int = 10) -> list[list[str]]:
    """Sort zones spatially and chunk into batches for efficient API calls."""
    coords = []
    for cid in zones:
        i, j = map(int, cid.split("_"))
        coords.append((cid, i, j))

    coarse = CELL_M * 5
    lat_step_int = max(1, round(coarse / 111_000.0 / LAT_STEP))
    lon_step_int = max(1, round(coarse / (111_000.0 * math.cos(math.radians(13.0))) / LON_STEP))
    coords.sort(key=lambda x: (x[1] // lat_step_int, x[2] // lon_step_int, x[1], x[2]))

    sorted_zones = [c[0] for c in coords]
    return [sorted_zones[i:i + batch_size] for i in range(0, len(sorted_zones), batch_size)]


def call_distance_matrix(
    token: str,
    zone_batch: list[str],
    pairs: dict[str, tuple],
    resource: str,
    date_time: str | None = None,
) -> dict[str, float] | None:
    """Call Mappls Distance Matrix for a batch. Returns {cell_id: duration} or None."""
    coords_parts = []
    for cid in zone_batch:
        src, _ = pairs[cid]
        coords_parts.append(f"{src[1]:.6f},{src[0]:.6f}")
    for cid in zone_batch:
        _, dst = pairs[cid]
        coords_parts.append(f"{dst[1]:.6f},{dst[0]:.6f}")

    n = len(zone_batch)
    url = f"{MAPPLS_DM_BASE}/{token}/{resource}/driving/{';'.join(coords_parts)}"
    params = {
        "sources": ";".join(str(i) for i in range(n)),
        "destinations": ";".join(str(i) for i in range(n, 2 * n)),
        "rtype": 0,
        "region": "ind",
    }
    if date_time:
        params["date_time"] = date_time

    try:
        resp = requests.get(url, params=params, timeout=30)
    except requests.RequestException as e:
        logger.warning("Distance matrix request failed: %s", e)
        return None

    if resp.status_code == 401:
        logger.warning("Mappls 401 — quota exhausted")
        return None
    if resp.status_code != 200:
        logger.warning("Mappls error %d: %s", resp.status_code, resp.text[:200])
        return None

    data = resp.json()
    if data.get("responseCode") and data["responseCode"] != 200:
        logger.warning("Mappls API error code: %s", data.get("responseCode"))
        return {cid: 0 for cid in zone_batch}

    durations = data["results"]["durations"]
    return {cid: durations[i][i] for i, cid in enumerate(zone_batch)}


def _save_cache(data: dict, cache_dir: Path, filename: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / filename).write_text(json.dumps(data, indent=2))


def _load_cache(cache_dir: Path, filename: str) -> dict | None:
    path = cache_dir / filename
    if path.exists():
        return json.loads(path.read_text())
    return None


def fetch_all_congestion(
    token: str,
    zones: list[str],
    pairs: dict[str, tuple],
    reference_days: dict[str, str],
    hours: list[int],
    batch_size: int = 10,
    cache_dir: Path | None = None,
) -> tuple[dict[str, float], dict[str, dict[int, dict[str, float]]]] | None:
    """
    Fetch freeflow + traffic for all zones across reference days and hours.
    Returns (freeflow, traffic) or None on total failure.
    traffic structure: {day_label: {hour: {cell_id: duration}}}
    """
    if cache_dir is None:
        cache_dir = Path("scripts/output/api_cache")

    batches = group_zones_by_locality(zones, batch_size)
    quota_hit = False

    # --- Freeflow ---
    freeflow: dict[str, float] = {}
    for idx, batch in enumerate(batches):
        fname = f"freeflow_batch_{idx}.json"
        cached = _load_cache(cache_dir, fname)
        if cached:
            raw = cached.get("raw_response", cached)
            for i, cid in enumerate(batch):
                freeflow[cid] = raw["results"]["durations"][i][i]
        elif not quota_hit:
            result = call_distance_matrix(token, batch, pairs, "distance_matrix")
            if result is None:
                quota_hit = True
                continue
            _save_cache(
                {"zone_ids": list(batch), "raw_response": {"results": {"durations": [[result[cid]] for cid in batch]}}, "parsed": result},
                cache_dir, fname,
            )
            freeflow.update(result)
            time.sleep(0.5)

    if not freeflow:
        return None

    # --- Traffic per reference day per hour ---
    traffic: dict[str, dict[int, dict[str, float]]] = {}
    for day_label, date_str in reference_days.items():
        traffic[day_label] = {}
        for hour in hours:
            dt = f"{date_str}T{hour:02d}:00"
            traffic[day_label][hour] = {}
            for idx, batch in enumerate(batches):
                fname = f"traffic_{day_label}_h{hour:02d}_batch_{idx}.json"
                cached = _load_cache(cache_dir, fname)
                if cached:
                    raw = cached.get("raw_response", cached)
                    for i, cid in enumerate(batch):
                        traffic[day_label][hour][cid] = raw["results"]["durations"][i][i]
                elif not quota_hit:
                    result = call_distance_matrix(
                        token, batch, pairs, "distance_matrix_eta", date_time=dt
                    )
                    if result is None:
                        quota_hit = True
                        continue
                    _save_cache(
                        {"zone_ids": list(batch), "day": day_label, "hour": hour,
                         "date_time": dt, "parsed": result},
                        cache_dir, fname,
                    )
                    traffic[day_label][hour].update(result)
                    time.sleep(0.5)

    return freeflow, traffic
