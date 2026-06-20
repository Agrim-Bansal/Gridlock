export const Spinner = ({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) => {
  const dims = { sm: 'h-4 w-4', md: 'h-5 w-5', lg: 'h-8 w-8' };
  const borders = { sm: 'border-[1.5px]', md: 'border-2', lg: 'border-[2.5px]' };
  return (
    <div
      className={`${dims[size]} ${borders[size]} animate-spin rounded-full border-stone-200 border-t-stone-600 dark:border-stone-700 dark:border-t-stone-300`}
      role="status"
      aria-label="Loading"
    />
  );
};

export const Skeleton = ({ className = '' }: { className?: string }) => (
  <div className={`skeleton rounded-md bg-stone-100 dark:bg-stone-800 ${className}`} />
);

export const RankingSkeleton = () => (
  <div className="flex flex-col gap-1.5 p-2">
    {Array.from({ length: 8 }).map((_, i) => (
      <div
        key={i}
        className="animate-fade-in rounded-lg px-3 py-3"
        style={{ animationDelay: `${i * 50}ms` }}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-3 w-3" />
            <Skeleton className="h-3.5 w-24" />
          </div>
          <Skeleton className="h-4 w-10" />
        </div>
        <div className="mt-2 flex items-center gap-2 pl-5">
          <Skeleton className="h-3 w-14" />
          <Skeleton className="h-4 w-16 rounded-full" />
        </div>
      </div>
    ))}
  </div>
);
