import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Sparkles, ExternalLink, X, Link2 } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { checkMilestone, markMilestoneReached } from '../utils/milestones';
import { MilestoneToast } from './delight';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

// Container variants for staggered children
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0
    }
  }
};

// Child variants for staggered reveal
const childVariants = {
  hidden: { opacity: 0, y: -10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: brutalSpring
  }
};

// Reduced motion variants (instant appear)
const reducedContainerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 }
};

const reducedChildVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 }
};

// CSS keyframes for border glow pulse (injected once)
const glowKeyframes = `
@keyframes memoryGlow {
  0% {
    box-shadow: 4px 4px 0 #0F0F0F, 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% {
    box-shadow: 4px 4px 0 #0F0F0F, 0 0 20px 4px rgba(59, 130, 246, 0.6);
  }
  100% {
    box-shadow: 4px 4px 0 #0F0F0F, 0 0 0 0 rgba(59, 130, 246, 0);
  }
}

@keyframes sparkleShimmer {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  25% {
    opacity: 0.7;
    transform: scale(1.1);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
  75% {
    opacity: 0.8;
    transform: scale(1.05);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}
`;

// Inject keyframes into document head (only once)
if (typeof document !== 'undefined') {
  const styleId = 'memory-jogger-animations';
  if (!document.getElementById(styleId)) {
    const styleSheet = document.createElement('style');
    styleSheet.id = styleId;
    styleSheet.textContent = glowKeyframes;
    document.head.appendChild(styleSheet);
  }
}

const MemoryJogger = ({
  data,
  onRevisit,
  onDismiss
}) => {
  const shouldReduceMotion = useReducedMotion();

  if (!data?.has_memory || !data?.bookmark) {
    return null;
  }

  const { bookmark, context } = data;
  const {
    id,
    title,
    url,
    domain,
    favicon,
    thumbnail,
    ai_summary
  } = bookmark;

  const {
    days_since_saved,
    connection_count,
    connected_topics,
    reason
  } = context || {};

  const handleRevisit = (e) => {
    e?.stopPropagation();
    window.open(url, '_blank');
    if (onRevisit) onRevisit(id);

    // Check for first resurfacing milestone
    const { reached } = checkMilestone('first_resurfacing');
    if (!reached) {
      markMilestoneReached('first_resurfacing');
      toast.custom((t) => (
        <MilestoneToast
          milestone="first_resurfacing"
          onDismiss={() => toast.dismiss(t)}
        />
      ), { duration: 5000 });
    }
  };

  const handleDismiss = (e) => {
    e.stopPropagation();
    if (onDismiss) onDismiss(id);
  };

  // Personalized header label based on days_since_saved
  const headerLabel = days_since_saved
    ? `Saved ${days_since_saved} days ago`
    : 'Memory of the Day';

  // Connection indicator text (shown separately below header if connection_count > 0)
  const connectionText = connection_count > 0
    ? `Connects to ${connection_count} recent saves`
    : null;

  // Use appropriate variants based on reduced motion preference
  const activeContainerVariants = shouldReduceMotion ? reducedContainerVariants : containerVariants;
  const activeChildVariants = shouldReduceMotion ? reducedChildVariants : childVariants;

  // Glow animation style (only applied when not reduced motion)
  const glowStyle = shouldReduceMotion
    ? {}
    : { animation: 'memoryGlow 2s ease-out forwards' };

  // Sparkle animation style (only applied when not reduced motion)
  const sparkleStyle = shouldReduceMotion
    ? {}
    : { animation: 'sparkleShimmer 1.5s ease-in-out' };

  return (
    <motion.div
      variants={activeContainerVariants}
      initial="hidden"
      animate="visible"
      onClick={handleRevisit}
      style={glowStyle}
      className="w-full bg-background border-2 border-foreground p-4 mb-6 shadow-brutal cursor-pointer hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150"
    >
      {/* Header Label - Icon Badge (0ms delay) */}
      <motion.div
        variants={activeChildVariants}
        className="flex items-center gap-2 mb-1"
      >
        <div className="p-1.5 bg-accent border-2 border-foreground">
          <Sparkles
            className="w-4 h-4 text-accent-foreground"
            style={sparkleStyle}
          />
        </div>
        <span className="font-mono text-xs uppercase tracking-wider text-accent font-medium">
          {headerLabel}
        </span>
      </motion.div>

      {/* Connection Indicator (100ms delay - part of title/header group) */}
      <motion.div variants={activeChildVariants}>
        {connectionText && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground font-mono uppercase tracking-wider mb-3 ml-9">
            <Link2 className="w-3 h-3" />
            <span>{connectionText}</span>
          </div>
        )}
        {!connectionText && <div className="mb-2" />}
      </motion.div>

      {/* Main Content (200ms delay) */}
      <motion.div
        variants={activeChildVariants}
        className="flex items-start gap-4"
      >
        {/* Left: Thumbnail/Favicon + Content */}
        <div className="flex gap-4 flex-1 min-w-0">
          {/* Thumbnail */}
          <div className="flex-shrink-0 w-16 h-16 bg-muted border-2 border-foreground overflow-hidden">
            {thumbnail ? (
              <img
                src={thumbnail}
                alt=""
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-accent/10">
                {favicon ? (
                  <img src={favicon} alt="" className="w-8 h-8" />
                ) : (
                  <Sparkles className="w-5 h-5 text-muted-foreground" />
                )}
              </div>
            )}
          </div>

          {/* Title + Summary */}
          <div className="flex-1 min-w-0">
            <h4 className="font-heading font-bold text-base leading-tight line-clamp-1 mb-1">
              {title || 'Untitled'}
            </h4>

            {/* Domain */}
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1 truncate">
              {domain}
            </p>

            {/* One-sentence summary */}
            {ai_summary?.one_sentence && (
              <p className="text-sm text-muted-foreground line-clamp-1">
                {ai_summary.one_sentence}
              </p>
            )}

            {/* Reason for resurfacing */}
            {reason && (
              <p className="text-xs text-accent font-mono uppercase tracking-wider mt-1">
                {reason}
              </p>
            )}
          </div>
        </div>

        {/* Right: Context + Actions */}
        <div className="flex-shrink-0 flex flex-col items-end gap-2">
          {/* Connected topics */}
          {connected_topics && connected_topics.length > 0 && (
            <div className="flex gap-1 flex-wrap justify-end">
              {connected_topics.slice(0, 2).map((topic, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 bg-muted border border-foreground font-mono text-xs uppercase tracking-wider"
                >
                  {topic}
                </span>
              ))}
            </div>
          )}
        </div>
      </motion.div>

      {/* Actions (300ms delay) */}
      <motion.div
        variants={activeChildVariants}
        className="flex items-center gap-2 mt-3 justify-end"
      >
        <Button
          variant="accent"
          size="sm"
          onClick={handleRevisit}
          className="bg-primary text-primary-foreground border-primary"
        >
          <ExternalLink className="w-3 h-3 mr-1" />
          REVISIT
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDismiss}
          title="Not today"
        >
          <X className="w-3 h-3 mr-1" />
          NOT TODAY
        </Button>
      </motion.div>
    </motion.div>
  );
};

export default MemoryJogger;
