import { motion, useReducedMotion } from 'framer-motion';
import { Sparkles, BookmarkPlus, FolderPlus, Network, BarChart3, ArrowRight } from 'lucide-react';
import { Button } from '../ui/button';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

/**
 * Enhanced empty state component with better guidance and next steps.
 * Replaces basic "No bookmarks yet" with actionable guidance.
 */
export const EmptyStateGuide = ({
  type = 'bookmarks',
  onPrimaryAction,
  _u19_onSecondaryAction,
}) => {
  const shouldReduceMotion = useReducedMotion();

  const configs = {
    bookmarks: {
      icon: Sparkles,
      iconBg: 'bg-primary',
      title: 'Your Second Brain Awaits',
      description: 'Save any webpage and let AI do the heavy lifting—summarizing, tagging, and connecting your knowledge.',
      primaryLabel: 'Save Your First Bookmark',
      primaryIcon: BookmarkPlus,
      tips: [
        'Paste any URL to save an article, video, or page',
        'AI automatically extracts key insights',
        'Watch connections form in your Knowledge Graph',
      ],
    },
    collections: {
      icon: FolderPlus,
      iconBg: 'bg-accent',
      title: 'Organize Your Way',
      description: 'Collections help you group related bookmarks. Create one for a project, topic, or anything that matters to you.',
      primaryLabel: 'Create Collection',
      primaryIcon: FolderPlus,
      tips: [
        'Group bookmarks by project or topic',
        'Drag and drop bookmarks into collections',
        'Collections appear in your sidebar',
      ],
    },
    graph: {
      icon: Network,
      iconBg: 'bg-foreground',
      title: 'See Your Knowledge Connect',
      description: 'The Knowledge Graph visualizes how your saved content relates. Save more bookmarks to see the connections emerge.',
      primaryLabel: 'Add Bookmarks First',
      primaryIcon: BookmarkPlus,
      tips: [
        'Each bookmark becomes a node',
        'AI finds semantic connections',
        'Click nodes to explore relationships',
      ],
    },
    analytics: {
      icon: BarChart3,
      iconBg: 'bg-accent',
      title: 'Track Your Reading',
      description: 'Analytics show your reading patterns and habits. Save some bookmarks to see your stats.',
      primaryLabel: 'Start Saving',
      primaryIcon: BookmarkPlus,
      tips: [
        'See reading time estimates',
        'Track what you\'ve read',
        'Discover reading trends',
      ],
    },
  };

  const config = configs[type] || configs.bookmarks;
  const Icon = config.icon;
  const PrimaryIcon = config.primaryIcon;

  return (
    <motion.div
      initial={shouldReduceMotion ? {} : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={brutalSpring}
      className="max-w-lg mx-auto py-12 px-4"
    >
      {/* Icon */}
      <motion.div
        initial={shouldReduceMotion ? {} : { scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ ...brutalSpring, delay: 0.1 }}
        className="flex justify-center mb-6"
      >
        <div className={`w-20 h-20 border-2 border-foreground ${config.iconBg} flex items-center justify-center shadow-brutal`}>
          <Icon className={`w-10 h-10 ${config.iconBg === 'bg-foreground' ? 'text-background' : 'text-primary-foreground'}`} />
        </div>
      </motion.div>

      {/* Title */}
      <motion.h2
        initial={shouldReduceMotion ? {} : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...brutalSpring, delay: 0.15 }}
        className="font-display text-3xl font-bold uppercase tracking-wide text-center mb-3"
      >
        {config.title}
      </motion.h2>

      {/* Description */}
      <motion.p
        initial={shouldReduceMotion ? {} : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...brutalSpring, delay: 0.2 }}
        className="text-muted-foreground text-center mb-8 font-body"
      >
        {config.description}
      </motion.p>

      {/* Tips */}
      <motion.div
        initial={shouldReduceMotion ? {} : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...brutalSpring, delay: 0.25 }}
        className="border-2 border-dashed border-muted-foreground/30 p-4 mb-8"
      >
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
          How it works
        </p>
        <ul className="space-y-2">
          {config.tips.map((tip, index) => (
            <li key={index} className="flex items-start gap-3">
              <ArrowRight className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
              <span className="text-sm">{tip}</span>
            </li>
          ))}
        </ul>
      </motion.div>

      {/* Primary action */}
      <motion.div
        initial={shouldReduceMotion ? {} : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...brutalSpring, delay: 0.3 }}
        className="flex justify-center"
      >
        <Button
          onClick={onPrimaryAction}
          size="lg"
          className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
        >
          <PrimaryIcon className="w-5 h-5 mr-2" />
          {config.primaryLabel}
        </Button>
      </motion.div>
    </motion.div>
  );
};

export default EmptyStateGuide;
