import type { Hotspot, Severity } from '../../types';
import { cisToColor } from '../../lib/colors';
import { PeakHourChip } from './PeakHourChip';

interface RankingRowProps {
  hotspot: Hotspot;
  rank: number;
  isSelected: boolean;
  onSelect: (cellId: string) => void;
}

const tintClass: Record<Severity, string> = {
  critical: 'bg-red-50/50 dark:bg-red-950/15',
  high: 'bg-orange-50/40 dark:bg-orange-950/10',
  moderate: 'bg-amber-50/25 dark:bg-amber-950/8',
  low: 'bg-transparent',
};

export const RankingRow = ({ hotspot, rank, isSelected, onSelect }: RankingRowProps) => {
  const color = cisToColor(hotspot.congestionImpactScore);

  return (
    <button
      onClick={() => onSelect(hotspot.cellId)}
      className={`group relative w-full rounded-lg px-3 py-2.5 text-left transition-all duration-200 ${
        isSelected
          ? 'bg-white shadow-md ring-1 ring-stone-200/80 dark:bg-stone-800 dark:ring-stone-600/50'
          : `${tintClass[hotspot.severity]} hover:bg-stone-50 hover:shadow-sm active:scale-[0.99] dark:hover:bg-stone-800/40`
      }`}
    >
      {isSelected && (
        <span
          className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full"
          style={{ backgroundColor: color }}
        />
      )}
      <div className="flex items-baseline justify-between gap-2">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className={`w-4 text-right text-[11px] tabular-nums ${
            isSelected ? 'text-stone-500 dark:text-stone-400' : 'text-stone-400 dark:text-stone-600'
          }`}>
            {rank}
          </span>
          <span className={`truncate text-[13px] ${
            isSelected
              ? 'font-semibold text-stone-900 dark:text-white'
              : 'font-medium text-stone-700 dark:text-stone-300'
          }`}>
            {hotspot.locationName || `Cell ${hotspot.cellId}`}
          </span>
        </div>
        <span
          className="shrink-0 rounded-md px-1.5 py-0.5 font-mono text-sm font-semibold tabular-nums"
          style={{
            color,
            backgroundColor: isSelected ? `${color}20` : `${color}10`,
          }}
        >
          {hotspot.congestionImpactScore}
        </span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2 pl-6">
        <span className={`text-[11px] ${
          isSelected ? 'text-stone-500 dark:text-stone-400' : 'text-stone-400 dark:text-stone-500'
        }`}>
          {hotspot.violationCount} violations
        </span>
        {hotspot.patrolTime && (
          <span className="rounded-md bg-stone-800/90 px-1.5 py-0.5 font-mono text-[10px] font-medium text-stone-100 dark:bg-stone-200 dark:text-stone-900">
            Deploy: {hotspot.patrolTime}
          </span>
        )}
        {hotspot.peakHours.length > 0 && (
          <div className="flex gap-1">
            {hotspot.peakHours.map((ph, i) => (
              <PeakHourChip key={i} {...ph} />
            ))}
          </div>
        )}
      </div>
    </button>
  );
};
