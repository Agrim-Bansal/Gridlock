import { NavLink } from 'react-router-dom';

interface TopBarProps {
  isDark: boolean;
  onToggleTheme: () => void;
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm transition-all duration-200 ${
    isActive
      ? 'bg-stone-100 text-stone-900 font-medium dark:bg-stone-800 dark:text-stone-100'
      : 'text-stone-500 hover:text-stone-800 hover:bg-stone-50 dark:text-stone-400 dark:hover:text-stone-200 dark:hover:bg-stone-800/50'
  }`;

export const TopBar = ({ isDark, onToggleTheme }: TopBarProps) => (
  <header className="flex h-14 items-center justify-between border-b border-stone-200/60 bg-white/80 px-5 backdrop-blur-sm dark:border-stone-800/60 dark:bg-stone-900/80">
    <div className="flex items-center gap-6">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-stone-900 dark:bg-stone-100">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-white dark:text-stone-900">
            <rect x="1" y="1" width="5" height="5" rx="1" fill="currentColor" opacity="0.9" />
            <rect x="8" y="1" width="5" height="5" rx="1" fill="currentColor" opacity="0.5" />
            <rect x="1" y="8" width="5" height="5" rx="1" fill="currentColor" opacity="0.3" />
            <rect x="8" y="8" width="5" height="5" rx="1" fill="currentColor" opacity="0.7" />
          </svg>
        </div>
        <h1 className="font-serif text-xl tracking-tight text-stone-900 dark:text-stone-100">
          Gridlock
        </h1>
      </div>
      <nav className="flex gap-1">
        <NavLink to="/" className={navLinkClass} end>
          Dashboard
        </NavLink>
        <NavLink to="/data" className={navLinkClass}>
          Data
        </NavLink>
      </nav>
    </div>
    <button
      onClick={onToggleTheme}
      className="group relative flex h-8 w-8 items-center justify-center rounded-lg text-stone-400 transition-all duration-200 hover:bg-stone-100 hover:text-stone-600 active:scale-95 dark:text-stone-500 dark:hover:bg-stone-800 dark:hover:text-stone-300"
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="8" cy="8" r="3.5" />
          <path d="M8 1.5v1M8 13.5v1M2.75 2.75l.7.7M12.55 12.55l.7.7M1.5 8h1M13.5 8h1M2.75 13.25l.7-.7M12.55 3.45l.7-.7" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M13.5 9.2A5.5 5.5 0 016.8 2.5 6 6 0 1013.5 9.2z" />
        </svg>
      )}
    </button>
  </header>
);
