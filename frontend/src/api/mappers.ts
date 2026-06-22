import type {
  RawHotspot,
  RawHeatmapCell,
  RawPredictionResponse,
  RawDataset,
  RawModelStatusResponse,
  RawUploadResponse,
} from './types';
import type { Hotspot, HeatmapCell, PredictionResult, Dataset, ModelInfo } from '../types';

export const mapHotspot = (raw: RawHotspot): Hotspot => ({
  cellId: raw.cell_id,
  locationName: raw.location_name ?? null,
  violationCount: raw.violation_count,
  violationTypes: raw.violation_types,
  severity: raw.severity,
  congestionImpactScore: raw.congestion_impact_score,
  peakHours: raw.peak_hours.map((ph) => ({
    start: ph.start,
    end: ph.end,
    expectedViolations: ph.expected_violations,
  })),
  patrolTime: raw.patrol_time ?? null,
});

export const mapHeatmapCell = (raw: RawHeatmapCell): HeatmapCell => ({
  cellId: raw.cell_id,
  violationCount: raw.violation_count,
});

export const mapPredictions = (raw: RawPredictionResponse): PredictionResult => {
  const rankedRaw = raw.ranked_hotspots ?? raw.hotspots ?? [];
  const heatmapRaw = raw.heatmap_cells ?? [];

  return {
    date: raw.date,
    generatedAt: raw.generated_at,
    rankedHotspots: rankedRaw.map(mapHotspot),
    heatmapCells: heatmapRaw.map(mapHeatmapCell),
  };
};

export const mapDataset = (raw: RawDataset | RawUploadResponse): Dataset => ({
  id: raw.id,
  filename: raw.filename,
  uploadedAt: raw.uploaded_at,
  rowCount: raw.row_count,
  status: raw.status,
});

export const mapModelInfo = (raw: RawModelStatusResponse): ModelInfo => ({
  status: raw.status,
  lastTrainedAt: raw.last_trained_at,
  datasetCount: raw.dataset_count,
  totalRows: raw.total_rows,
});
