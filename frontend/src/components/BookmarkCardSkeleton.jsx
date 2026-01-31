import { Skeleton } from './ui/skeleton';

const BookmarkCardSkeleton = ({ viewMode = 'list' }) => {
  if (viewMode === 'list') {
    return (
      <div className="flex items-center gap-4 p-4 border-2 border-foreground/20 bg-card">
        {/* Thumbnail */}
        <Skeleton className="flex-shrink-0 w-12 h-12 rounded-none bg-muted" />

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Title */}
          <Skeleton className="h-5 w-3/4 rounded-none bg-muted" />

          {/* Summary */}
          <Skeleton className="h-4 w-full rounded-none bg-muted" />

          {/* Metadata row */}
          <div className="flex items-center gap-3">
            <Skeleton className="h-3 w-20 rounded-none bg-muted" />
            <Skeleton className="h-3 w-16 rounded-none bg-muted" />
            <Skeleton className="h-3 w-24 rounded-none bg-muted" />
          </div>

          {/* Tags */}
          <div className="flex gap-1">
            <Skeleton className="h-5 w-16 rounded-none bg-muted" />
            <Skeleton className="h-5 w-20 rounded-none bg-muted" />
            <Skeleton className="h-5 w-14 rounded-none bg-muted" />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex-shrink-0 flex items-center gap-1">
          <Skeleton className="h-8 w-8 rounded-none bg-muted" />
          <Skeleton className="h-8 w-8 rounded-none bg-muted" />
        </div>
      </div>
    );
  }

  // Grid view skeleton
  return (
    <div className="overflow-hidden border-2 border-foreground/20 bg-card">
      {/* Thumbnail */}
      <Skeleton className="aspect-[16/9] w-full rounded-none bg-muted" />

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Title */}
        <Skeleton className="h-5 w-full rounded-none bg-muted" />
        <Skeleton className="h-5 w-2/3 rounded-none bg-muted" />

        {/* Summary */}
        <Skeleton className="h-4 w-full rounded-none bg-muted" />
        <Skeleton className="h-4 w-3/4 rounded-none bg-muted" />

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5">
          <Skeleton className="h-5 w-16 rounded-none bg-muted" />
          <Skeleton className="h-5 w-20 rounded-none bg-muted" />
          <Skeleton className="h-5 w-14 rounded-none bg-muted" />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t-2 border-foreground/10">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded-none bg-muted" />
            <Skeleton className="h-3 w-20 rounded-none bg-muted" />
          </div>
          <div className="flex items-center gap-1">
            <Skeleton className="h-7 w-7 rounded-none bg-muted" />
            <Skeleton className="h-7 w-7 rounded-none bg-muted" />
          </div>
        </div>

        {/* Timestamp row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-3 w-24 rounded-none bg-muted" />
            <Skeleton className="h-3 w-16 rounded-none bg-muted" />
          </div>
          <Skeleton className="h-5 w-16 rounded-none bg-muted" />
        </div>
      </div>
    </div>
  );
};

export default BookmarkCardSkeleton;
