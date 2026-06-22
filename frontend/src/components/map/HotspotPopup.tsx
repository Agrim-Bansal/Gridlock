import type { Hotspot } from '../../types';
import { PeakHourChip } from '../rankings/PeakHourChip';

export const HotspotPopup = ({ hotspot }: { hotspot: Hotspot }) => (
  <div className="min-w-[220px] text-sm">
    <p className="font-semibold">{hotspot.locationName || `Cell ${hotspot.cellId}`}</p>
    <p className="text-xs text-slate-500">Cell: {hotspot.cellId}</p>
    <hr className="my-1.5 border-slate-200 dark:border-slate-600" />
    <div className="flex justify-between">
      <span>Violations</span>
      <span className="font-bold">{hotspot.violationCount}</span>
    </div>
    {hotspot.violationTypes.map((vt) => (
      <div key={vt.type} className="flex justify-between pl-3 text-xs text-slate-500">
        <span>{vt.type}</span>
        <span>{vt.count}</span>
      </div>
    ))}
    <hr className="my-1.5 border-slate-200 dark:border-slate-600" />
    <div className="flex justify-between">
      <span>Congestion Impact</span>
      <span className="font-bold">{hotspot.congestionImpactScore} / 100</span>
    </div>
    {hotspot.patrolTime && (
      <div className="mt-1 flex justify-between">
        <span>Deploy</span>
        <span className="font-mono font-bold">{hotspot.patrolTime}</span>
      </div>
    )}
    {hotspot.peakHours.length > 0 && (
      <>
        <hr className="my-1.5 border-slate-200 dark:border-slate-600" />
        <p className="mb-1 text-xs font-medium">Peak Hours</p>
        <div className="flex flex-wrap gap-1">
          {hotspot.peakHours.map((ph, i) => (
            <div key={i} className="text-center">
              <PeakHourChip {...ph} />
              <p className="text-[9px] text-slate-400">~{ph.expectedViolations}</p>
            </div>
          ))}
        </div>
      </>
    )}
  </div>
);
