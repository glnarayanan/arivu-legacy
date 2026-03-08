import { motion, AnimatePresence } from 'framer-motion';
import { FileTextIcon, CheckIcon, XIcon, Loader2Icon, LinkIcon, BookOpenIcon } from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 25,
    },
  },
};

const ProcessingIndicator = ({ status }) => {
  if (status === 'pending') {
    return (
      <div className="w-5 h-5 border border-foreground bg-accent/10 flex items-center justify-center">
        <Loader2Icon className="w-3 h-3 text-accent animate-spin" />
      </div>
    );
  }
  if (status === 'complete') {
    return (
      <div className="w-5 h-5 border border-foreground bg-green-100 flex items-center justify-center">
        <CheckIcon className="w-3 h-3 text-green-700" />
      </div>
    );
  }
  if (status === 'failed') {
    return (
      <div className="w-5 h-5 border border-foreground bg-red-100 flex items-center justify-center">
        <XIcon className="w-3 h-3 text-red-700" />
      </div>
    );
  }
  return null;
};

const RecentBookmarkCard = ({ bookmark, isFocused, onFocus }) => {
  const status = bookmark.ai_summary?.processing_status || 'pending';

  return (
    <motion.button
      variants={itemVariants}
      onClick={() => onFocus(bookmark.id)}
      className={`w-full flex items-start gap-3 p-3 border-2 border-foreground bg-card text-left transition-all duration-150 ${
        isFocused
          ? 'bg-primary/5 shadow-none translate-x-[2px] translate-y-[2px]'
          : 'shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none'
      }`}
    >
      <div className="flex-shrink-0 w-8 h-8 border border-foreground bg-muted flex items-center justify-center">
        {bookmark.favicon ? (
          <img
            src={bookmark.favicon}
            alt=""
            className="w-4 h-4"
            onError={(e) => (e.target.style.display = 'none')}
          />
        ) : (
          <FileTextIcon className="w-4 h-4 text-muted-foreground" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-heading font-bold text-sm line-clamp-1">{bookmark.title}</h4>
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mt-1">
          {bookmark.domain}
        </p>
      </div>
      <ProcessingIndicator status={status} />
    </motion.button>
  );
};

const RelatedBookmarkCard = ({ bookmark, onView }) => {
  return (
    <motion.button
      variants={itemVariants}
      onClick={() => onView(bookmark.id)}
      className="w-full flex items-start gap-3 p-3 border-2 border-foreground bg-card text-left shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150"
    >
      <div className="flex-shrink-0 w-8 h-8 border border-foreground bg-muted flex items-center justify-center">
        {bookmark.favicon ? (
          <img
            src={bookmark.favicon}
            alt=""
            className="w-4 h-4"
            onError={(e) => (e.target.style.display = 'none')}
          />
        ) : (
          <FileTextIcon className="w-4 h-4 text-muted-foreground" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-heading font-bold text-sm line-clamp-1">{bookmark.title}</h4>
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mt-1">
          {bookmark.connection_reason} • {bookmark.domain}
        </p>
      </div>
      <LinkIcon className="w-4 h-4 text-accent flex-shrink-0 mt-1" />
    </motion.button>
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

const EmptyState = ({ icon: Icon, title, subtitle }) => {
  return (
    <div className="p-4 border-2 border-foreground bg-muted text-center">
      <div className="w-10 h-10 mx-auto mb-3 border-2 border-foreground bg-primary/10 flex items-center justify-center">
        <Icon className="w-5 h-5 text-primary" />
      </div>
      <p className="font-heading font-bold text-sm">{title}</p>
      <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mt-2">
        {subtitle}
      </p>
    </div>
  );
};

const RecentlySavedPanel = ({
  recentlySaved = [],
  focusedRecentId,
  onFocusRecent,
  relatedBookmarks = [],
  relatedLoading,
  onViewBookmark,
}) => {
  return (
    <div className="p-4 space-y-6">
      {/* Recently Saved Section */}
      <section>
        <h3 className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-4">
          Recently Saved
        </h3>

        {recentlySaved.length === 0 ? (
          <EmptyState
            icon={BookOpenIcon}
            title="No recent bookmarks"
            subtitle="Save a bookmark to see it here"
          />
        ) : (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-2"
          >
            <AnimatePresence mode="popLayout">
              {recentlySaved.slice(0, 5).map((bookmark) => (
                <RecentBookmarkCard
                  key={bookmark.id}
                  bookmark={bookmark}
                  isFocused={focusedRecentId === bookmark.id}
                  onFocus={onFocusRecent}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </section>

      {/* Related Bookmarks Section */}
      {focusedRecentId && (
        <motion.section
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <h3 className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-4">
            Related Bookmarks
          </h3>

          {relatedLoading ? (
            <div className="space-y-2">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : relatedBookmarks.length === 0 ? (
            <EmptyState
              icon={LinkIcon}
              title="No related bookmarks found"
              subtitle="This bookmark has no connections yet"
            />
          ) : (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="space-y-2"
            >
              {relatedBookmarks.map((bookmark) => (
                <RelatedBookmarkCard
                  key={bookmark.id}
                  bookmark={bookmark}
                  onView={onViewBookmark}
                />
              ))}
            </motion.div>
          )}
        </motion.section>
      )}
    </div>
  );
};

export default RecentlySavedPanel;
