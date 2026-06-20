import { Link } from 'react-router-dom';
import type { ModelStatus } from '../../types';

interface StatusBarProps {
  status: ModelStatus;
  lastTrainedAt: string | null;
  datasetCount: number;
}

const statusConfig: Record<ModelStatus, { label: string; dotClass: string; pillBg: string }> = {
  idle: {
    label: 'Idle',
    dotClass: 'bg-stone-400 dark:bg-stone-500',
    pillBg: 'bg-stone-100 text-stone-500 dark:bg-stone-800 dark:text-stone-400',
  },
  training: {
    label: 'Training',
    dotClass: 'bg-amber-400 animate-pulse-ring',
    pillBg: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
  },
  ready: {
    label: 'Ready',
    dotClass: 'bg-emerald-500',
    pillBg: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
  },
};

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const formatDate = (iso: string) => {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const day = d.getDate();
  const month = MONTHS[d.getMonth()];
  const hours = d.getHours();
  const mins = String(d.getMinutes()).padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const h12 = hours % 12 || 12;
  return `${day} ${month}, ${h12}:${mins} ${ampm}`;
};

const relativeTime = (iso: string) => {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 0) return 'just now';
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
};

export const StatusBar = ({ status, lastTrainedAt, datasetCount }: StatusBarProps) => {
  const cfg = statusConfig[status];
  return (
    <footer className="flex h-10 items-center gap-4 border-t border-stone-200/60 bg-white/80 px-5 backdrop-blur-sm dark:border-stone-800/60 dark:bg-stone-900/80">
      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.pillBg}`}>
        <span className={`inline-block h-1.5 w-1.5 rounded-full ${cfg.dotClass}`} />
        {cfg.label}
      </span>
      {lastTrainedAt && (
        <>
          <span className="text-stone-300 dark:text-stone-700">&middot;</span>
          <span
            className="font-mono text-[11px] tabular-nums text-stone-400 dark:text-stone-500"
            title={relativeTime(lastTrainedAt)}
          >
            {formatDate(lastTrainedAt)}
          </span>
        </>
      )}
      <span className="text-stone-300 dark:text-stone-700">&middot;</span>
      <Link
        to="/data"
        className="text-xs text-stone-400 transition-colors hover:text-stone-600 dark:text-stone-500 dark:hover:text-stone-300"
      >
        {datasetCount} dataset{datasetCount !== 1 ? 's' : ''}
      </Link>
    </footer>
  );
};
