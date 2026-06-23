import type { Hotspot } from '../../types';
import { RankingRow } from './RankingRow';

interface CongestionListProps {
  hotspots: Hotspot[];
  selectedCellId: string | null;
  onSelect: (cellId: string) => void;
}

/** Top-20 shortlist in CIS priority order (backend-ranked patrol targets). */
export const CongestionList = ({ hotspots, selectedCellId, onSelect }: CongestionListProps) => {
  return (
    <div className="flex flex-col gap-1">
      {hotspots.map((h, i) => (
        <div key={h.cellId} className="animate-fade-in" style={{ animationDelay: `${i * 30}ms` }}>
          <RankingRow
            hotspot={h}
            rank={h.rank ?? i + 1}
            isSelected={h.cellId === selectedCellId}
            onSelect={onSelect}
          />
        </div>
      ))}
    </div>
  );
};
