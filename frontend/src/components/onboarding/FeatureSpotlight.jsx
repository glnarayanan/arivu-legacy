import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

/**
 * Contextual tooltip/spotlight for feature discovery.
 * Shows once per feature, dismissed state persisted to localStorage.
 */
export const FeatureSpotlight = ({
  id,
  targetRef,
  title,
  description,
  position = 'bottom', // 'top', 'bottom', 'left', 'right'
  onDismiss,
  showArrow = true,
  delay = 0,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const tooltipRef = useRef(null);

  const storageKey = `arivu_spotlight_${id}`;

  useEffect(() => {
    const hasSeen = localStorage.getItem(storageKey);
    if (hasSeen) return;

    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [id, delay, storageKey]);

  useEffect(() => {
    if (!isVisible || !targetRef?.current) return;

    const updatePosition = () => {
      const targetRect = targetRef.current.getBoundingClientRect();
      const tooltipWidth = 280;
      const tooltipHeight = 120;
      const offset = 12;

      let top = 0;
      let left = 0;

      switch (position) {
        case 'top':
          top = targetRect.top - tooltipHeight - offset;
          left = targetRect.left + targetRect.width / 2 - tooltipWidth / 2;
          break;
        case 'bottom':
          top = targetRect.bottom + offset;
          left = targetRect.left + targetRect.width / 2 - tooltipWidth / 2;
          break;
        case 'left':
          top = targetRect.top + targetRect.height / 2 - tooltipHeight / 2;
          left = targetRect.left - tooltipWidth - offset;
          break;
        case 'right':
          top = targetRect.top + targetRect.height / 2 - tooltipHeight / 2;
          left = targetRect.right + offset;
          break;
        default:
          break;
      }

      // Keep within viewport
      left = Math.max(12, Math.min(left, window.innerWidth - tooltipWidth - 12));
      top = Math.max(12, Math.min(top, window.innerHeight - tooltipHeight - 12));

      setCoords({ top, left });
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);

    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
    };
  }, [isVisible, targetRef, position]);

  const handleDismiss = () => {
    localStorage.setItem(storageKey, 'true');
    setIsVisible(false);
    onDismiss?.();
  };

  if (!isVisible) return null;

  const getArrowStyles = () => {
    const base = "absolute w-3 h-3 bg-card border-foreground rotate-45";
    switch (position) {
      case 'top':
        return `${base} -bottom-1.5 left-1/2 -translate-x-1/2 border-r-2 border-b-2`;
      case 'bottom':
        return `${base} -top-1.5 left-1/2 -translate-x-1/2 border-l-2 border-t-2`;
      case 'left':
        return `${base} -right-1.5 top-1/2 -translate-y-1/2 border-t-2 border-r-2`;
      case 'right':
        return `${base} -left-1.5 top-1/2 -translate-y-1/2 border-b-2 border-l-2`;
      default:
        return base;
    }
  };

  return createPortal(
    <AnimatePresence>
      <motion.div
        ref={tooltipRef}
        initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
        transition={brutalSpring}
        style={{
          position: 'fixed',
          top: coords.top,
          left: coords.left,
          zIndex: 9999,
        }}
        className="w-[280px] bg-card border-2 border-foreground shadow-brutal p-4"
      >
        {/* Arrow */}
        {showArrow && <div className={getArrowStyles()} />}

        {/* Close button */}
        <button
          onClick={handleDismiss}
          className="absolute top-2 right-2 w-6 h-6 flex items-center justify-center hover:bg-muted transition-colors"
          aria-label="Dismiss tip"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Content */}
        <div className="pr-6">
          <h4 className="font-heading font-bold text-sm uppercase tracking-wide mb-1">
            {title}
          </h4>
          <p className="font-mono text-xs text-muted-foreground leading-relaxed">
            {description}
          </p>
        </div>

        {/* Got it button */}
        <button
          onClick={handleDismiss}
          className="mt-3 font-mono text-xs uppercase tracking-wider text-accent hover:text-accent/80 transition-colors"
        >
          Got it
        </button>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
};

/**
 * Hook to manage spotlight visibility for a specific feature
 */
export const useSpotlight = (id) => {
  const [hasSeen, setHasSeen] = useState(true);

  useEffect(() => {
    const seen = localStorage.getItem(`arivu_spotlight_${id}`);
    setHasSeen(!!seen);
  }, [id]);

  const markSeen = () => {
    localStorage.setItem(`arivu_spotlight_${id}`, 'true');
    setHasSeen(true);
  };

  return { hasSeen, markSeen };
};

export default FeatureSpotlight;
