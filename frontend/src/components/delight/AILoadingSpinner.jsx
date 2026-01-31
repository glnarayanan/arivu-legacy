import { useReducedMotion } from 'framer-motion';
import { LoadingMessages } from './LoadingMessages';

/**
 * AI-themed loading spinner with geometric brutalist design.
 * Combines a square rotating spinner with cycling messages.
 *
 * @param {string[]} messages - Array of messages to cycle through
 * @param {'sm' | 'md' | 'lg'} size - Spinner size (default: 'md')
 * @param {string} className - Additional CSS classes
 */
export const AILoadingSpinner = ({
  messages = ['Processing...'],
  size = 'md',
  className = ''
}) => {
  const shouldReduceMotion = useReducedMotion();

  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-[3px]'
  };

  const containerClasses = {
    sm: 'gap-2',
    md: 'gap-2',
    lg: 'gap-3'
  };

  return (
    <div className={`inline-flex items-center ${containerClasses[size]} ${className}`}>
      {/* Square geometric spinner - NOT circular */}
      <div
        className={`${sizeClasses[size]} border-accent border-t-transparent ${
          shouldReduceMotion ? '' : 'animate-spin'
        }`}
        style={{
          animationDuration: '600ms',
          animationTimingFunction: 'linear'
        }}
        role="status"
        aria-label="Loading"
      />
      <LoadingMessages
        messages={messages}
        className="text-accent"
      />
    </div>
  );
};

export default AILoadingSpinner;
