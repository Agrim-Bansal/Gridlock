import { Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[Gridlock] Unhandled error:', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="flex h-screen w-full items-center justify-center bg-stone-50 px-6 dark:bg-stone-950">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-red-100 dark:bg-red-900/30">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-red-500">
              <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
          </div>
          <h1 className="mb-2 font-serif text-xl text-stone-800 dark:text-stone-200">
            Something went wrong
          </h1>
          <p className="mb-1 text-sm text-stone-500 dark:text-stone-400">
            An unexpected error occurred. Try reloading the page.
          </p>
          <pre className="mb-4 max-h-24 overflow-auto rounded-lg bg-stone-100 px-3 py-2 text-left text-xs text-red-700 dark:bg-stone-900 dark:text-red-400">
            {this.state.error.message}
          </pre>
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 rounded-lg bg-stone-800 px-5 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-stone-700 active:scale-[0.98] dark:bg-stone-200 dark:text-stone-900 dark:hover:bg-stone-100"
          >
            Reload page
          </button>
        </div>
      </div>
    );
  }
}
