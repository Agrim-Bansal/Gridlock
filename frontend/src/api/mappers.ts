import type {
  RawHotspot,
  RawPredictionResponse,
  RawDataset,
  RawModelStatusResponse,
  RawUploadResponse,
} from './types';
import type { Hotspot, PredictionResult, Dataset, ModelInfo } from '../types';

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
});

export const mapPredictions = (raw: RawPredictionResponse): PredictionResult => ({
  date: raw.date,
  generatedAt: raw.generated_at,
  hotspots: raw.hotspots.map(mapHotspot),
});

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
