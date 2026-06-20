export interface RawViolationType {
  type: string;
  count: number;
}

export interface RawPeakHour {
  start: string;
  end: string;
  expected_violations: number;
}

export interface RawHotspot {
  cell_id: string;
  location_name?: string;
  violation_count: number;
  violation_types: RawViolationType[];
  severity: 'low' | 'moderate' | 'high' | 'critical';
  congestion_impact_score: number;
  peak_hours: RawPeakHour[];
}

export interface RawPredictionResponse {
  date: string;
  generated_at: string;
  hotspots: RawHotspot[];
}

export interface RawDataset {
  id: string;
  filename: string;
  uploaded_at: string;
  row_count: number;
  status: 'processing' | 'active';
}

export interface RawDatasetListResponse {
  datasets: RawDataset[];
}

export interface RawUploadResponse {
  id: string;
  filename: string;
  uploaded_at: string;
  row_count: number;
  status: 'processing' | 'active';
}

export interface RawDeleteResponse {
  message: string;
  retrain_status: string;
}

export interface RawModelStatusResponse {
  status: 'idle' | 'training' | 'ready';
  last_trained_at: string | null;
  dataset_count: number;
  total_rows: number;
}
