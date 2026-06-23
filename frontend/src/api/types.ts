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
  patrol_time?: string | null;
  rank?: number;
}

export interface RawHeatmapCell {
  cell_id: string;
  violation_count: number;
}

export interface RawPredictionResponse {
  date: string;
  generated_at: string;
  /** Legacy: all hotspots in one array. Prefer ranked_hotspots + heatmap_cells. */
  hotspots?: RawHotspot[];
  ranked_hotspots?: RawHotspot[];
  heatmap_cells?: RawHeatmapCell[];
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

export interface RawCellLocation {
  road: string;
  locality: string;
  display_name: string;
}

export interface RawCellNamesResponse {
  cell_names: Record<string, RawCellLocation>;
}
