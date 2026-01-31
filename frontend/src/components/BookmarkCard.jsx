import { ExternalLinkIcon, TrashIcon, SparklesIcon, ClockIcon, BookOpenIcon } from 'lucide-react';
import { Button } from './ui/button';
import { formatDistanceToNow } from 'date-fns';
import AgingIndicator from './AgingIndicator';
import axiosInstance from '../utils/axiosConfig';
import { LoadingMessages } from './delight';

const BookmarkCard = ({ bookmark, onDelete, onClick, bulkMode, isSelected, onToggleSelect, isHighlighted, viewMode = 'list' }) => {
  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm('Delete this bookmark?')) {
      onDelete(bookmark.id);
    }
  };

  const handleExternalLink = async (e) => {
    e.stopPropagation();

    try {
      await axiosInstance.post(`/bookmarks/${bookmark.id}/accessed?source=external`);
    } catch (error) {
      console.error('Failed to track external access:', error);
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

  if (viewMode === 'list') {
    return (
      <div
        data-testid={`bookmark-card-${bookmark.id}`}
        onClick={handleCardClick}
        className={`group relative flex items-center gap-4 p-4 border-2 border-foreground bg-card shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150 cursor-pointer ${
          isHighlighted ? 'ring-2 ring-primary' : ''
        } ${isSelected ? 'ring-2 ring-primary' : ''}`}
      >
        {bulkMode && (
          <div className="flex-shrink-0">
            <div className={`w-5 h-5 border-2 border-foreground flex items-center justify-center ${ 
              isSelected ? 'bg-primary' : 'bg-white'
            }`}>
              {isSelected && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          </div>
        )}

        <div className="flex-shrink-0 w-12 h-12 border border-foreground overflow-hidden bg-muted">
          {bookmark.thumbnail ? (
            <img
              src={bookmark.thumbnail}
              alt={bookmark.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.style.display = 'none';
                const fallbackDiv = document.createElement('div');
                fallbackDiv.className = 'w-full h-full flex items-center justify-center text-xl font-heading font-bold text-muted-foreground opacity-50';
                fallbackDiv.textContent = bookmark.domain?.charAt(0).toUpperCase() || '';
                e.target.parentElement.appendChild(fallbackDiv);
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xl font-heading font-bold text-muted-foreground opacity-50">
              {bookmark.domain?.charAt(0).toUpperCase()}
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2 mb-1">
            {bookmark.read_status && (
              <div className="flex-shrink-0 flex items-center gap-1 px-1.5 py-0.5 bg-green-100 border border-foreground font-mono text-xs uppercase">
                <svg className="w-3 h-3 text-green-700" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
            )}
            <h3 className="font-heading font-bold text-base line-clamp-1 flex-1">
              {bookmark.title || bookmark.url}
            </h3>
          </div>

          {bookmark.ai_summary?.one_sentence && (
            <p className="text-sm text-muted-foreground line-clamp-1 mb-2">
              {bookmark.ai_summary.one_sentence}
            </p>
          )}

          <div className="flex items-center gap-3 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            <div className="flex items-center gap-1">
              {bookmark.favicon && (
                <img src={bookmark.favicon} alt="" className="w-3 h-3" onError={(e) => e.target.style.display = 'none'} />
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
                  <span>{bookmark.reading_time} min</span>
                </div>
              </>
            )}
          </div>

          {bookmark.ai_summary?.suggested_tags && bookmark.ai_summary.suggested_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {bookmark.ai_summary.suggested_tags.slice(0, 3).map((tag, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2 py-0.5 border border-foreground bg-muted font-mono text-xs uppercase tracking-wider text-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {bookmark.ai_summary?.processing_status === 'pending' && (
            <div className="flex items-center gap-2 text-accent mt-2">
              <SparklesIcon className="w-3 h-3 animate-pulse" />
              <LoadingMessages
                messages={[
                  'Analyzing content...',
                  'Extracting concepts...',
                  'Building connections...',
                  'Training your brain...'
                ]}
                className="text-accent"
              />
            </div>
          )}
        </div>

        <div className="flex-shrink-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            data-testid={`external-link-${bookmark.id}`}
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 hover:bg-muted"
            onClick={handleExternalLink}
          >
            <ExternalLinkIcon className="w-4 h-4" />
          </Button>
          <Button
            data-testid={`delete-bookmark-${bookmark.id}`}
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={handleDelete}
          >
            <TrashIcon className="w-4 h-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid={`bookmark-card-${bookmark.id}`}
      onClick={handleCardClick}
      className={`bookmark-card group relative overflow-hidden border-2 border-foreground bg-card shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150 cursor-pointer ${
        isHighlighted ? 'ring-2 ring-primary' : ''
      } ${isSelected ? 'ring-2 ring-primary' : ''}`}
    >
      {bulkMode && (
        <div className="absolute top-3 right-3 z-10">
          <div className={`w-6 h-6 border-2 border-foreground flex items-center justify-center ${ 
            isSelected ? 'bg-primary' : 'bg-white'
          }`}>
            {isSelected && (
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
        </div>
      )}

      {bookmark.read_status && (
        <div className="absolute top-3 left-3 z-10">
          <div className="flex items-center gap-1 px-2 py-1 bg-green-100 border border-foreground">
            <svg className="w-3 h-3 text-green-700" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="font-mono text-xs uppercase text-green-700">Read</span>
          </div>
        </div>
      )}

      <div className="aspect-[16/9] overflow-hidden border-b-2 border-foreground bg-muted">
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
          <div className="w-full h-full bg-muted flex items-center justify-center">
            <div className="text-3xl font-heading font-bold text-muted-foreground opacity-20">
              {bookmark.domain?.charAt(0).toUpperCase()}
            </div>
          </div>
        )}
      </div>

      <div className="p-4 space-y-3">
        <h3 className="font-heading font-bold text-base line-clamp-2 leading-snug">
          {bookmark.title || bookmark.url}
        </h3>

        {bookmark.ai_summary?.one_sentence && (
          <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
            {bookmark.ai_summary.one_sentence}
          </p>
        )}

        {bookmark.ai_summary?.suggested_tags && bookmark.ai_summary.suggested_tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {bookmark.ai_summary.suggested_tags.slice(0, 3).map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 border border-foreground bg-muted font-mono text-xs uppercase tracking-wider text-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {bookmark.ai_summary?.processing_status === 'pending' && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-accent">
              <SparklesIcon className="w-3 h-3 animate-pulse" />
              <LoadingMessages
                messages={[
                  'Analyzing content...',
                  'Extracting concepts...',
                  'Building connections...',
                  'Training your brain...'
                ]}
                className="text-accent"
              />
            </div>
            <div className="w-full bg-muted h-1.5 overflow-hidden border border-foreground/10">
              <div className="h-full bg-accent animate-pulse" style={{width: '60%'}}></div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between pt-3 border-t-2 border-foreground">
          <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            {bookmark.favicon && (
              <img src={bookmark.favicon} alt="" className="w-4 h-4" onError={(e) => e.target.style.display = 'none'} />
            )}
            <span className="truncate max-w-[120px]">{bookmark.domain}</span>
          </div>
          <div className="flex items-center gap-1">
            <Button
              data-testid={`external-link-${bookmark.id}`}
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 hover:bg-muted"
              onClick={handleExternalLink}
            >
              <ExternalLinkIcon className="w-3.5 h-3.5" />
            </Button>
            <Button
              data-testid={`delete-bookmark-${bookmark.id}`}
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={handleDelete}
            >
              <TrashIcon className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        <div className="flex items-center justify-between font-mono text-xs uppercase tracking-wider text-muted-foreground pt-1">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <ClockIcon className="w-3 h-3" />
              <span>{formatDistanceToNow(new Date(bookmark.created_at), { addSuffix: true })}</span>
            </div>
            <AgingIndicator bookmark={bookmark} size="compact" />
          </div>
          {bookmark.reading_time && (
            <div className="flex items-center gap-1 px-2 py-0.5 border border-foreground/20 bg-muted">
              <BookOpenIcon className="w-3 h-3" />
              <span>{bookmark.reading_time} min</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BookmarkCard;
