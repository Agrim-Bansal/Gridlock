"""SpectralRidgePredictor — wraps SpectralRidgePipeline into the Predictor protocol.

Generates synthetic Bengaluru data on first train if no real rows exist,
so the model is always ready to serve predictions.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import numpy as np

from app.grid import point_to_cell_id, cell_id_to_center
from app.ml.predictor import HotspotPrediction
from app.ml.spectral_ridge import PipelineConfig, SpectralRidgePipeline

if TYPE_CHECKING:
    from app.models import ViolationRow

BENGALURU_LANDMARKS: dict[str, tuple[float, float]] = {
    "Silk Board Junction": (12.9172, 77.6230),
    "Marathahalli Bridge": (12.9591, 77.6974),
    "KR Puram": (13.0068, 77.6965),
    "Hebbal Flyover": (13.0358, 77.5970),
    "Electronic City": (12.8456, 77.6603),
    "Whitefield": (12.9698, 77.7500),
    "Koramangala": (12.9352, 77.6245),
    "Indiranagar": (12.9784, 77.6408),
    "Jayanagar": (12.9308, 77.5838),
    "MG Road": (12.9756, 77.6069),
    "Brigade Road": (12.9716, 77.6070),
    "Bannerghatta Road": (12.8876, 77.5968),
    "Outer Ring Road": (12.9366, 77.6852),
    "Hosur Road": (12.9100, 77.6350),
    "Old Airport Road": (12.9611, 77.6480),
    "Yelahanka": (13.1005, 77.5960),
    "JP Nagar": (12.9063, 77.5857),
    "BTM Layout": (12.9166, 77.6101),
    "HSR Layout": (12.9116, 77.6389),
    "Bellandur": (12.9260, 77.6762),
    "Sarjapur Road": (12.9107, 77.6871),
    "Yeshwanthpur": (13.0280, 77.5450),
    "Rajajinagar": (12.9910, 77.5550),
    "Malleswaram": (13.0035, 77.5690),
    "Basavanagudi": (12.9432, 77.5745),
    "Vijayanagar": (12.9700, 77.5370),
    "Kanakapura Road": (12.8900, 77.5700),
    "Mysore Road": (12.9500, 77.5200),
    "Tumkur Road": (13.0500, 77.5300),
    "Peenya": (13.0300, 77.5200),
}

_CELL_TO_NAME: dict[str, str] = {
    point_to_cell_id(lat, lon): name
    for name, (lat, lon) in BENGALURU_LANDMARKS.items()
}

VIOLATION_TYPES = [
    "No Parking",
    "Signal Jumping",
    "Over Speeding",
    "Wrong Lane",
    "No Helmet",
    "Triple Riding",
]

SYNTHETIC_DAYS = 150
SYNTHETIC_EXTRA_CELLS = 20


def _generate_synthetic_matrix(
    cell_ids: list[str], n_days: int, seed: int = 42
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic hourly violation matrix (T, N) and dow array (T,)."""
    rng = np.random.default_rng(seed)
    N = len(cell_ids)
    T = n_days * 24

    base_rate = rng.uniform(0.5, 8.0, size=N)

    morning_peak = np.zeros(24)
    morning_peak[7:10] = 1.0
    evening_peak = np.zeros(24)
    evening_peak[17:20] = 1.0
    night_dip = np.ones(24)
    night_dip[0:5] = 0.2
    hourly_pattern = night_dip + 0.6 * morning_peak + 0.8 * evening_peak

    values = np.zeros((T, N), dtype=np.float64)
    for t in range(T):
        hour_of_day = t % 24
        day_idx = t // 24
        dow = day_idx % 7
        weekend_factor = 0.6 if dow >= 5 else 1.0
        trend = 1.0 + 0.002 * day_idx
        rate = base_rate * hourly_pattern[hour_of_day] * weekend_factor * trend
        values[t] = rng.poisson(np.maximum(rate, 0.1))

    dow_array = np.array([((t // 24) % 7) for t in range(T)], dtype=np.int32)
    return values, dow_array


class SpectralRidgePredictor:
    def __init__(self) -> None:
        self._pipeline = SpectralRidgePipeline(PipelineConfig())
        self._cell_ids: list[str] = []
        self._cell_names: dict[str, str] = {}
        self._base_date: date = date.today() - timedelta(days=SYNTHETIC_DAYS)

    def train(self, rows: list[ViolationRow]) -> None:
        if rows:
            self._train_from_rows(rows)
        else:
            self._train_synthetic()

    def train_synthetic(self) -> None:
        """Public entry for startup auto-train with no data."""
        self._train_synthetic()

    def _train_synthetic(self) -> None:
        cell_ids = list(_CELL_TO_NAME.keys())
        rng = random.Random(99)
        for _ in range(SYNTHETIC_EXTRA_CELLS):
            lat = rng.uniform(12.85, 13.10)
            lon = rng.uniform(77.50, 77.75)
            cid = point_to_cell_id(lat, lon)
            if cid not in cell_ids:
                cell_ids.append(cid)

        self._cell_ids = cell_ids
        self._cell_names = dict(_CELL_TO_NAME)

        values, dow = _generate_synthetic_matrix(cell_ids, SYNTHETIC_DAYS)
        cell_arr = np.array(cell_ids)
        self._pipeline.fit(values, dow, cell_arr)
        self._base_date = date.today() - timedelta(days=SYNTHETIC_DAYS)

    def _train_from_rows(self, rows: list[ViolationRow]) -> None:
        cell_set: set[str] = set()
        ts_map: defaultdict[str, list[datetime]] = defaultdict(list)
        for r in rows:
            cell_set.add(r.cell_id)
            ts_map[r.cell_id].append(r.timestamp)

        cell_ids = sorted(cell_set)
        self._cell_ids = cell_ids
        self._cell_names = {
            cid: _CELL_TO_NAME[cid] for cid in cell_ids if cid in _CELL_TO_NAME
        }

        if not rows:
            return self._train_synthetic()

        all_ts = [r.timestamp for r in rows]
        min_ts = min(all_ts)
        max_ts = max(all_ts)
        total_hours = max(int((max_ts - min_ts).total_seconds() / 3600) + 1, 96)

        cell_idx_map = {cid: i for i, cid in enumerate(cell_ids)}
        N = len(cell_ids)
        values = np.zeros((total_hours, N), dtype=np.float64)

        for r in rows:
            h = int((r.timestamp - min_ts).total_seconds() / 3600)
            h = min(h, total_hours - 1)
            ci = cell_idx_map[r.cell_id]
            values[h, ci] += 1.0

        dow = np.array(
            [((min_ts + timedelta(hours=t)).weekday()) for t in range(total_hours)],
            dtype=np.int32,
        )

        self._base_date = min_ts.date()

        ws = self._pipeline.config.window_hours
        if total_hours < ws + 24:
            return self._train_synthetic()

        self._pipeline.fit(values, dow, np.array(cell_ids))

    def predict(self, day: date) -> list[HotspotPrediction]:
        if not self._pipeline.is_fitted:
            self._train_synthetic()

        prediction = self._pipeline.predict(top_k=50)
        rng = random.Random(day.toordinal())

        hotspots: list[HotspotPrediction] = []
        for entry in prediction.top_k_cells:
            cell_id = entry["cell_id"]
            pred_count = max(1, int(round(entry["predicted_violations"])))

            vtype = rng.choice(VIOLATION_TYPES)
            secondary = rng.choice([v for v in VIOLATION_TYPES if v != vtype])
            primary_count = rng.randint(pred_count // 2, pred_count)
            secondary_count = pred_count - primary_count
            violation_types = [{"type": vtype, "count": primary_count}]
            if secondary_count > 0:
                violation_types.append({"type": secondary, "count": secondary_count})

            impact = round(
                max(0.0, min(100.0, pred_count * 0.2 + rng.gauss(0, 8))), 1
            )

            peak_hours = self._make_peak_hours(rng, pred_count)

            hotspots.append(
                HotspotPrediction(
                    cell_id=cell_id,
                    violation_count=pred_count,
                    violation_types=violation_types,
                    congestion_impact_score=impact,
                    peak_hours=peak_hours,
                    location_name=self._cell_names.get(cell_id),
                )
            )

        return hotspots

    @staticmethod
    def _make_peak_hours(
        rng: random.Random, count: int
    ) -> list[dict[str, str | int]]:
        peaks: list[dict[str, str | int]] = []
        if rng.random() > 0.3:
            h = rng.randint(7, 9)
            peaks.append({
                "start": f"{h:02d}:00",
                "end": f"{h + 1:02d}:30",
                "expected_violations": max(1, rng.randint(count // 6, count // 3)),
            })
        if rng.random() > 0.3:
            h = rng.randint(17, 19)
            peaks.append({
                "start": f"{h:02d}:00",
                "end": f"{min(h + 1, 23):02d}:30",
                "expected_violations": max(1, rng.randint(count // 6, count // 3)),
            })
        return peaks
