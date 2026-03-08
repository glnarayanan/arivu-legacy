import { motion, useReducedMotion } from 'framer-motion';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

/**
 * Animated checkmark that draws itself with a sharp, angular design.
 *
 * @param {number} size - Size of the checkmark in pixels (default: 24)
 * @param {string} color - Stroke color (default: 'currentColor')
 * @param {number} delay - Delay before animation starts in seconds (default: 0)
 * @param {function} onComplete - Callback when animation completes
 */
export const SuccessCheckmark = ({
  size = 24,
  color = 'currentColor',
  delay = 0,
  onComplete
}) => {
  const shouldReduceMotion = useReducedMotion();

  // Sharp angular checkmark path (not rounded)
  // Starts from bottom-left corner, goes to bottom of V, then up to top-right
  const checkmarkPath = "M 4 12 L 9 17 L 20 6";

  if (shouldReduceMotion) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="Success checkmark"
      >
        <path
          d={checkmarkPath}
          stroke={color}
          strokeWidth={3}
          strokeLinecap="square"
          strokeLinejoin="miter"
          fill="none"
        />
      </svg>
    );
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Success checkmark"
    >
      <motion.path
        d={checkmarkPath}
        stroke={color}
        strokeWidth={3}
        strokeLinecap="square"
        strokeLinejoin="miter"
        fill="none"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{
          ...brutalSpring,
          delay,
        }}
        onAnimationComplete={onComplete}
      />
    </svg>
  );
};

export default SuccessCheckmark;
