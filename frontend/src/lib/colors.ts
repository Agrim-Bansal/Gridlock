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

const HEATMAP_LOW = '#94a3b8';
const HEATMAP_HIGH = '#dc2626';

/** Violation-intensity fill for heatmap cells; opacity scales with normalized count. */
export const heatmapFill = (violationCount: number, maxCount: number): { color: string; opacity: number } => {
  const t = maxCount > 0 ? violationCount / maxCount : 0;
  // Blend slate → red by intensity; keep readable on both map styles
  const opacity = 0.12 + t * 0.45;
  const color = t >= 0.66 ? HEATMAP_HIGH : t >= 0.33 ? '#f97316' : HEATMAP_LOW;
  return { color, opacity };
};
