const EXAMPLE_CSV = `timestamp,latitude,longitude,violation,severity
2024-01-15 08:30:00,12.9172,77.6230,No Parking,high
2024-01-15 09:00:00,12.9591,77.6974,Signal Jump,moderate`;

export const UploadFormatHint = () => (
  <div className="rounded-lg border border-stone-200 bg-stone-50 p-4 dark:border-stone-700 dark:bg-stone-800/50">
    <h4 className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">
      Expected CSV format
    </h4>
    <div className="mb-3 space-y-1.5 text-xs text-stone-600 dark:text-stone-400">
      <p>
        <span className="font-medium text-stone-800 dark:text-stone-200">Required columns:</span>{' '}
        <code className="rounded bg-stone-200/60 px-1 py-0.5 dark:bg-stone-700">timestamp</code>,{' '}
        <code className="rounded bg-stone-200/60 px-1 py-0.5 dark:bg-stone-700">latitude</code>,{' '}
        <code className="rounded bg-stone-200/60 px-1 py-0.5 dark:bg-stone-700">longitude</code>
      </p>
      <p>
        <span className="font-medium text-stone-800 dark:text-stone-200">Optional columns:</span>{' '}
        <code className="rounded bg-stone-200/60 px-1 py-0.5 dark:bg-stone-700">violation</code>,{' '}
        <code className="rounded bg-stone-200/60 px-1 py-0.5 dark:bg-stone-700">severity</code>
      </p>
      <p>
        Header aliases accepted (case-insensitive):{' '}
        <span className="text-stone-500 dark:text-stone-500">
          lat, lon/lng/long, time/datetime, violation_type, severity_src
        </span>
      </p>
    </div>
    <pre className="overflow-x-auto rounded-md bg-stone-900 p-3 text-xs leading-relaxed text-stone-300 dark:bg-stone-950">
      {EXAMPLE_CSV}
    </pre>
    <p className="mt-2 text-[11px] text-stone-400 dark:text-stone-500">
      Timestamps: YYYY-MM-DD HH:MM:SS, ISO 8601, or DD/MM/YYYY HH:MM:SS. Extra columns are ignored.
    </p>
  </div>
);
