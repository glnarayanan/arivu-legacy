import { ExternalLinkIcon, TrashIcon, SparklesIcon, ClockIcon } from 'lucide-react';
import { Button } from './ui/button';
import { formatDistanceToNow } from 'date-fns';

const BookmarkCard = ({ bookmark, onDelete, onClick }) => {
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

  return (
    <div
      data-testid={`bookmark-card-${bookmark.id}`}
      onClick={onClick}
      className="bookmark-card group relative overflow-hidden rounded-2xl border bg-card transition-all hover:border-primary/20 hover:shadow-lg cursor-pointer"
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
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <SparklesIcon className="w-3 h-3 animate-pulse ai-gradient" />
            <span>AI processing...</span>
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
