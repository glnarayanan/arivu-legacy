import { ExternalLinkIcon, TrashIcon, SparklesIcon, ClockIcon, BookOpenIcon } from 'lucide-react';
import { Button } from './ui/button';
import { formatDistanceToNow } from 'date-fns';

const BookmarkCard = ({ bookmark, onDelete, onClick, bulkMode, isSelected, onToggleSelect, isHighlighted, viewMode = 'list' }) => {
  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm('Delete this bookmark?')) {
      onDelete(bookmark.id);
    }
  };

  const handleExternalLink = async (e) => {
    e.stopPropagation();

    // Track external URL access (Phase 1: fire and forget)
    try {
      await axiosInstance.post(`/bookmarks/${bookmark.id}/accessed?source=external`);
    } catch (error) {
      console.error('Failed to track external access:', error);
      // Don't block user from opening URL
    }

    window.open(bookmark.url, '_blank');
  };

  const handleCardClick = (e) => {
    if (bulkMode) {
      e.stopPropagation();
      onToggleSelect();
    } else {
      onClick();
    }
  };

  // List View (Compact)
  if (viewMode === 'list') {
    return (
      <div
        data-testid={`bookmark-card-${bookmark.id}`}
        onClick={handleCardClick}
        className={`group relative flex items-center gap-4 p-4 rounded-xl border bg-card hover:border-primary/20 hover:shadow-md transition-all cursor-pointer ${
          isHighlighted ? 'ring-2 ring-primary' : ''
        } ${isSelected ? 'ring-2 ring-violet-500' : ''}`}
      >
        {/* Bulk Select Checkbox */}
        {bulkMode && (
          <div className="flex-shrink-0">
            <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${ 
              isSelected ? 'bg-violet-500 border-violet-500' : 'bg-white border-gray-300'
            }`}>
              {isSelected && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          </div>
        )}

        {/* Thumbnail */}
        <div className="flex-shrink-0 w-12 h-12 rounded-lg overflow-hidden bg-muted">
          {bookmark.thumbnail ? (
            <img
              src={bookmark.thumbnail}
              alt={bookmark.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.parentElement.innerHTML = `<div class="w-full h-full flex items-center justify-center text-2xl text-muted-foreground opacity-30">${bookmark.domain?.charAt(0).toUpperCase()}</div>`;
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-2xl text-muted-foreground opacity-30">
              {bookmark.domain?.charAt(0).toUpperCase()}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2 mb-1">
            {bookmark.read_status && (
              <div className="flex-shrink-0 flex items-center gap-1 px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 rounded text-xs">
                <svg className="w-3 h-3 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
            )}
            <h3 className="font-medium text-base line-clamp-1 flex-1">
              {bookmark.title || bookmark.url}
            </h3>
          </div>

          {/* AI Summary */}
          {bookmark.ai_summary?.one_sentence && (
            <p className="text-sm text-muted-foreground line-clamp-1 mb-2">
              {bookmark.ai_summary.one_sentence}
            </p>
          )}

          {/* Meta Info */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              {bookmark.favicon && (
                <img src={bookmark.favicon} alt="" className="w-3 h-3 rounded" onError={(e) => e.target.style.display = 'none'} />
              )}
              <span className="truncate max-w-[120px]">{bookmark.domain}</span>
            </div>
            <span>•</span>
            <AgingIndicator bookmark={bookmark} size="compact" />
            <span>•</span>
            <span>{formatDistanceToNow(new Date(bookmark.created_at), { addSuffix: true })}</span>
            {bookmark.reading_time && (
              <>
                <span>•</span>
                <div className="flex items-center gap-1">
                  <BookOpenIcon className="w-3 h-3" />
                  <span className="font-mono">{bookmark.reading_time} min</span>
                </div>
              </>
            )}
          </div>

          {/* Tags */}
          {bookmark.ai_summary?.suggested_tags && bookmark.ai_summary.suggested_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {bookmark.ai_summary.suggested_tags.slice(0, 3).map((tag, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono bg-muted text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* AI Processing */}
          {bookmark.ai_summary?.processing_status === 'pending' && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-2">
              <SparklesIcon className="w-3 h-3 animate-pulse ai-gradient" />
              <span>AI processing...</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex-shrink-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            data-testid={`external-link-${bookmark.id}`}
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 rounded-full"
            onClick={handleExternalLink}
          >
            <ExternalLinkIcon className="w-4 h-4" />
          </Button>
          <Button
            data-testid={`delete-bookmark-${bookmark.id}`}
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 rounded-full text-destructive hover:text-destructive"
            onClick={handleDelete}
          >
            <TrashIcon className="w-4 h-4" />
          </Button>
        </div>
      </div>
    );
  }

  // Grid View (Card)
  return (
    <div
      data-testid={`bookmark-card-${bookmark.id}`}
      onClick={handleCardClick}
      className={`bookmark-card group relative overflow-hidden rounded-2xl border bg-card transition-all hover:border-primary/20 hover:shadow-lg cursor-pointer ${
        isHighlighted ? 'ring-2 ring-primary' : ''
      } ${isSelected ? 'ring-2 ring-violet-500' : ''}`}
    >
      {/* Bulk Select Checkbox */}
      {bulkMode && (
        <div className="absolute top-3 right-3 z-10">
          <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${ 
            isSelected ? 'bg-violet-500 border-violet-500' : 'bg-white border-gray-300'
          }`}>
            {isSelected && (
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
        </div>
      )}

      {/* Read Status Badge */}
      {bookmark.read_status && (
        <div className="absolute top-3 left-3 z-10">
          <div className="flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 rounded-full">
            <svg className="w-3 h-3 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-xs font-medium text-green-600 dark:text-green-400">Read</span>
          </div>
        </div>
      )}

      {/* Compact Thumbnail */}
      <div className="aspect-[16/9] overflow-hidden bg-muted">
        {bookmark.thumbnail ? (
          <img
            src={bookmark.thumbnail}
            alt={bookmark.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center">
            <div className="text-3xl font-mono text-muted-foreground opacity-20">
              {bookmark.domain?.charAt(0).toUpperCase()}
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-2">
        {/* Title */}
        <h3 className="font-heading font-semibold text-base line-clamp-2 leading-snug">
          {bookmark.title || bookmark.url}
        </h3>

        {/* AI Summary */}
        {bookmark.ai_summary?.one_sentence && (
          <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
            {bookmark.ai_summary.one_sentence}
          </p>
        )}

        {/* Tags */}
        {bookmark.ai_summary?.suggested_tags && bookmark.ai_summary.suggested_tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {bookmark.ai_summary.suggested_tags.slice(0, 3).map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono bg-muted text-muted-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* AI Processing */}
        {bookmark.ai_summary?.processing_status === 'pending' && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <SparklesIcon className="w-3 h-3 animate-pulse ai-gradient" />
              <span>AI processing...</span>
            </div>
            <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-violet-500 to-teal-400 rounded-full animate-pulse" style={{width: '60%'}}></div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-border/50">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {bookmark.favicon && (
              <img src={bookmark.favicon} alt="" className="w-4 h-4 rounded" onError={(e) => e.target.style.display = 'none'} />
            )}
            <span className="truncate max-w-[120px]">{bookmark.domain}</span>
          </div>
          <div className="flex items-center gap-1">
            <Button
              data-testid={`external-link-${bookmark.id}`}
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 rounded-full"
              onClick={handleExternalLink}
            >
              <ExternalLinkIcon className="w-3.5 h-3.5" />
            </Button>
            <Button
              data-testid={`delete-bookmark-${bookmark.id}`}
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 rounded-full text-destructive hover:text-destructive"
              onClick={handleDelete}
            >
              <TrashIcon className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Reading time & Date */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <ClockIcon className="w-3 h-3" />
              <span>{formatDistanceToNow(new Date(bookmark.created_at), { addSuffix: true })}</span>
            </div>
            <AgingIndicator bookmark={bookmark} size="compact" />
          </div>
          {bookmark.reading_time && (
            <div className="flex items-center gap-1 px-2 py-0.5 bg-muted rounded-full">
              <BookOpenIcon className="w-3 h-3" />
              <span className="font-mono">{bookmark.reading_time} min</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BookmarkCard;
