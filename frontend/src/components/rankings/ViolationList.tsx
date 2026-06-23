import type { Hotspot } from '../../types';
import { RankingRow } from './RankingRow';

interface ViolationListProps {
  hotspots: Hotspot[];
  selectedCellId: string | null;
  onSelect: (cellId: string) => void;
}

/** Top-20 shortlist sorted by predicted violation count. */
export const ViolationList = ({ hotspots, selectedCellId, onSelect }: ViolationListProps) => {
  const sorted = [...hotspots].sort((a, b) => b.violationCount - a.violationCount);
  return (
    <div className="flex flex-col gap-1">
      {sorted.map((h, i) => (
        <div key={h.cellId} className="animate-fade-in" style={{ animationDelay: `${i * 30}ms` }}>
          <RankingRow
            hotspot={h}
            rank={i + 1}
            isSelected={h.cellId === selectedCellId}
            onSelect={onSelect}
          />
        </div>
      ))}
    </div>
  );
};
