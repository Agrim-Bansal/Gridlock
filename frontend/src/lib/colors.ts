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
