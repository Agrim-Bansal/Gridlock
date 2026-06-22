import type { Severity } from '../types';

export const severityColor: Record<Severity, string> = {
  low: '#22c55e',
  moderate: '#eab308',
  high: '#f97316',
  critical: '#ef4444',
};

export const severityLabel: Record<Severity, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  critical: 'Critical',
};

/** Map CIS (0–100) to the same palette used for severity bands. */
export const cisToColor = (score: number): string => {
  if (score >= 90) return severityColor.critical;
  if (score >= 70) return severityColor.high;
  if (score >= 40) return severityColor.moderate;
  return severityColor.low;
};

const HEATMAP_MUTED = '#64748b';

/** Muted fill for suppressed heatmap cells; opacity scales with normalized count. */
export const heatmapFill = (violationCount: number, maxCount: number): { color: string; opacity: number } => {
  const t = maxCount > 0 ? violationCount / maxCount : 0;
  return { color: HEATMAP_MUTED, opacity: 0.06 + t * 0.28 };
};
