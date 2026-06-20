from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.models import ViolationRow


@dataclass
class HotspotPrediction:
    cell_id: str
    violation_count: int
    violation_types: list[dict]
    congestion_impact_score: float
    peak_hours: list[dict]
    location_name: str | None = None
    severity: str = field(default="", repr=False)


class Predictor(Protocol):
    def train(self, rows: list[ViolationRow]) -> None: ...
    def predict(self, day: date) -> list[HotspotPrediction]: ...
