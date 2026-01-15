import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { CheckIcon, FileTextIcon, SparklesIcon, PlusIcon } from 'lucide-react';

const ConnectionCard = ({ connection }) => {
  return (
    <div className="flex items-start gap-3 p-3 border-2 border-foreground bg-card shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150">
      <div className="flex-shrink-0 w-8 h-8 border border-foreground bg-muted flex items-center justify-center">
        {connection.favicon ? (
          <img 
            src={connection.favicon} 
            alt="" 
            className="w-4 h-4" 
            onError={(e) => e.target.style.display = 'none'} 
          />
        ) : (
          <FileTextIcon className="w-4 h-4 text-muted-foreground" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-heading font-bold text-sm line-clamp-1">
          {connection.title}
        </h4>
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mt-1">
          {connection.connection_reason || connection.connection_type} • {connection.domain}
        </p>
      </div>
    </div>
  );
};

const SkeletonCard = () => {
  return (
    <div className="flex items-start gap-3 p-3 border-2 border-foreground bg-card animate-pulse">
      <div className="flex-shrink-0 w-8 h-8 border border-foreground bg-muted" />
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-muted w-3/4" />
        <div className="h-3 bg-muted w-1/2" />
      </div>
    </div>
  );
};

const ConnectionsModal = ({ open, onOpenChange, data, onViewBookmark }) => {
  const bookmark = data?.bookmark;
  const connections = data?.connections || [];
  const isLoading = !data;

  const handleViewBookmark = () => {
    if (bookmark?.id && onViewBookmark) {
      onViewBookmark(bookmark.id);
    }
    onOpenChange(false);
  };

  const handleSaveAnother = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent 
        className="border-2 border-foreground shadow-brutal max-w-md"
        aria-describedby="connections-description"
      >
        <DialogHeader className="border-b-2 border-foreground pb-4 -mx-6 px-6 -mt-2">
          <div className="flex items-center gap-2 text-green-700">
            <div className="w-6 h-6 border-2 border-foreground bg-green-100 flex items-center justify-center">
              <CheckIcon className="w-4 h-4" />
            </div>
            <DialogTitle className="font-mono text-sm uppercase tracking-wider">
              Bookmark Saved
            </DialogTitle>
          </div>
          <DialogDescription id="connections-description" className="sr-only">
            Your bookmark has been saved. View related connections from your knowledge base.
          </DialogDescription>
        </DialogHeader>

        {bookmark && (
          <div className="py-4 border-b-2 border-foreground -mx-6 px-6">
            <h3 className="font-heading font-bold text-lg line-clamp-2">
              "{bookmark.title || 'Untitled'}"
            </h3>
            <div className="flex items-center gap-2 mt-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
              <span>{bookmark.domain}</span>
              <span>•</span>
              <div className="flex items-center gap-1 text-accent">
                <SparklesIcon className="w-3 h-3 animate-pulse" />
                <span>AI processing...</span>
              </div>
            </div>
          </div>
        )}

        <div className="py-4 -mx-6 px-6">
          <h4 className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-4">
            Connects to Your Knowledge
          </h4>

          {isLoading ? (
            <div className="space-y-3">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : connections.length === 0 ? (
            <div className="p-4 border-2 border-foreground bg-muted text-center">
              <div className="w-10 h-10 mx-auto mb-3 border-2 border-foreground bg-primary/10 flex items-center justify-center">
                <PlusIcon className="w-5 h-5 text-primary" />
              </div>
              <p className="font-heading font-bold text-sm">
                This is your first bookmark about {bookmark?.domain || 'this topic'}!
              </p>
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mt-2">
                Save more to build your knowledge graph
              </p>
            </div>
          ) : (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {connections.slice(0, 5).map((connection) => (
                <ConnectionCard key={connection.id} connection={connection} />
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 pt-4 border-t-2 border-foreground -mx-6 px-6 -mb-2">
          <Button
            onClick={handleViewBookmark}
            className="flex-1 border-2 border-foreground bg-foreground text-background hover:bg-foreground/90 shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150 font-mono text-xs uppercase tracking-wider"
          >
            View Bookmark
          </Button>
          <Button
            variant="outline"
            onClick={handleSaveAnother}
            className="flex-1 border-2 border-foreground bg-background hover:bg-muted shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150 font-mono text-xs uppercase tracking-wider"
          >
            Save Another
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ConnectionsModal;
