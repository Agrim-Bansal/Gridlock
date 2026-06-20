interface ErrorBannerProps {
  message: string;
  onDismiss: () => void;
  onRetry?: () => void;
}

export const ErrorBanner = ({ message, onDismiss, onRetry }: ErrorBannerProps) => (
  <div className="animate-slide-up flex items-center justify-between gap-3 rounded-lg border border-amber-200/80 bg-amber-50/80 px-4 py-2.5 backdrop-blur-sm dark:border-amber-800/30 dark:bg-amber-950/30">
    <div className="flex items-center gap-2.5">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 text-amber-500">
        <path d="M8 5v3.5M8 10.5h.005M14 8A6 6 0 112 8a6 6 0 0112 0z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="text-sm text-amber-800 dark:text-amber-200">{message}</span>
    </div>
    <div className="flex items-center gap-1.5">
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-md bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 transition-all duration-200 hover:bg-amber-200 active:scale-95 dark:bg-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-900/60"
        >
          Retry
        </button>
      )}
      <button
        onClick={onDismiss}
        className="flex h-6 w-6 items-center justify-center rounded-md text-amber-400 transition-colors hover:bg-amber-100 hover:text-amber-600 dark:text-amber-600 dark:hover:bg-amber-900/40 dark:hover:text-amber-400"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <path d="M2.5 2.5l7 7M9.5 2.5l-7 7" />
        </svg>
      </button>
    </div>
  </div>
);
