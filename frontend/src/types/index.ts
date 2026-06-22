export interface ViolationType {
  type: string;
  count: number;
}

export interface PeakHour {
  start: string;
  end: string;
  expectedViolations: number;
}

export type Severity = 'low' | 'moderate' | 'high' | 'critical';

export interface Hotspot {
  cellId: string;
  locationName: string | null;
  violationCount: number;
  violationTypes: ViolationType[];
  severity: Severity;
  congestionImpactScore: number;
  peakHours: PeakHour[];
  patrolTime: string | null;
}

export interface HeatmapCell {
  cellId: string;
  violationCount: number;
}

export interface PredictionResult {
  date: string;
  generatedAt: string;
  rankedHotspots: Hotspot[];
  heatmapCells: HeatmapCell[];
}

export type DatasetStatus = 'processing' | 'active';

export interface Dataset {
  id: string;
  filename: string;
  uploadedAt: string;
  rowCount: number;
  status: DatasetStatus;
}

export type ModelStatus = 'idle' | 'training' | 'ready';

export interface ModelInfo {
  status: ModelStatus;
  lastTrainedAt: string | null;
  datasetCount: number;
  totalRows: number;
}
