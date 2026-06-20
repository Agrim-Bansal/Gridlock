import { Spinner } from '../shared/Spinner';

interface CsvPreviewProps {
  filename: string;
  fileSize: string;
  headers: string[];
  rows: string[][];
  onCancel: () => void;
  onUpload: () => void;
  uploading: boolean;
}

export const CsvPreview = ({ filename, fileSize, headers, rows, onCancel, onUpload, uploading }: CsvPreviewProps) => (
  <div className="overflow-hidden rounded-xl border border-stone-200/80 bg-white shadow-sm dark:border-stone-700/60 dark:bg-stone-900">
    <div className="flex items-center justify-between border-b border-stone-100 px-5 py-3.5 dark:border-stone-800">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100 dark:bg-stone-800">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-stone-500 dark:text-stone-400">
            <path d="M9 1.5H4a1.5 1.5 0 00-1.5 1.5v10A1.5 1.5 0 004 14.5h8a1.5 1.5 0 001.5-1.5V6L9 1.5z" />
            <path d="M9 1.5V6h4.5" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-medium text-stone-800 dark:text-stone-200">{filename}</p>
          <p className="text-[11px] text-stone-400 dark:text-stone-500">{fileSize}</p>
        </div>
      </div>
      <button
        onClick={onCancel}
        className="flex h-7 w-7 items-center justify-center rounded-lg text-stone-400 transition-all duration-200 hover:bg-stone-100 hover:text-stone-600 active:scale-95 dark:hover:bg-stone-800 dark:hover:text-stone-300"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <path d="M2.5 2.5l7 7M9.5 2.5l-7 7" />
        </svg>
      </button>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full font-mono text-xs">
        <thead>
          <tr className="bg-stone-50 dark:bg-stone-800/50">
            {headers.map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-stone-500 dark:text-stone-400">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-stone-100 dark:border-stone-800">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-1.5 text-stone-600 dark:text-stone-400">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    <div className="flex justify-end gap-2 border-t border-stone-100 px-5 py-3.5 dark:border-stone-800">
      <button
        onClick={onCancel}
        className="rounded-lg border border-stone-200 px-4 py-1.5 text-sm text-stone-600 transition-all duration-200 hover:bg-stone-50 active:scale-[0.98] dark:border-stone-700 dark:text-stone-400 dark:hover:bg-stone-800"
      >
        Cancel
      </button>
      <button
        onClick={onUpload}
        disabled={uploading}
        className="inline-flex items-center gap-2 rounded-lg bg-stone-900 px-4 py-1.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:bg-stone-800 hover:shadow-md active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-200"
      >
        {uploading && <Spinner size="sm" />}
        {uploading ? 'Uploading...' : 'Upload & train'}
      </button>
    </div>
  </div>
);
