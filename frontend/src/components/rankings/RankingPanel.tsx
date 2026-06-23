import { useState } from 'react';
import type { Hotspot } from '../../types';
import { ViolationList } from './ViolationList';
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

type Tab = 'violations' | 'impact';

export const RankingPanel = ({
  rankedHotspots,
  selectedCellId,
  onSelectCell,
  modelStatus,
  loading,
}: RankingPanelProps) => {
  const [tab, setTab] = useState<Tab>('impact');

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
        <div className="flex border-b border-stone-200/60 dark:border-stone-800/60">
          <div className="flex-1 py-2.5 text-center text-xs font-medium text-stone-400 dark:text-stone-500">
            By violations
          </div>
          <div className="flex-1 py-2.5 text-center text-xs font-medium text-stone-400 dark:text-stone-500">
            By congestion
          </div>
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
      <div className="relative flex border-b border-stone-200/60 dark:border-stone-800/60">
        <button
          type="button"
          className={`flex-1 py-2.5 text-center text-xs font-medium transition-colors duration-200 ${
            tab === 'violations'
              ? 'text-stone-900 dark:text-stone-100'
              : 'text-stone-400 hover:text-stone-600 dark:text-stone-500 dark:hover:text-stone-300'
          }`}
          onClick={() => setTab('violations')}
        >
          By violations
        </button>
        <button
          type="button"
          className={`flex-1 py-2.5 text-center text-xs font-medium transition-colors duration-200 ${
            tab === 'impact'
              ? 'text-stone-900 dark:text-stone-100'
              : 'text-stone-400 hover:text-stone-600 dark:text-stone-500 dark:hover:text-stone-300'
          }`}
          onClick={() => setTab('impact')}
        >
          By congestion
        </button>
        <div
          className="absolute bottom-0 h-0.5 bg-stone-900 transition-all duration-300 ease-out dark:bg-stone-100"
          style={{ left: tab === 'violations' ? '0%' : '50%', width: '50%' }}
        />
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {tab === 'violations' ? (
          <ViolationList
            hotspots={rankedHotspots}
            selectedCellId={selectedCellId}
            onSelect={onSelectCell}
          />
        ) : (
          <CongestionList
            hotspots={rankedHotspots}
            selectedCellId={selectedCellId}
            onSelect={onSelectCell}
          />
        )}
      </div>
    </div>
  );
};
