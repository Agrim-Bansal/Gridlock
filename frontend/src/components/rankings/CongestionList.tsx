import type { Hotspot } from '../../types';
import { RankingRow } from './RankingRow';

interface CongestionListProps {
  hotspots: Hotspot[];
  selectedCellId: string | null;
  onSelect: (cellId: string) => void;
}

/** Top-20 shortlist sorted by Congestion Impact Score. */
export const CongestionList = ({ hotspots, selectedCellId, onSelect }: CongestionListProps) => {
  const sorted = [...hotspots].sort((a, b) => b.congestionImpactScore - a.congestionImpactScore);
  return (
    <div className="flex flex-col gap-1">
      {sorted.map((h, i) => (
        <div key={h.cellId} className="animate-fade-in" style={{ animationDelay: `${i * 30}ms` }}>
          <RankingRow
            hotspot={h}
            rank={i + 1}
            isSelected={h.cellId === selectedCellId}
            mode="impact"
            onSelect={onSelect}
          />
        </div>
      ))}
    </div>
  );
};
