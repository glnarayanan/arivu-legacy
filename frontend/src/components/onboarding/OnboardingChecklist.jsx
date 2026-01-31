import { useState, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { CheckCircle2, Circle, ChevronDown, ChevronUp, X, Bookmark, Network, FolderPlus, Tag } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

const CHECKLIST_STORAGE_KEY = 'arivu_onboarding_checklist';
const CHECKLIST_DISMISSED_KEY = 'arivu_onboarding_dismissed';

/**
 * Getting started checklist that tracks onboarding progress.
 * Shows in sidebar when user has incomplete tasks.
 */
export const OnboardingChecklist = ({
  bookmarkCount = 0,
  collectionCount = 0,
  hasVisitedGraph = false,
  onOpenAddBookmark
}) => {
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();
  const [isExpanded, setIsExpanded] = useState(true);
  const [isDismissed, setIsDismissed] = useState(false);
  const [completedItems, setCompletedItems] = useState([]);

  // Load dismissed state
  useEffect(() => {
    const dismissed = localStorage.getItem(CHECKLIST_DISMISSED_KEY);
    if (dismissed === 'true') {
      setIsDismissed(true);
    }
  }, []);

  // Track completed items
  useEffect(() => {
    const completed = [];

    if (bookmarkCount >= 1) completed.push('first_bookmark');
    if (bookmarkCount >= 3) completed.push('three_bookmarks');
    if (collectionCount >= 1) completed.push('first_collection');
    if (hasVisitedGraph) completed.push('visit_graph');

    setCompletedItems(completed);

    // Persist to localStorage
    localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(completed));
  }, [bookmarkCount, collectionCount, hasVisitedGraph]);

  const checklistItems = [
    {
      id: 'first_bookmark',
      label: 'Save your first bookmark',
      icon: Bookmark,
      action: () => onOpenAddBookmark?.(),
      actionLabel: 'Add bookmark',
    },
    {
      id: 'three_bookmarks',
      label: 'Save 3 bookmarks',
      icon: Bookmark,
      action: () => onOpenAddBookmark?.(),
      actionLabel: 'Add more',
    },
    {
      id: 'first_collection',
      label: 'Create a collection',
      icon: FolderPlus,
      action: null, // Handled by sidebar
      actionLabel: 'Use sidebar',
    },
    {
      id: 'visit_graph',
      label: 'Explore Knowledge Graph',
      icon: Network,
      action: () => navigate('/knowledge-graph'),
      actionLabel: 'View graph',
    },
  ];

  const completedCount = completedItems.length;
  const totalCount = checklistItems.length;
  const isComplete = completedCount === totalCount;

  // Auto-dismiss when complete
  useEffect(() => {
    if (isComplete && !isDismissed) {
      const timer = setTimeout(() => {
        handleDismiss();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isComplete, isDismissed]);

  const handleDismiss = () => {
    localStorage.setItem(CHECKLIST_DISMISSED_KEY, 'true');
    setIsDismissed(true);
  };

  if (isDismissed || isComplete) return null;

  return (
    <motion.div
      initial={shouldReduceMotion ? {} : { opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={shouldReduceMotion ? {} : { opacity: 0, y: -10 }}
      transition={brutalSpring}
      className="border-2 border-foreground bg-card mb-4"
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs uppercase tracking-wider font-medium">
            Getting Started
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            {completedCount}/{totalCount}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDismiss();
            }}
            className="p-1 hover:bg-muted rounded-none"
            aria-label="Dismiss checklist"
          >
            <X className="w-3 h-3 text-muted-foreground" />
          </button>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </div>
      </button>

      {/* Progress bar */}
      <div className="h-1 bg-muted">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(completedCount / totalCount) * 100}%` }}
          transition={brutalSpring}
          className="h-full bg-primary"
        />
      </div>

      {/* Checklist items */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={shouldReduceMotion ? {} : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={shouldReduceMotion ? {} : { height: 0, opacity: 0 }}
            transition={brutalSpring}
            className="overflow-hidden"
          >
            <div className="p-3 pt-2 space-y-2">
              {checklistItems.map((item) => {
                const isCompleted = completedItems.includes(item.id);
                const Icon = item.icon;

                return (
                  <div
                    key={item.id}
                    className={`flex items-center gap-3 p-2 transition-colors ${
                      isCompleted ? 'opacity-60' : 'hover:bg-muted/30'
                    }`}
                  >
                    {/* Checkbox */}
                    <div className="flex-shrink-0">
                      {isCompleted ? (
                        <CheckCircle2 className="w-4 h-4 text-primary" />
                      ) : (
                        <Circle className="w-4 h-4 text-muted-foreground" />
                      )}
                    </div>

                    {/* Label */}
                    <span className={`flex-1 font-mono text-xs uppercase tracking-wider ${
                      isCompleted ? 'line-through text-muted-foreground' : ''
                    }`}>
                      {item.label}
                    </span>

                    {/* Action button */}
                    {!isCompleted && item.action && (
                      <button
                        onClick={item.action}
                        className="font-mono text-xs uppercase tracking-wider text-accent hover:text-accent/80 transition-colors"
                      >
                        {item.actionLabel}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default OnboardingChecklist;
