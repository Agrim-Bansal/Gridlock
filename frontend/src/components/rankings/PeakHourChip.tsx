import type { PeakHour } from '../../types';

const formatTime = (t: string) => {
  const [h, m] = t.split(':').map(Number);
  const suffix = h >= 12 ? 'p' : 'a';
  const hour = h > 12 ? h - 12 : h === 0 ? 12 : h;
  return m > 0 ? `${hour}:${String(m).padStart(2, '0')}${suffix}` : `${hour}${suffix}`;
};

export const PeakHourChip = ({ start, end }: PeakHour) => (
  <span className="rounded-full bg-stone-100/80 px-2 py-0.5 font-mono text-[10px] tabular-nums text-stone-500 dark:bg-stone-800/80 dark:text-stone-400">
    {formatTime(start)}–{formatTime(end)}
  </span>
);
