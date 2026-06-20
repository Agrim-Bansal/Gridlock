import { useState } from 'react';
import type { Dataset } from '../../types';
import { Spinner } from '../shared/Spinner';

interface DatasetTableProps {
  datasets: Dataset[];
  onDelete: (id: string) => void;
}

const formatDate = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) +
    ' ' +
    d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true });
};

export const DatasetTable = ({ datasets, onDelete }: DatasetTableProps) => {
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const handleDelete = (id: string) => {
    if (confirmId === id) {
      onDelete(id);
      setConfirmId(null);
    } else {
      setConfirmId(id);
    }
  };

  if (datasets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-stone-200 py-14 dark:border-stone-700">
        <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-stone-100 dark:bg-stone-800">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-stone-400 dark:text-stone-500">
            <path d="M4 4h12M4 8h12M4 12h8M4 16h5" />
          </svg>
        </div>
        <p className="text-sm text-stone-400 dark:text-stone-500">
          No datasets uploaded yet
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-stone-200/80 bg-white shadow-sm dark:border-stone-700/60 dark:bg-stone-900">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-stone-100 dark:border-stone-800">
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-stone-400 dark:text-stone-500">File</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-stone-400 dark:text-stone-500">Uploaded</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-stone-400 dark:text-stone-500">Rows</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-stone-400 dark:text-stone-500">Status</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((ds, i) => (
            <tr
              key={ds.id}
              className="animate-fade-in border-t border-stone-100 transition-colors hover:bg-stone-50/50 dark:border-stone-800 dark:hover:bg-stone-800/30"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <td className="px-4 py-3 font-medium text-stone-800 dark:text-stone-200">
                {ds.filename}
              </td>
              <td className="px-4 py-3 text-stone-500 dark:text-stone-400">
                {formatDate(ds.uploadedAt)}
              </td>
              <td className="px-4 py-3 font-mono tabular-nums text-stone-500 dark:text-stone-400">
                {ds.rowCount.toLocaleString()}
              </td>
              <td className="px-4 py-3">
                {ds.status === 'processing' ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
                    <Spinner size="sm" /> Processing
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Active
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                {ds.status === 'active' && (
                  <button
                    onClick={() => handleDelete(ds.id)}
                    className={`rounded-md px-2.5 py-1 text-xs transition-all duration-200 ${
                      confirmId === ds.id
                        ? 'animate-fade-in bg-red-50 font-medium text-red-600 ring-1 ring-red-200/60 dark:bg-red-950/30 dark:text-red-400 dark:ring-red-800/30'
                        : 'text-stone-400 hover:bg-stone-100 hover:text-red-500 dark:text-stone-600 dark:hover:bg-stone-800 dark:hover:text-red-400'
                    }`}
                  >
                    {confirmId === ds.id ? 'Confirm delete?' : 'Delete'}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
