import { motion, useReducedMotion } from 'framer-motion';
import { X } from 'lucide-react';
import { SuccessCheckmark } from './SuccessCheckmark';
import { Button } from '../ui/button';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

/**
 * Custom success toast component with animated checkmark.
 * Follows brutalist design system.
 *
 * @param {string} message - The success message to display
 * @param {object} action - Optional action button { label: string, onClick: function }
 * @param {function} onClose - Callback to close the toast
 */
export const SuccessToast = ({
  message,
  action,
  onClose
}) => {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -10, scale: 0.95 }}
      transition={brutalSpring}
      className="flex items-center gap-3 bg-card border-2 border-foreground shadow-brutal p-4 min-w-[280px] max-w-[400px]"
    >
      {/* Animated checkmark with green circle background */}
      <div className="flex-shrink-0 w-8 h-8 bg-green-500 border-2 border-foreground flex items-center justify-center">
        <SuccessCheckmark
          size={18}
          color="#FFFFFF"
          delay={0.1}
        />
      </div>

      {/* Message */}
      <span className="flex-1 font-mono text-sm uppercase tracking-wider text-foreground font-medium">
        {message}
      </span>

      {/* Action button (optional) */}
      {action && (
        <Button
          variant="ghost"
          size="sm"
          onClick={action.onClick}
          className="rounded-none border-2 border-foreground bg-background hover:bg-muted font-mono uppercase text-xs tracking-wider px-3 py-1 h-auto"
        >
          {action.label}
        </Button>
      )}

      {/* Close button */}
      <button
        onClick={onClose}
        className="flex-shrink-0 w-6 h-6 flex items-center justify-center hover:bg-muted transition-colors"
        aria-label="Close toast"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
};

export default SuccessToast;
