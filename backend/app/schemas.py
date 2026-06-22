from pydantic import BaseModel


class ViolationTypeOut(BaseModel):
    type: str
    count: int


class PeakHourOut(BaseModel):
    start: str
    end: str
    expected_violations: int


class HotspotOut(BaseModel):
    cell_id: str
    location_name: str | None = None
    violation_count: int
    violation_types: list[ViolationTypeOut]
    severity: str
    congestion_impact_score: float
    patrol_time: str
    rank: int
    peak_hours: list[PeakHourOut] = []


class HeatmapCellOut(BaseModel):
    cell_id: str
    violation_count: int


class PredictionResponse(BaseModel):
    date: str
    generated_at: str
    ranked_hotspots: list[HotspotOut]
    heatmap_cells: list[HeatmapCellOut]
    hotspots: list[HotspotOut] = []


class ModelStatusResponse(BaseModel):
    status: str
    last_trained_at: str | None = None
    dataset_count: int
    total_rows: int


class DatasetOut(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    row_count: int
    status: str


class DatasetListResponse(BaseModel):
    datasets: list[DatasetOut]


class DeleteResponse(BaseModel):
    message: str
    retrain_status: str


class ErrorResponse(BaseModel):
    error: str
    message: str
