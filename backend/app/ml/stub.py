from __future__ import annotations

import random
from datetime import date
from typing import TYPE_CHECKING

from app.grid import point_to_cell_id
from app.ml.predictor import HotspotPrediction

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


class StubPredictor:
    def __init__(self) -> None:
        self._trained_cells: list[str] = []
        self._train_count: int = 0

    def train(self, rows: list[ViolationRow]) -> None:
        self._trained_cells = list({r.cell_id for r in rows})
        self._train_count += 1

    def predict(self, day: date) -> list[HotspotPrediction]:
        seed = day.toordinal() * 1000 + self._train_count
        rng = random.Random(seed)

        cells = self._pick_cells(rng)

        hotspots: list[HotspotPrediction] = []
        for cell_id in cells:
            count = rng.randint(5, 500)
            impact = round(
                max(0.0, min(100.0, count * 0.2 + rng.gauss(0, 12))), 1
            )
            hotspots.append(
                HotspotPrediction(
                    cell_id=cell_id,
                    violation_count=count,
                    violation_types=[{"type": "No Parking", "count": count}],
                    congestion_impact_score=impact,
                    peak_hours=self._make_peak_hours(rng, count),
                    location_name=_CELL_TO_NAME.get(cell_id),
                )
            )

        return hotspots

    def _pick_cells(self, rng: random.Random) -> list[str]:
        if self._trained_cells:
            n = min(len(self._trained_cells), rng.randint(20, 50))
            cells = rng.sample(self._trained_cells, n)
            landmark_cells = list(_CELL_TO_NAME.keys())
            rng.shuffle(landmark_cells)
            for cid in landmark_cells[: rng.randint(5, 15)]:
                if cid not in cells:
                    cells.append(cid)
            return cells

        cells = list(_CELL_TO_NAME.keys())
        for _ in range(rng.randint(10, 30)):
            lat = rng.uniform(12.85, 13.10)
            lon = rng.uniform(77.45, 77.75)
            cells.append(point_to_cell_id(lat, lon))
        return cells

    @staticmethod
    def _make_peak_hours(
        rng: random.Random, count: int
    ) -> list[dict[str, str | int]]:
        peaks: list[dict[str, str | int]] = []
        if rng.random() > 0.3:
            h = rng.randint(7, 9)
            peaks.append(
                {
                    "start": f"{h:02d}:00",
                    "end": f"{h + 1:02d}:30",
                    "expected_violations": max(1, rng.randint(count // 6, count // 3)),
                }
            )
        if rng.random() > 0.3:
            h = rng.randint(17, 19)
            peaks.append(
                {
                    "start": f"{h:02d}:00",
                    "end": f"{min(h + 1, 23):02d}:30",
                    "expected_violations": max(1, rng.randint(count // 6, count // 3)),
                }
            )
        return peaks
