import { useState, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { X, Sparkles, Network, FolderPlus, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/button';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

const FIRST_GUIDE_KEY = 'arivu_first_bookmark_guide_seen';

/**
 * Contextual guide shown after user saves their first bookmark.
 * Explains what AI is doing and suggests next steps.
 */
export const FirstBookmarkGuide = ({ bookmarkId, onDismiss }) => {
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const hasSeen = localStorage.getItem(FIRST_GUIDE_KEY);
    if (!hasSeen && bookmarkId) {
      // Show after a delay to let the save animation complete
      const timer = setTimeout(() => setIsVisible(true), 2000);
      return () => clearTimeout(timer);
    }
  }, [bookmarkId]);

  const handleDismiss = () => {
    localStorage.setItem(FIRST_GUIDE_KEY, 'true');
    setIsVisible(false);
    onDismiss?.();
  };

  const handleViewBookmark = () => {
    localStorage.setItem(FIRST_GUIDE_KEY, 'true');
    setIsVisible(false);
    navigate(`/bookmark/${bookmarkId}`);
  };

  const handleViewGraph = () => {
    localStorage.setItem(FIRST_GUIDE_KEY, 'true');
    setIsVisible(false);
    navigate('/knowledge-graph');
  };

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 20 }}
        transition={brutalSpring}
        className="fixed bottom-24 right-6 z-50 w-[340px] bg-card border-2 border-foreground shadow-brutal"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b-2 border-foreground bg-accent/10">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-accent" />
            <span className="font-heading font-bold uppercase tracking-wide text-sm">
              AI is Working
            </span>
          </div>
          <button
            onClick={handleDismiss}
            className="p-1 hover:bg-muted transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          <p className="text-sm mb-4">
            Your bookmark is being processed. In a moment, you'll see:
          </p>

          <div className="space-y-3 mb-4">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
              <span className="text-sm">AI-generated summary</span>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
              <span className="text-sm">Auto-suggested tags</span>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
              <span className="text-sm">Key insights extracted</span>
            </div>
          </div>

          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-4">
            What's next?
          </p>

          <div className="space-y-2">
            <Button
              onClick={handleViewBookmark}
              className="w-full rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all justify-start"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              View AI Summary
              <ArrowRight className="w-4 h-4 ml-auto" />
            </Button>

            <Button
              onClick={handleViewGraph}
              variant="outline"
              className="w-full rounded-none border-2 border-foreground bg-background hover:bg-muted transition-all justify-start"
            >
              <Network className="w-4 h-4 mr-2" />
              Explore Knowledge Graph
              <ArrowRight className="w-4 h-4 ml-auto" />
            </Button>

            <button
              onClick={handleDismiss}
              className="w-full text-center font-mono text-xs uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors py-2"
            >
              Add more bookmarks first
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default FirstBookmarkGuide;
