import { Link } from 'react-router-dom';

interface EmptyStateProps {
  title: string;
  message: string;
  linkTo?: string;
  linkLabel?: string;
}

export const EmptyState = ({ title, message, linkTo, linkLabel }: EmptyStateProps) => (
  <div className="animate-fade-in flex w-full flex-col items-center justify-center gap-3 py-12 text-center">
    <div className="mb-1 flex h-12 w-12 items-center justify-center rounded-xl bg-stone-100 dark:bg-stone-800">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-stone-400 dark:text-stone-500">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    </div>
    <p className="font-serif text-lg text-stone-700 dark:text-stone-300">{title}</p>
    <p className="max-w-xs text-sm leading-relaxed text-stone-400 dark:text-stone-500">{message}</p>
    {linkTo && linkLabel && (
      <Link
        to={linkTo}
        className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:bg-stone-800 hover:shadow-md active:scale-[0.98] dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-200"
      >
        {linkLabel}
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5.25 3.5L8.75 7L5.25 10.5" />
        </svg>
      </Link>
    )}
  </div>
);
