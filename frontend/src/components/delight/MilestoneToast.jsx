import { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { X, Trophy, Star } from 'lucide-react';
import { SuccessCheckmark } from './SuccessCheckmark';
import { BrutalConfetti } from './BrutalConfetti';
import { getMilestoneMessage, isMajorMilestone } from '../../utils/milestones';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

/**
 * Celebratory toast for milestone achievements.
 * Uses BrutalConfetti for major milestones and SuccessCheckmark for minor ones.
 *
 * @param {string} milestone - The milestone identifier (e.g., 'bookmark_50', 'first_graph')
 * @param {function} onDismiss - Callback to close the toast
 */
export const MilestoneToast = ({ milestone, onDismiss }) => {
  const shouldReduceMotion = useReducedMotion();
  const [showConfetti, setShowConfetti] = useState(false);

  const message = getMilestoneMessage(milestone);
  const isMajor = isMajorMilestone(milestone);

  useEffect(() => {
    if (isMajor && !shouldReduceMotion) {
      // Slight delay for confetti to sync with toast entrance
      const timer = setTimeout(() => {
        setShowConfetti(true);
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [isMajor, shouldReduceMotion]);

  if (!message) {
    console.warn(`MilestoneToast: Unknown milestone "${milestone}"`);
    return null;
  }

  const Icon = isMajor ? Trophy : Star;

  return (
    <>
      <motion.div
        initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -10, scale: 0.95 }}
        transition={brutalSpring}
        className="flex items-start gap-4 bg-card border-2 border-foreground shadow-brutal p-4 min-w-[320px] max-w-[420px]"
      >
        {/* Icon with background */}
        <div className={`flex-shrink-0 w-10 h-10 border-2 border-foreground flex items-center justify-center ${
          isMajor ? 'bg-primary' : 'bg-accent'
        }`}>
          {isMajor ? (
            <Icon className="w-5 h-5 text-primary-foreground" />
          ) : (
            <SuccessCheckmark
              size={20}
              color="#FFFFFF"
              delay={0.1}
            />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h4 className="font-heading font-bold text-base uppercase tracking-wide text-foreground">
            {message.title}
          </h4>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mt-1">
            {message.description}
          </p>
        </div>

        {/* Close button */}
        <button
          onClick={onDismiss}
          className="flex-shrink-0 w-6 h-6 flex items-center justify-center hover:bg-muted transition-colors"
          aria-label="Close toast"
        >
          <X className="w-4 h-4" />
        </button>
      </motion.div>

      {/* Confetti for major milestones */}
      <BrutalConfetti
        active={showConfetti}
        onComplete={() => setShowConfetti(false)}
      />
    </>
  );
};

export default MilestoneToast;
