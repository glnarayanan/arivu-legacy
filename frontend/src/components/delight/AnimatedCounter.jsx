import { useEffect, useState } from 'react';
import { useSpring, useTransform, useReducedMotion } from 'framer-motion';

const brutalSpring = {
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

/**
 * Animated number counter with spring physics.
 * Displays in mono font with optional suffix.
 *
 * @param {number} endValue - Target value to count to
 * @param {number} startValue - Starting value (default: 0)
 * @param {string} suffix - Optional suffix like "%" or " bookmarks"
 * @param {number} duration - Animation duration in seconds (default: 0.5)
 * @param {number} delay - Delay before animation starts in seconds (default: 0)
 */
export const AnimatedCounter = ({
  endValue,
  startValue = 0,
  suffix = '',
  duration = 0.5,
  delay = 0,
}) => {
  const shouldReduceMotion = useReducedMotion();

  // Calculate spring parameters based on duration
  // Adjust stiffness to match desired duration while keeping brutalist feel
  // Formula: higher stiffness = faster animation
  const adjustedSpring = {
    ...brutalSpring,
    stiffness: brutalSpring.stiffness * (0.5 / Math.max(duration, 0.1)),
  };

  const springValue = useSpring(startValue, adjustedSpring);
  const displayValue = useTransform(springValue, (latest) => Math.round(latest));

  useEffect(() => {
    if (shouldReduceMotion) {
      springValue.set(endValue);
      return;
    }

    const timer = setTimeout(() => {
      springValue.set(endValue);
    }, delay * 1000);

    return () => clearTimeout(timer);
  }, [endValue, delay, springValue, shouldReduceMotion]);

  // For reduced motion, show final value immediately
  if (shouldReduceMotion) {
    return (
      <span
        className="font-mono uppercase tracking-wider"
        aria-label={`${endValue}${suffix}`}
      >
        {endValue}{suffix}
      </span>
    );
  }

  return (
    <span
      className="font-mono uppercase tracking-wider"
      aria-label={`${endValue}${suffix}`}
    >
      <DisplayNumber value={displayValue} />
      {suffix}
    </span>
  );
};

/**
 * Separate component to read motion value and display it.
 */
const DisplayNumber = ({ value }) => {
  const [displayNumber, setDisplayNumber] = useState(0);

  useEffect(() => {
    const unsubscribe = value.on('change', (latest) => {
      setDisplayNumber(latest);
    });
    return unsubscribe;
  }, [value]);

  return <>{displayNumber}</>;
};

export default AnimatedCounter;
