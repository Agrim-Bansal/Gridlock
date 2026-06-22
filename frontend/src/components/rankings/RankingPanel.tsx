import type { Hotspot } from '../../types';
import { CongestionList } from './CongestionList';
import { EmptyState } from '../shared/EmptyState';
import { RankingSkeleton } from '../shared/Spinner';

interface RankingPanelProps {
  rankedHotspots: Hotspot[];
  selectedCellId: string | null;
  onSelectCell: (cellId: string) => void;
  modelStatus: 'idle' | 'training' | 'ready';
  loading?: boolean;
}

export const RankingPanel = ({
  rankedHotspots,
  selectedCellId,
  onSelectCell,
  modelStatus,
  loading,
}: RankingPanelProps) => {
  if (modelStatus === 'idle') {
    return (
      <div className="flex h-full items-center p-5">
        <EmptyState
          title="No predictions yet"
          message="Upload training data to generate violation forecasts."
          linkTo="/data"
          linkLabel="Upload data"
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b border-stone-200/60 px-3 py-2.5 dark:border-stone-800/60">
          <p className="text-center text-xs font-medium text-stone-500 dark:text-stone-400">
            Top patrol targets (by impact)
          </p>
        </div>
        <RankingSkeleton />
      </div>
    );
  }

  if (rankedHotspots.length === 0) {
    return (
      <div className="flex h-full items-center p-5">
        <EmptyState
          title="No hotspots for this date"
          message="Try selecting a different date."
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-stone-200/60 px-3 py-2.5 dark:border-stone-800/60">
        <p className="text-center text-xs font-medium text-stone-500 dark:text-stone-400">
          Top patrol targets (by impact)
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        <CongestionList
          hotspots={rankedHotspots}
          selectedCellId={selectedCellId}
          onSelect={onSelectCell}
        />
      </div>
    </div>
  );
};
