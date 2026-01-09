import React from 'react';
import { Clock, RefreshCw, AlarmClockOff, Archive, ExternalLink } from 'lucide-react';
import { Button } from './ui/button';

/**
 * ResurfacingCard - Displays a bookmark suggestion from the Intelligent Resurfacing Engine
 * 
 * Shows bookmark with:
 * - Title, domain, thumbnail
 * - Reading time badge
 * - Why it's being resurfaced
 * - Actions: Read Again, Snooze, Archive
 */
const ResurfacingCard = ({
  bookmark,
  onReadAgain,
  onSnooze,
  onArchive,
  isLoading = false
}) => {
  const {
    id,
    title,
    url,
    domain,
    thumbnail,
    favicon,
    reading_time,
    resurfacing_reason,
    days_since_access,
    ai_summary
  } = bookmark;

  const handleReadAgain = () => {
    // Open in new tab and notify parent
    window.open(url, '_blank');
    if (onReadAgain) onReadAgain(id);
  };

  return (
    <div className="bg-background border-2 border-foreground p-4 hover:shadow-brutal transition-shadow">
      <div className="flex gap-4">
        {/* Thumbnail */}
        <div className="flex-shrink-0 w-20 h-20 bg-muted border-2 border-foreground overflow-hidden">
          {thumbnail ? (
            <img
              src={thumbnail}
              alt=""
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-primary/10">
              {favicon ? (
                <img src={favicon} alt="" className="w-8 h-8" />
              ) : (
                <RefreshCw className="w-6 h-6 text-muted-foreground" />
              )}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h4 className="font-heading font-bold text-sm uppercase leading-tight line-clamp-2 mb-1">
            {title || 'Untitled'}
          </h4>

          {/* Domain & Reading Time */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
            <span className="font-mono uppercase truncate">{domain}</span>
            {reading_time && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {reading_time} min
                </span>
              </>
            )}
          </div>

          {/* One-sentence summary */}
          {ai_summary?.one_sentence && (
            <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
              {ai_summary.one_sentence}
            </p>
          )}

          {/* Resurfacing reason */}
          <div className="flex items-center gap-1 text-xs text-primary font-mono uppercase tracking-wider">
            <RefreshCw className="w-3 h-3" />
            {resurfacing_reason}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t-2 border-foreground/20">
        <Button
          variant="default"
          size="sm"
          onClick={handleReadAgain}
          disabled={isLoading}
          className="flex-1"
        >
          <ExternalLink className="w-3 h-3 mr-1" />
          READ AGAIN
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onSnooze && onSnooze(id, 7)}
          disabled={isLoading}
          title="Snooze for 1 week"
        >
          <AlarmClockOff className="w-3 h-3" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onArchive && onArchive(id)}
          disabled={isLoading}
          title="Don't show again"
        >
          <Archive className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
};

/**
 * ResurfacingSection - Container for multiple resurfacing cards
 * 
 * Shows a header and grid of resurfacing suggestions
 */
export const ResurfacingSection = ({
  suggestions = [],
  onReadAgain,
  onSnooze,
  onArchive,
  isLoading = false,
  onRefresh
}) => {
  if (suggestions.length === 0 && !isLoading) {
    return null;
  }

  return (
    <div className="mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-primary border-2 border-foreground">
            <RefreshCw className="w-4 h-4 text-primary-foreground" />
          </div>
          <h3 className="font-heading font-bold uppercase tracking-wide">
            Worth Revisiting
          </h3>
        </div>
        {onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
            className="text-xs"
          >
            <RefreshCw className={`w-3 h-3 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
            REFRESH
          </Button>
        )}
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          // Loading skeletons
          [...Array(3)].map((_, i) => (
            <div key={i} className="bg-muted border-2 border-foreground/30 p-4 animate-pulse">
              <div className="flex gap-4">
                <div className="w-20 h-20 bg-foreground/10" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-foreground/10 w-3/4" />
                  <div className="h-3 bg-foreground/10 w-1/2" />
                  <div className="h-3 bg-foreground/10 w-full" />
                </div>
              </div>
            </div>
          ))
        ) : (
          suggestions.map((bookmark) => (
            <ResurfacingCard
              key={bookmark.id}
              bookmark={bookmark}
              onReadAgain={onReadAgain}
              onSnooze={onSnooze}
              onArchive={onArchive}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default ResurfacingCard;
