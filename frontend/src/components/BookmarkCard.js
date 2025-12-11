import { ExternalLinkIcon, TrashIcon, SparklesIcon, ClockIcon } from 'lucide-react';
import { Button } from './ui/button';
import { formatDistanceToNow } from 'date-fns';

const BookmarkCard = ({ bookmark, onDelete, onClick, bulkMode, isSelected, onToggleSelect, isHighlighted }) => {
  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm('Delete this bookmark?')) {
      onDelete(bookmark.id);
    }
  };

  const handleExternalLink = (e) => {
    e.stopPropagation();
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

  return (
    <div
      data-testid={`bookmark-card-${bookmark.id}`}
      onClick={handleCardClick}
      className={`bookmark-card group relative overflow-hidden rounded-2xl border bg-card transition-all hover:border-primary/20 hover:shadow-lg cursor-pointer ${
        isHighlighted ? 'ring-2 ring-primary' : ''
      } ${isSelected ? 'ring-2 ring-violet-500' : ''}`}
    >
      {/* Thumbnail */}
      {bookmark.thumbnail ? (
        <div className="aspect-video overflow-hidden bg-muted">
          <img
            src={bookmark.thumbnail}
            alt={bookmark.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      ) : (
        <div className="aspect-video bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center">
          <div className="text-4xl font-mono text-muted-foreground opacity-20">
            {bookmark.domain?.charAt(0).toUpperCase()}
          </div>
        </div>
      )}

      {/* Bulk Select Checkbox */}
      {bulkMode && (
        <div className="absolute top-4 right-4 z-10">
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
        <div className="absolute top-4 left-4 z-10">
          <div className="flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 rounded-full">
            <svg className="w-3 h-3 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-xs font-medium text-green-600 dark:text-green-400">Read</span>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="p-5 space-y-3">
        {/* Title */}
        <h3 className="font-heading font-semibold text-lg line-clamp-2 leading-snug">
          {bookmark.title || bookmark.url}
        </h3>

        {/* AI Summary - One Sentence */}
        {bookmark.ai_summary?.one_sentence && (
          <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
            {bookmark.ai_summary.one_sentence}
          </p>
        )}

        {/* Tags */}
        {bookmark.ai_summary?.suggested_tags && bookmark.ai_summary.suggested_tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {bookmark.ai_summary.suggested_tags.slice(0, 3).map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono bg-muted text-muted-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* AI Processing Status */}
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
            <span className="truncate max-w-[150px]">{bookmark.domain}</span>
          </div>
          <div className="flex items-center gap-1">
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

        {/* Created timestamp */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <ClockIcon className="w-3 h-3" />
          <span>{formatDistanceToNow(new Date(bookmark.created_at), { addSuffix: true })}</span>
        </div>
      </div>
    </div>
  );
};

export default BookmarkCard;
